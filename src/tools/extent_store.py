#!/usr/bin/env python3
"""GDE extent store: large contiguous tensor storage (Phase 2/3 prototype).

The 256-byte slot store suits small knowledge records, not model tensors.
Here each tensor is one contiguous extent in a data file, described by a
JSON manifest: {tensor_id: {offset, length, sha256, dtype}}.

Streaming reads are chunked so peak memory is bounded by chunk_size,
never by tensor size.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator

CHUNK = 1 << 20  # 1 MiB default streaming chunk


def write_extents(data_path: Path, tensors: list[tuple[str, bytes, str]]) -> dict:
    """Write tensors contiguously; return the manifest. Small/test-scale
    writer: callers streaming from GGUF should copy in chunks instead."""
    manifest: dict = {"format_version": 1, "tensors": {}}
    offset = 0
    with open(data_path, "wb") as f:
        for tensor_id, blob, dtype in tensors:
            f.write(blob)
            manifest["tensors"][tensor_id] = {
                "offset": offset,
                "length": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "dtype": dtype,
            }
            offset += len(blob)
    return manifest


def save_manifest(manifest: dict, path: Path) -> None:
    path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def stream_extent(data_path: Path, entry: dict, chunk_size: int = CHUNK) -> Iterator[bytes]:
    """Yield one extent in bounded chunks (Phase 3 bounded-RAM reader)."""
    remaining = int(entry["length"])
    with open(data_path, "rb") as f:
        f.seek(int(entry["offset"]))
        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk:
                raise IOError("extent truncated on disk")
            remaining -= len(chunk)
            yield chunk


def read_extent(data_path: Path, manifest: dict, tensor_id: str) -> bytes:
    """Read and checksum-verify one extent. Raises on corruption."""
    entry = manifest["tensors"][tensor_id]
    h = hashlib.sha256()
    parts: list[bytes] = []
    for chunk in stream_extent(data_path, entry):
        h.update(chunk)
        parts.append(chunk)
    if h.hexdigest() != entry["sha256"]:
        raise ValueError(f"sha256 mismatch for tensor {tensor_id!r}: file is corrupt")
    return b"".join(parts)
