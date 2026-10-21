#!/bin/bash
# fix round 4 art chain (PR #27 review of b448e33): art -> gap fill (now also gaps near the art limit + tails) -> seam tone
# handover -> seam lobes -> close-up grain -> foam cords along the grain
cd "$(dirname "$0")"; set -e; H=../../scripts/heavy.sh
rm -f art_M_pretone.pkl art_M_pregap.pkl
$H ./py.sh waveart.py M > logs/art_M.log 2>&1
./py.sh gapfill.py M > logs/gapfill_r4.log 2>&1
./py.sh tonematch.py M > logs/tonematch_r4.log 2>&1
./py.sh seamedge.py M > logs/seamedge_r4.log 2>&1
$H ./py.sh grainfield.py M > logs/grain_r4.log 2>&1
./py.sh foamcord.py M > logs/foamcord_r4.log 2>&1
echo ART_CHAIN_R4_DONE
