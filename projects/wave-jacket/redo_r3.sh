#!/bin/bash
# fix round 3 art chain (PR #27 review of fe0a29f): art (unit slivers kept, drop long-axis angles) -> gap fill -> seam tone handover
cd "$(dirname "$0")"; set -e; H=../../scripts/heavy.sh
rm -f art_M_pretone.pkl art_M_pregap.pkl
$H ./py.sh waveart.py M > logs/art_M.log 2>&1
./py.sh gapfill.py M > logs/gapfill_r3.log 2>&1
./py.sh tonematch.py M > logs/tonematch_r3.log 2>&1
echo ART_CHAIN_DONE >> logs/tonematch_r3.log
