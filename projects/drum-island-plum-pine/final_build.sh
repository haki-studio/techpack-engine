#!/bin/bash
# after all stitch files exist: results -> specs -> pattern outputs -> packs -> package
set -e
cd "$(dirname "$0")"
python3 make_current.py > final_log.txt 2>&1
python3 spec2.py >> final_log.txt 2>&1
python3 run_front.py 02 03 04 >> final_log.txt 2>&1
python3 pattern_out.py dxf pdf >> final_log.txt 2>&1
python3 build_all.py >> final_log.txt 2>&1
python3 shrink.py out/HAKI_Drum-Island_plum-pine_FULL-TECHPACK_RevC.pdf out/full_small.pdf 3000 82 && mv out/full_small.pdf out/HAKI_Drum-Island_plum-pine_FULL-TECHPACK_RevC.pdf
for f in out/0*/*SPEC_Rev[FC].pdf; do python3 shrink.py "$f" "$f.tmp" 3000 82 && mv "$f.tmp" "$f"; done
python3 finish3.py >> final_log.txt 2>&1
echo FINALDONE >> final_log.txt
