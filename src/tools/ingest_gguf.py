#!/usr/bin/env python3
"""Ingest a GGUF model into the GDE extent store, transactionally (Phase 2).

Layout produced in the output directory:
  extents.bin     header extent followed by every tensor extent, contiguous
  manifest.json   {format_version, source:{...}, tensors:{id:{...}}}

Transactional process:
  1. Stream-copy to extents.bin.partial, hashing every tensor on the fly.
  2. fsync, then re-read the partial file and verify every tensor hash.
  3. Verify reconstruction: sha256 over (header + tensors in file order)
     must equal sha256 of the original GGUF, computed streaming.
  4. Only then atomically rename .partial -> extents.bin and write the
     manifest (also via temp + rename). Any failure leaves .partial
     artifacts that verify_store() will reject; nothing is silently
     accepted.

Memory is bounded by --chunk (default 1 MiB) plus interpreter overhead.

Usage:
  python src/tools/ingest_gguf.py <model.gguf> <out_dir>
  python src/tools/ingest_gguf.py --verify <out_dir>
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gguf_manifest as gm  # noqa: E402

CHUNK = 1 << 20


def _copy_range(src_f, dst_f, offset: int, length: int, chunk: int) -> str:
    h = hashlib.sha256()
    src_f.seek(offset)
    remaining = length
    while remaining > 0:
        data = src_f.read(min(chunk, remaining))
        if not data:
            raise IOError("source GGUF truncated during ingestion")
        h.update(data)
        dst_f.write(data)
        remaining -= len(data)
    return h.hexdigest()


def _hash_range(f, offset: int, length: int, chunk: int) -> str:
    h = hashlib.sha256()
    f.seek(offset)
    remaining = length
    while remaining > 0:
        data = f.read(min(chunk, remaining))
        if not data:
            raise IOError("file truncated during verification")
        h.update(data)
        remaining -= len(data)
    return h.hexdigest()


def ingest(src_path: Path, out_dir: Path, chunk: int = CHUNK) -> dict:
    parsed = gm.parse_gguf(src_path)
    tensors = sorted(parsed["tensors"], key=lambda t: t["absolute_offset"])
    # The reconstruction proof requires gapless coverage of the data region.
    pos = parsed["data_region_start"]
    for t in tensors:
        if t["absolute_offset"] != pos:
            raise ValueError(f"gap/overlap before tensor {t['name']}: cannot prove byte-identical reconstruction")
        pos += t["n_bytes"]
    if pos != parsed["file_size"]:
        raise ValueError("tensors do not exactly fill the GGUF file")

    out_dir.mkdir(parents=True, exist_ok=True)
    partial = out_dir / "extents.bin.partial"
    manifest: dict = {
        "format_version": 1,
        "source": {"file_size": parsed["file_size"], "architecture": parsed["metadata"],
                   "tensor_count": parsed["tensor_count"], "header_bytes": parsed["header_bytes"]},
        "tensors": {},
    }
    with open(src_path, "rb") as src, open(partial, "wb") as dst:
        hdr_hash = _copy_range(src, dst, 0, parsed["header_bytes"], chunk)
        manifest["tensors"]["__header__"] = {
            "offset": 0, "length": parsed["header_bytes"], "sha256": hdr_hash,
            "dtype": "GGUF_HEADER", "dims": []}
        offset = parsed["header_bytes"]
        for t in tensors:
            digest = _copy_range(src, dst, t["absolute_offset"], t["n_bytes"], chunk)
            manifest["tensors"][t["name"]] = {
                "offset": offset, "length": t["n_bytes"], "sha256": digest,
                "dtype": t["type_name"], "dims": t["dims"]}
            offset += t["n_bytes"]
        dst.flush()
        os.fsync(dst.fileno())

    # Step 2+3: verify the copy and the reconstruction before committing.
    verify_extents_file(partial, manifest, chunk)
    with open(src_path, "rb") as src, open(partial, "rb") as dst:
        original_hash = _hash_range(src, 0, parsed["file_size"], chunk)
        rebuilt_hash = _hash_range(dst, 0, offset, chunk)
    if original_hash != rebuilt_hash:
        raise ValueError("reconstruction hash != original GGUF hash; refusing to commit store")
    manifest["source"]["gguf_sha256"] = original_hash

    final = out_dir / "extents.bin"
    os.replace(partial, final)
    tmp_manifest = out_dir / "manifest.json.tmp"
    tmp_manifest.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    os.replace(tmp_manifest, out_dir / "manifest.json")
    return manifest


def verify_extents_file(extents_path: Path, manifest: dict, chunk: int = CHUNK) -> int:
    """Re-hash every extent. Raises on missing/corrupt/incomplete data."""
    total = 0
    with open(extents_path, "rb") as f:
        file_len = f.seek(0, os.SEEK_END)
        for tid, e in manifest["tensors"].items():
            if e["offset"] + e["length"] > file_len:
                raise ValueError(f"extent {tid!r} extends past end of store (incomplete write)")
            if _hash_range(f, e["offset"], e["length"], chunk) != e["sha256"]:
                raise ValueError(f"sha256 mismatch for extent {tid!r} (corrupt store)")
            total += e["length"]
    return total


def verify_store(out_dir: Path, chunk: int = CHUNK) -> dict:
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("no manifest.json: store was never committed (interrupted ingestion?)")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    extents = out_dir / "extents.bin"
    if not extents.exists():
        raise FileNotFoundError("manifest present but extents.bin missing")
    total = verify_extents_file(extents, manifest, chunk)
    expected = sum(e["length"] for e in manifest["tensors"].values())
    if total != expected or extents.stat().st_size != expected:
        raise ValueError("store size does not match manifest (incomplete or padded store)")
    return manifest


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--verify":
        m = verify_store(Path(args[1]))
        print(f"STORE OK: {len(m['tensors'])} extents, gguf_sha256={m['source'].get('gguf_sha256')}")
        return
    src, out_dir = Path(args[0]), Path(args[1])
    m = ingest(src, out_dir)
    print(f"INGESTED: {len(m['tensors'])} extents, gguf_sha256={m['source']['gguf_sha256']}")


if __name__ == "__main__":
    main()
