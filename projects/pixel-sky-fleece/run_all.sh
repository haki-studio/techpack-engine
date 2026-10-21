#!/bin/bash
# Pixel Sky fleece, full rebuild (from the repo root): bash projects/pixel-sky-fleece/run_all.sh
set -e
cd "$(dirname "$0")/../.."; source scripts/env.sh projects/pixel-sky-fleece >/dev/null
python3 pattern_fl.py qa
../../scripts/heavy.sh python3 jacquard.py
python3 emb_art.py
cd ../..; for F in E1 E2 E3 E1B; do scripts/heavy.sh python3 -m digitize.run projects/pixel-sky-fleece/bench/run_$F.yaml --no-api; done
cd projects/pixel-sky-fleece
python3 gates_jq.py; python3 gates_fl.py; python3 gates_selftest.py; python3 emb_place.py; ../../scripts/heavy.sh python3 pattern_fl.py dxf pdf png
python3 fflat.py; python3 compare.py
# pack twice: R1 (D2) reads the recompressed PDF that finish.py writes in the first pass
for pass in 1 2; do ../../scripts/heavy.sh python3 pack.py; python3 finish.py; done
