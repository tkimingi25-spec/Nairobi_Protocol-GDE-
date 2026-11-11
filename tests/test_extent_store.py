"""Phase 2/3 gates: extent round-trip, corruption detection, bounded streaming.

Uses only tiny synthetic tensors in a temp dir (kilobytes). The real
llama3:8b blob is parsed read-only by test_gguf_manifest_real_blob when
present; it is never copied.

Run: python tests/test_extent_store.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "tools"))
import extent_store as es  # noqa: E402
import gguf_manifest as gm  # noqa: E402


def test_roundtrip_and_corruption() -> None:
    tensors = [("layer0.attn", os.urandom(10_000), "Q4_0"),
               ("layer0.ffn", os.urandom(50_000), "Q4_0"),
               ("embed", os.urandom(999), "F16")]
    with tempfile.TemporaryDirectory() as d:
        data = Path(d) / "model.gde"
        manifest = es.write_extents(data, tensors)
        for tid, blob, _ in tensors:
            assert es.read_extent(data, manifest, tid) == blob
        # Corrupt one byte inside layer0.ffn and expect detection.
        with open(data, "r+b") as f:
            f.seek(manifest["tensors"]["layer0.ffn"]["offset"] + 10)
            f.write(b"\xff")
        try:
            es.read_extent(data, manifest, "layer0.ffn")
            raise AssertionError("corruption was not detected")
        except ValueError:
            pass


def test_bounded_streaming() -> None:
    blob = os.urandom(100_000)
    with tempfile.TemporaryDirectory() as d:
        data = Path(d) / "model.gde"
        manifest = es.write_extents(data, [("big", blob, "Q4_0")])
        entry = manifest["tensors"]["big"]
        chunks = list(es.stream_extent(data, entry, chunk_size=4096))
        assert max(len(c) for c in chunks) <= 4096
        assert b"".join(chunks) == blob


def test_gguf_manifest_real_blob() -> None:
    blobs = Path.home() / ".ollama" / "models" / "blobs"
    if not blobs.exists():
        print("SKIP: no Ollama blob store on this machine")
        return
    candidates = sorted(blobs.iterdir(), key=lambda p: p.stat().st_size, reverse=True)
    for c in candidates:
        if c.stat().st_size < 1_000_000:
            continue
        m = gm.parse_gguf(c)
        assert m["tensor_count"] > 100, m["tensor_count"]
        names = [t["name"] for t in m["tensors"]]
        assert any("attn" in n or "blk" in n for n in names)
        print(f"GGUF: {m['tensor_count']} tensors, arch={m['metadata']}")
        return
    print("SKIP: no large blob found")


def main() -> None:
    test_roundtrip_and_corruption()
    test_bounded_streaming()
    test_gguf_manifest_real_blob()
    print("PASS: extent store gates")


if __name__ == "__main__":
    main()
