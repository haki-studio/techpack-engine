#!/bin/bash
# Rev C art chain (founder 21 Oct 'Do A'): waveart output (art_M_pregap.pkl) -> gap fill -> structure passes (no whole-region
# recolour) -> SEAM-BAND REDRAW -> seam lobes (one-sided runs) -> close-up grain -> grain carried into the redrawn zones -> foam cords
cd "$(dirname "$0")"; set -e; H=../../scripts/heavy.sh
cp art_M_pregap.pkl art_M.pkl; rm -f art_M_pretone.pkl art_M_preredraw.pkl art_M_preedge.pkl
./py.sh gapfill.py M > logs/gapfill_rc.log 2>&1
./py.sh tonematch.py M --no-recolour > logs/tonematch_rc.log 2>&1
./py.sh seamredraw.py M > logs/seamredraw_rc.log 2>&1
./py.sh seamedge.py M > logs/seamedge_rc.log 2>&1
$H ./py.sh grainfield.py M > logs/grain_rc.log 2>&1
./py.sh seamredraw.py M --grain >> logs/seamredraw_rc.log 2>&1
./py.sh foamcord.py M > logs/foamcord_rc.log 2>&1
./py.sh continuity.py M --art > logs/continuity_art_rc.log 2>&1
echo ART_CHAIN_RC_DONE
