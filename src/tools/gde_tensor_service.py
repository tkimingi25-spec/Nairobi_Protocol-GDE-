#!/usr/bin/env python3
"""GDE tensor service: the retrieval layer behind the virtual GGUF file.

Presents the original GGUF byte space while every read is serviced from
the Phase 2 extent store, in bounded chunks, with a configurable bounded
LRU cache, thread-safe pread-based I/O, per-read accounting, and
optional integrity verification. Filesystem adapters (FUSE / WinFsp)
are thin wrappers over read_at(); the access-pattern proof harness in
tests simulates a runtime consumer against the same path.

Extent layout (from ingest_gguf) preserves original file offsets, so
file_offset maps 1:1 to extent-store offset; the manifest is still the
authority for which tensor a byte belongs to and for verification.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


class TensorService:
    def __init__(self, store_dir: Path, chunk_size: int = 1 << 18,
                 cache_bytes: int = 0, verify_sample: bool = False):
        self.manifest = json.loads((store_dir / "manifest.json").read_text(encoding="utf-8"))
        self.extents_path = store_dir / "extents.bin"
        self.chunk_size = chunk_size
        self.cache_bytes = cache_bytes
        self.verify_sample = verify_sample
        self._fd = os.open(self.extents_path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        self._lock = threading.Lock()
        self._cache: OrderedDict[tuple[int, int], bytes] = OrderedDict()
        self._cache_used = 0
        self.stats = {"reads": 0, "bytes": 0, "cache_hits": 0, "cache_misses": 0,
                      "per_tensor_bytes": {}}
        self.file_size = self.manifest["source"]["file_size"]
        # tensor lookup by byte range for accounting
        self._ranges = sorted(
            (e["offset"], e["offset"] + e["length"], tid)
            for tid, e in self.manifest["tensors"].items())

    def close(self) -> None:
        os.close(self._fd)

    def _tensor_at(self, offset: int) -> str:
        for lo, hi, tid in self._ranges:
            if lo <= offset < hi:
                return tid
        return "<gap>"

    def _read_block(self, block_offset: int) -> bytes:
        """Read one chunk_size block, through the bounded LRU if enabled."""
        key = (block_offset, self.chunk_size)
        if self.cache_bytes > 0:
            with self._lock:
                hit = self._cache.get(key)
                if hit is not None:
                    self._cache.move_to_end(key)
                    self.stats["cache_hits"] += 1
                    return hit
                self.stats["cache_misses"] += 1
        if hasattr(os, "pread"):
            data = os.pread(self._fd, self.chunk_size, block_offset)
        else:  # Windows: seek+read under lock (thread-safe, serialized)
            with self._lock:
                os.lseek(self._fd, block_offset, os.SEEK_SET)
                data = os.read(self._fd, self.chunk_size)
        if self.cache_bytes > 0 and len(data) <= self.cache_bytes:
            with self._lock:
                while self._cache_used + len(data) > self.cache_bytes and self._cache:
                    _, evicted = self._cache.popitem(last=False)
                    self._cache_used -= len(evicted)
                self._cache[key] = data
                self._cache_used += len(data)
        return data

    def read_at(self, offset: int, length: int) -> bytes:
        """Serve [offset, offset+length) from extents, chunk-bounded."""
        if offset < 0 or length < 0 or offset + length > self.file_size:
            raise IOError(f"read outside GGUF space: off={offset} len={length}")
        out = bytearray()
        pos = offset
        end = offset + length
        while pos < end:
            block = pos - (pos % self.chunk_size)
            within = pos - block
            take = min(self.chunk_size - within, end - pos)
            out += self._read_block(block)[within:within + take]
            pos += take
        with self._lock:
            self.stats["reads"] += 1
            self.stats["bytes"] += length
            tid = self._tensor_at(offset)
            self.stats["per_tensor_bytes"][tid] = \
                self.stats["per_tensor_bytes"].get(tid, 0) + length
        return bytes(out)

    def read_tensor(self, tensor_id: str, verify: bool = False) -> bytes:
        e = self.manifest["tensors"][tensor_id]
        data = self.read_at(e["offset"], e["length"])
        if verify or self.verify_sample:
            if hashlib.sha256(data).hexdigest() != e["sha256"]:
                raise ValueError(f"integrity failure reading tensor {tensor_id!r}")
        return data

    def prefetch(self, tensor_ids: list[str], workers: int = 2) -> None:
        """Async warm-up of the bounded cache. Optional and measurable:
        callers must benchmark with and without it (see Phase 6 harness)."""
        if self.cache_bytes <= 0:
            return
        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(lambda t: self.read_tensor(t), tensor_ids))
