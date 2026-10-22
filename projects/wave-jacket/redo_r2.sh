#!/bin/bash
# fix round 2 art chain (PR #27): re-trace (close-ups) -> art -> gap fill -> seam tone handover. gapfill runs BEFORE
# tonematch so fills near a seam take the leader's thread too (the first order left mockup tones on the seams).
cd "$(dirname "$0")"; set -e; H=../../scripts/heavy.sh
$H ./py.sh wavetrace.py > logs/trace_r2.log 2>&1
rm -f art_M_pretone.pkl art_M_pregap.pkl
$H ./py.sh waveart.py M > logs/art_M.log 2>&1
./py.sh gapfill.py M > logs/gapfill_r2.log 2>&1
./py.sh tonematch.py M > logs/tonematch_r2.log 2>&1
echo ART_CHAIN_DONE >> logs/tonematch_r2.log
