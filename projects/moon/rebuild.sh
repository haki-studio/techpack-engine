#!/bin/bash
# Rev B full rebuild: art -> clearances -> stitch files (per size + per grade) -> gates -> pattern -> previews -> specs -> pack
cd "$(dirname "$0")"; H=../../scripts/heavy.sh; set -o pipefail
log() { echo "[$(date +%T)] $*" >> rebuild_log.txt; }
: > rebuild_log.txt
rm -f art_*.pkl
printf "%s\n" M XS S L XL XXL 3XL graded | xargs -P 4 -I{} ./py.sh art_size.py {} 2>&1 | grep -v Warn >> rebuild_log.txt
./py.sh emb_place.py 2>&1 | grep -v Warn | grep -E "wrap|FAIL" >> rebuild_log.txt
log art+clearances done
rm -rf out/results/size_*.json out/results/grade_*.json out/01_back-scene/by-size out/03_lower-front/by-size out/02_chest-clouds/grade-* out/04_sleeve-clouds/grade-*
printf "%s\n" "size M" "grade B" "size XS" "size 3XL" "size S" "size L" "size XL" "size XXL" "grade A" "grade C" | xargs -P 4 -I{} sh -c 'set -- {}; if [ "$1" = size ]; then ../../scripts/heavy.sh ./py.sh build_size.py $2 > build_size_$2_log.txt 2>&1; else ../../scripts/heavy.sh ./py.sh build_grade.py $2 > build_grade_$2_log.txt 2>&1; fi'
grep -l Traceback build_size_*_log.txt build_grade_[ABC]_log.txt >> rebuild_log.txt && log BUILD ERRORS
./py.sh collect.py 2>&1 | grep -v Warn >> rebuild_log.txt
log stitch done
$H ./py.sh pattern_moon.py qa dxf pdf 2>&1 | grep -v Warn | tail -3 >> rebuild_log.txt
./py.sh covers.py 2>&1 | grep -v Warn | tail -1 >> rebuild_log.txt
./py.sh preview.py M 1.6 2>&1 | grep -v Warn | tail -1 >> rebuild_log.txt
./py.sh compare_cu.py 2>&1 | grep -v Warn | tail -1 >> rebuild_log.txt
log previews done
printf "%s\n" 01 02 03 04 | xargs -P 4 -I{} sh -c '../../scripts/heavy.sh ./py.sh moonspec.py {} 2>&1 | grep -v Warn | tail -2' >> rebuild_log.txt
$H ./py.sh build_all.py 2>&1 | grep -v Warn | tail -3 >> rebuild_log.txt
log ALLDONE
