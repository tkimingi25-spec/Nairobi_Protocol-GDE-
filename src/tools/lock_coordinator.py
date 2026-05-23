#!/usr/bin/env python3
"""Simple advisory lock coordinator using atomic file creation.

Usage:
  lock_coordinator.py acquire <lockfile>
  lock_coordinator.py release <lockfile>

This script uses os.open with O_CREAT|O_EXCL to create a lockfile atomically. On acquire,
it writes the PID and timestamp into the file. Release removes the file if owned by the PID.
"""
import os
import sys
import time

def acquire(lockfile: str) -> int:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    mode = 0o644
    try:
        fd = os.open(lockfile, flags, mode)
    except FileExistsError:
        return 1
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"pid:{os.getpid()}\n")
            f.write(f"ts:{time.time()}\n")
        return 0
    except Exception:
        try:
            os.unlink(lockfile)
        except Exception:
            pass
        return 2

def release(lockfile: str) -> int:
    try:
        if not os.path.exists(lockfile):
            return 0
        # Only remove if owned by current PID (best-effort)
        try:
            with open(lockfile, "r") as f:
                content = f.read()
        except Exception:
            content = ""
        if f"pid:{os.getpid()}" in content:
            os.unlink(lockfile)
            return 0
        # If not owned, refuse to remove
        return 3
    except Exception:
        return 4

def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    lockfile = argv[2]
    if cmd == "acquire":
        rc = acquire(lockfile)
        return rc
    elif cmd == "release":
        rc = release(lockfile)
        return rc
    else:
        print(__doc__)
        return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv))
