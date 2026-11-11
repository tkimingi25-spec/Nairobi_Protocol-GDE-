#!/usr/bin/env python3
"""Mount the GDE extent store as a read-only virtual GGUF (Windows).

Requires: WinFsp (https://winfsp.dev) and `pip install winfspy`.
Same contract as gde_fuse.py: every read is served by
TensorService.read_at and accounted in service.stats.

UNVERIFIED on the current dev laptop (WinFsp not installed there);
the service layer it wraps is covered by tests/test_tensor_service.py.

Usage: python src/tools/gde_winfsp.py <store_dir> <mountpoint e.g. G:>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gde_tensor_service import TensorService  # noqa: E402

try:
    from winfspy import (FileSystem, BaseFileSystemOperations,
                         FILE_ATTRIBUTE, CREATE_FILE_ACCESS, NTStatusError,
                         NTSTATUS)
except ImportError as e:  # pragma: no cover
    raise SystemExit("winfspy/WinFsp not installed: install WinFsp, then pip install winfspy") from e


class GDEOperations(BaseFileSystemOperations):
    def __init__(self, store_dir: Path):
        super().__init__()
        self.svc = TensorService(store_dir)

    def get_volume_info(self):
        return {"total_size": self.svc.file_size, "free_size": 0,
                "volume_label": "GDE"}

    def get_security_by_name(self, file_name, security_descriptor_handle, is_reparse_point):
        if file_name not in ("\\", "\\model.gguf"):
            raise NTStatusError(NTSTATUS.STATUS_OBJECT_NAME_NOT_FOUND)
        return FILE_ATTRIBUTE.FILE_ATTRIBUTE_READONLY, 0, None

    def create(self, file_name, create_options, granted_access, file_attributes,
               security_descriptor, allocation_size, main_file_name=None):
        if file_name != "\\model.gguf":
            raise NTStatusError(NTSTATUS.STATUS_OBJECT_NAME_NOT_FOUND)
        return 0, {"file_size": self.svc.file_size,
                   "file_attributes": FILE_ATTRIBUTE.FILE_ATTRIBUTE_READONLY}

    def get_file_info(self, file_context):
        return {"file_size": self.svc.file_size,
                "file_attributes": FILE_ATTRIBUTE.FILE_ATTRIBUTE_READONLY}

    def read_directory(self, file_context, marker):
        return [".", "..", "model.gguf"]

    def read(self, file_context, offset, length):
        return self.svc.read_at(offset, length)

    def cleanup(self, file_context, file_name, flags):
        pass

    def close(self, file_context):
        s = self.svc.stats
        print(f"[gde-winfsp] reads={s['reads']} bytes={s['bytes']} "
              f"cache_hits={s['cache_hits']} misses={s['cache_misses']}",
              file=sys.stderr)


if __name__ == "__main__":
    fs = FileSystem(sys.argv[2], GDEOperations(Path(sys.argv[1])),
                    sector_size=4096, sectors_per_allocation_unit=1,
                    volume_creation_time=0, volume_serial_number=0,
                    file_info_timeout=1000, case_sensitive_search=1,
                    case_preserved_names=1, unicode_on_disk=1,
                    persistent_acls=0, post_cleanup_when_modified_only=1,
                    um_file_context_is_user_context2=0, device_control=0)
    fs.start()
    print("Mounted. Press Enter to unmount.")
    input()
    fs.stop()
