#!/bin/bash
# run a CPU-heavy job (stitch builds, splits, specs) in one of N shared slots so parallel product builds don't
# overload the machine. N = $TECHPACK_SLOTS or half the cores.  usage: scripts/heavy.sh python3 build_size.py M
N="${TECHPACK_SLOTS:-$(( $(nproc) / 2 > 0 ? $(nproc) / 2 : 1 ))}"
R="$(cd "$(dirname "$0")/.." && pwd)"
if ! python3 "$R/scripts/storage.py" free-ok; then
  echo "DISK NEARLY FULL (< ${TECHPACK_MIN_FREE_GB:-5} GB free) — not starting: $*" >&2
  echo "Run: python3 scripts/storage.py   then   python3 scripts/storage.py clean --apply" >&2
  exit 3
fi
while true; do
  for i in $(seq 1 "$N"); do
    exec 9>"/tmp/techpack-slot-$i.lock"
    if flock -n 9; then "$@"; rc=$?; flock -u 9; exit $rc; fi
  done
  sleep 5
done
