#!/usr/bin/env bash
set -euo pipefail
# Usage: run_with_lock.sh <lockfile> -- <command...>
if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <lockfile> -- <command...>"
  exit 2
fi
LOCKFILE="$1"
shift
if [ "$1" != "--" ]; then
  echo "Missing -- separator"
  exit 2
fi
shift
COMMAND=("$@")

python3 src/tools/lock_coordinator.py acquire "$LOCKFILE"
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "Failed to acquire lock ($RC): $LOCKFILE"
  exit 3
fi

cleanup() {
  python3 src/tools/lock_coordinator.py release "$LOCKFILE" || true
}
trap cleanup EXIT

"${COMMAND[@]}"
