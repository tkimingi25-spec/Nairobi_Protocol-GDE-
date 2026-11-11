#!/usr/bin/env python3
"""Mount the GDE extent store as a read-only virtual GGUF (Linux/WSL2).

Requires: pip package `fusepy` and a working FUSE setup.
Every read() is served by gde_tensor_service.TensorService.read_at, so
all tensor bytes an inference runtime consumes traverse the GDE path
and are accounted in service.stats.

UNVERIFIED on the current dev laptop (no WSL2/FUSE installed there);
the service layer it wraps is covered by tests/test_tensor_service.py.

Usage: python src/tools/gde_fuse.py <store_dir> <mountpoint>
"""
from __future__ import annotations

import errno
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gde_tensor_service import TensorService  # noqa: E402

try:
    from fuse import FUSE, Operations
except ImportError as e:  # pragma: no cover
    raise SystemExit("fusepy not installed: pip install fusepy") from e


class GDEFile(Operations):
    def __init__(self, store_dir: Path):
        self.svc = TensorService(store_dir)

    def getattr(self, path, fh=None):
        if path == "/":
            return {"st_mode": stat.S_IFDIR | 0o555, "st_nlink": 2}
        if path == "/model.gguf":
            return {"st_mode": stat.S_IFREG | 0o444, "st_nlink": 1,
                    "st_size": self.svc.file_size}
        raise FileNotFoundError(errno.ENOENT, "no such file", path)

    def readdir(self, path, fh):
        return [".", "..", "model.gguf"]

    def read(self, path, size, offset, fh):
        if path != "/model.gguf":
            raise FileNotFoundError(errno.ENOENT, "no such file", path)
        return self.svc.read_at(offset, size)

    def release(self, path, fh):
        s = self.svc.stats
        print(f"[gde-fuse] reads={s['reads']} bytes={s['bytes']} "
              f"cache_hits={s['cache_hits']} misses={s['cache_misses']}",
              file=sys.stderr)
        return 0


if __name__ == "__main__":
    FUSE(GDEFile(Path(sys.argv[1])), sys.argv[2], foreground=True, ro=True)
