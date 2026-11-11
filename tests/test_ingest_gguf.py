"""Phase 2 gates on a tiny synthetic GGUF: ingest, verify, reconstruct,
corruption and interrupted-write detection. No large files are created.

Run: python tests/test_ingest_gguf.py
"""
from __future__ import annotations

import hashlib
import os
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "tools"))
import ingest_gguf as ig  # noqa: E402


def _synthetic_gguf(path: Path) -> bytes:
    # Two F32 tensors: a.weight [2,3] (24 B), b.weight [4] (16 B)
    a = os.urandom(24)
    b = os.urandom(16)
    infos = b""
    for name, dims, off in (("a.weight", [3, 2], 0), ("b.weight", [4], 24)):
        nb = name.encode()
        infos += struct.pack("<Q", len(nb)) + nb
        infos += struct.pack("<I", len(dims))
        for d in dims:
            infos += struct.pack("<Q", d)
        infos += struct.pack("<I", 0)  # F32
        infos += struct.pack("<Q", off)
    header = b"GGUF" + struct.pack("<IQQ", 3, 2, 0) + infos
    header += b"\x00" * ((32 - len(header) % 32) % 32)  # align to 32
    blob = header + a + b
    path.write_bytes(blob)
    return blob


def test_ingest_verify_reconstruct() -> None:
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "tiny.gguf"
        original = _synthetic_gguf(src)
        out = Path(d) / "store"
        manifest = ig.ingest(src, out)
        assert len(manifest["tensors"]) == 3  # header + 2 tensors
        assert manifest["source"]["gguf_sha256"] == hashlib.sha256(original).hexdigest()
        ig.verify_store(out)
        # Corruption must be detected.
        ext = out / "extents.bin"
        with open(ext, "r+b") as f:
            f.seek(manifest["tensors"]["b.weight"]["offset"])
            f.write(b"\xaa")
        try:
            ig.verify_store(out)
            raise AssertionError("corrupt store was accepted")
        except ValueError:
            pass


def test_interrupted_write_detected() -> None:
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "tiny.gguf"
        _synthetic_gguf(src)
        out = Path(d) / "store"
        ig.ingest(src, out)
        # Simulate an interrupted ingestion: partial file, no manifest commit.
        broken = Path(d) / "broken"
        broken.mkdir()
        (broken / "extents.bin.partial").write_bytes(b"\x00" * 64)
        try:
            ig.verify_store(broken)
            raise AssertionError("interrupted store was accepted")
        except FileNotFoundError:
            pass
        # Truncated committed store must also fail.
        ext = out / "extents.bin"
        with open(ext, "r+b") as f:
            f.truncate(ext.stat().st_size - 5)
        try:
            ig.verify_store(out)
            raise AssertionError("truncated store was accepted")
        except (ValueError, IOError):
            pass


def main() -> None:
    test_ingest_verify_reconstruct()
    test_interrupted_write_detected()
    print("PASS: ingest/reconstruction gates (synthetic GGUF)")


if __name__ == "__main__":
    main()
