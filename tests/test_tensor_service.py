"""Phase 4 gates: GDE tensor service read path.

Builds a tiny synthetic GGUF store, then consumes it the way a runtime
would: header first, sequential tensor fetches, random re-reads,
concurrent reads. Asserts every byte comes through the service (its
counters must account for all of it), integrity holds, cache stays
within its byte budget, and corrupt data raises instead of serving.

Run: python tests/test_tensor_service.py
"""
from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import ingest_gguf as ig  # noqa: E402
import gde_tensor_service as gts  # noqa: E402
from test_ingest_gguf import _synthetic_gguf  # noqa: E402


def test_service_read_path() -> None:
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "tiny.gguf"
        original = _synthetic_gguf(src)
        out = Path(d) / "store"
        ig.ingest(src, out)
        svc = gts.TensorService(out, chunk_size=64, cache_bytes=256)
        # Runtime-style consumption: whole file in slices via the service.
        rebuilt = b"".join(
            svc.read_at(off, min(37, len(original) - off))
            for off in range(0, len(original), 37))
        assert rebuilt == original
        assert svc.stats["bytes"] == len(original)
        # Tensor reads verify integrity.
        assert len(svc.read_tensor("a.weight", verify=True)) == 24
        # Cache respects its budget.
        assert svc._cache_used <= 256
        # Concurrent reads return consistent data.
        results: list[bytes] = []
        threads = [threading.Thread(target=lambda: results.append(svc.read_tensor("b.weight")))
                   for _ in range(16)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert all(len(r) == 16 for r in results) and len(set(results)) == 1
        svc.close()
        # Corrupt the store inside a.weight: verified reads must raise.
        ext = out / "extents.bin"
        with open(ext, "r+b") as f:
            f.seek(svc.manifest["tensors"]["a.weight"]["offset"] + 3)
            f.write(b"\xaa")
        svc2 = gts.TensorService(out, chunk_size=64)
        try:
            try:
                svc2.read_tensor("a.weight", verify=True)
                raise AssertionError("corrupt tensor was served")
            except ValueError:
                pass
        finally:
            svc2.close()


def main() -> None:
    test_service_read_path()
    print("PASS: tensor service read-path gates")


if __name__ == "__main__":
    main()
