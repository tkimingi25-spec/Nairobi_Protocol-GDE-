#!/usr/bin/env python3
"""Read-only GGUF header parser: list tensors without loading/copying data.

Used to plan GDE extent storage for a real model (e.g. the Ollama
llama3:8b blob) while performing no large writes: only the header,
metadata and tensor-info region is read.

Usage: python src/tools/gguf_manifest.py <model.gguf> [out_manifest.json]
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

GGUF_MAGIC = b"GGUF"
# GGUF metadata value types
_T = {0: "u8", 1: "i8", 2: "u16", 3: "i16", 4: "u32", 5: "i32", 6: "f32",
      7: "bool", 8: "str", 9: "arr", 10: "u64", 11: "i64", 12: "f64"}
_FIXED = {"u8": ("<B", 1), "i8": ("<b", 1), "u16": ("<H", 2), "i16": ("<h", 2),
          "u32": ("<I", 4), "i32": ("<i", 4), "f32": ("<f", 4), "bool": ("<?", 1),
          "u64": ("<Q", 8), "i64": ("<q", 8), "f64": ("<d", 8)}


class _Reader:
    def __init__(self, f):
        self.f = f

    def take(self, n: int) -> bytes:
        b = self.f.read(n)
        if len(b) != n:
            raise IOError("unexpected end of GGUF header")
        return b

    def unpack(self, fmt: str):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def string(self) -> str:
        n = self.unpack("<Q")
        return self.take(n).decode("utf-8", errors="replace")

    def value(self, vtype: int):
        name = _T[vtype]
        if name == "str":
            return self.string()
        if name == "arr":
            etype = self.unpack("<I")
            count = self.unpack("<Q")
            return [self.value(etype) for _ in range(count)]
        fmt, _ = _FIXED[name]
        return self.unpack(fmt)


# GGUF tensor type table: type_id -> (name, block_elems, block_bytes)
GGML_TYPES = {
    0: ("F32", 1, 4), 1: ("F16", 1, 2), 2: ("Q4_0", 32, 18), 3: ("Q4_1", 32, 20),
    6: ("Q5_0", 32, 22), 7: ("Q5_1", 32, 24), 8: ("Q8_0", 32, 34), 9: ("Q8_1", 32, 36),
    10: ("Q2_K", 256, 84), 11: ("Q3_K", 256, 110), 12: ("Q4_K", 256, 144),
    13: ("Q5_K", 256, 176), 14: ("Q6_K", 256, 210), 15: ("Q8_K", 256, 292),
    16: ("IQ2_XXS", 256, 66), 17: ("IQ2_XS", 256, 74), 18: ("IQ3_XXS", 256, 50),
    19: ("IQ1_S", 256, 52), 20: ("IQ4_NL", 32, 18), 21: ("IQ3_S", 256, 110),
    22: ("IQ2_S", 256, 82), 23: ("IQ4_XS", 256, 136), 24: ("I8", 1, 1),
    25: ("I16", 1, 2), 26: ("I32", 1, 4), 27: ("I64", 1, 8), 28: ("F64", 1, 8),
    29: ("IQ1_M", 256, 56), 30: ("BF16", 1, 2),
}


def tensor_nbytes(dims: list[int], type_id: int) -> int:
    name, block_elems, block_bytes = GGML_TYPES[type_id]
    elems = 1
    for d in dims:
        elems *= d
    if elems % block_elems:
        raise ValueError(f"tensor elems {elems} not divisible by block {block_elems} ({name})")
    return elems // block_elems * block_bytes


def parse_gguf(path: Path) -> dict:
    size = path.stat().st_size
    with open(path, "rb") as f:
        r = _Reader(f)
        if r.take(4) != GGUF_MAGIC:
            raise ValueError("not a GGUF file")
        version = r.unpack("<I")
        tensor_count = r.unpack("<Q")
        kv_count = r.unpack("<Q")
        metadata = {}
        for _ in range(kv_count):
            key = r.string()
            vtype = r.unpack("<I")
            val = r.value(vtype)
            if key in ("general.architecture", "general.name", "general.file_type"):
                metadata[key] = val
        alignment = 32
        tensors = []
        for _ in range(tensor_count):
            name = r.string()
            n_dims = r.unpack("<I")
            dims = [r.unpack("<Q") for _ in range(n_dims)]
            ttype = r.unpack("<I")
            rel_offset = r.unpack("<Q")
            tensors.append({"name": name, "dims": dims, "type_id": ttype,
                            "type_name": GGML_TYPES[ttype][0],
                            "n_bytes": tensor_nbytes(dims, ttype),
                            "offset_in_data_region": rel_offset})
        header_end = f.tell()
    data_start = (header_end + alignment - 1) // alignment * alignment
    for t in tensors:
        t["absolute_offset"] = data_start + t["offset_in_data_region"]
    return {"file": str(path), "file_size": size, "gguf_version": version,
            "metadata": metadata, "tensor_count": tensor_count,
            "header_bytes": data_start,
            "data_region_start": data_start, "tensors": tensors}


def main() -> None:
    src = Path(sys.argv[1])
    manifest = parse_gguf(src)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"tensors: {manifest['tensor_count']}  file_size: {manifest['file_size']}")
    for t in manifest["tensors"][:5]:
        print(" ", t["name"], t["dims"], "type", t["type_id"])


if __name__ == "__main__":
    main()
