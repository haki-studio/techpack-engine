#!/bin/bash
# full rebuild: art (all sizes) -> stitch files (all sizes, slot-limited) -> checks -> documents
set -e; cd "$(dirname "$0")"; source ../../scripts/env.sh projects/castle-falls-jacket >/dev/null
./run_art.sh M > out/art/run_art.log 2>&1
for s in XS S L XL XXL 3XL; do python3 art_size.py $s > out/art/art_$s.log 2>&1 & done; wait
python3 emb_place.py | tail -1
./run_build.sh M XS S L XL XXL 3XL
python3 make_current.py > out/make_current.log
python3 check_dst.py
../../scripts/heavy.sh ./run_docs.sh
echo PIPELINE DONE
