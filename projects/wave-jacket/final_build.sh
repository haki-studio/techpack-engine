#!/bin/bash
# documents: results -> gates -> pattern outputs -> covers -> compare -> pack -> shrink -> package
cd "$(dirname "$0")"; set -e
H=../../scripts/heavy.sh
./py.sh make_current.py
./py.sh emb_place.py | tail -1
$H ./py.sh coverage.py | tail -1
$H ./py.sh pattern_wave.py qa dxf pdf | tail -3
./py.sh covers.py
$H ./py.sh compare.py M
$H ./py.sh build_all.py | tail -3
F=out/HAKI_WAVE_FULL-TECHPACK_RevA.pdf
./py.sh shrink.py $F ${F%.pdf}_small.pdf 3000 82 && ls -la ${F%.pdf}_small.pdf
./py.sh finish.py
echo FINAL_DONE
