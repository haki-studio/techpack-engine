#!/bin/bash
# Rev E3 quick loop: scene -> size-M art -> size-M full stitch files (slot limiter) -> fidelity gates (debug tiles)
# SKIPSCENE=1 ./runM.sh   reuses scene.pkl;   ./runM.sh split   also writes the hoop splits
set -e
cd "$(dirname "$0")/../.." && source scripts/env.sh projects/grand-line-jacket >/dev/null
[ -n "$SKIPSCENE" ] || python3 -W ignore scene.py > out/scene_run.log 2>&1
python3 -W ignore art_size.py M > out/art_M.log 2>&1          # art builder (not a stitch build): outside the slot limiter
../../scripts/heavy.sh python3 -W ignore build_size.py M $([ "$1" = split ] || echo nosplit) > size_M_log.txt 2>&1
python3 -W ignore qa_fidelity.py M debug > out/qa_M.log 2>&1
echo RUNM_DONE
