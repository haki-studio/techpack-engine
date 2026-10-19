#!/bin/bash
# after all stitch files: results -> compare sheets -> specs -> covers -> packs -> shrink -> package
cd "$(dirname "$0")"; H=../../scripts/heavy.sh
./py.sh make_current.py
./py.sh compare_dst.py
$H ./py.sh spec_back.py && $H ./py.sh spec_front.py && ./py.sh covers.py && $H ./py.sh build_all.py || exit 1
for f in out/HAKI_FB_Forestball_FULL-TECHPACK_RevC.pdf out/HAKI_FB_EMBROIDERY-PACK_RevC.pdf out/01_back-scene/HAKI_FB_01_back-scene_SPEC_RevC.pdf out/02_chest-branch/HAKI_FB_02_chest-branch_SPEC_RevC.pdf; do
  $H ./py.sh shrink.py "$f" "$f.tmp.pdf" 3000 82 2>/dev/null && mv "$f.tmp.pdf" "$f"; done
./py.sh finish.py
echo DOCS_DONE
