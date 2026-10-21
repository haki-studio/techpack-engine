#!/bin/bash
# fix round 4, part 2: art chain from the gap fill on (waveart output = art_M_pregap.pkl is unchanged)
cd "$(dirname "$0")"; set -e; H=../../scripts/heavy.sh
cp art_M_pregap.pkl art_M.pkl; rm -f art_M_pretone.pkl     # tonematch starts from an existing pretone file: a stale one drops the new gap fills
./py.sh gapfill.py M > logs/gapfill_r4.log 2>&1
./py.sh tonematch.py M > logs/tonematch_r4.log 2>&1
./py.sh seamedge.py M > logs/seamedge_r4.log 2>&1
$H ./py.sh grainfield.py M > logs/grain_r4.log 2>&1
./py.sh foamcord.py M > logs/foamcord_r4.log 2>&1
echo ART_CHAIN_R4B_DONE
