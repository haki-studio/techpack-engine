#!/bin/bash
# second half of rebuild.sh (after the stitch builds): collect -> pattern -> covers/previews/compare -> specs -> pack
cd "$(dirname "$0")"; H=../../scripts/heavy.sh; set -o pipefail
log() { echo "[$(date +%T)] $*" >> rebuild_log.txt; }
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
