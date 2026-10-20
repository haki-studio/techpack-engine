#!/bin/bash
# Rev E3: every size from the current scene.pkl: per-size art (art builder, direct), then per-size full stitch files + hoop
# splits (each through the slot limiter, all queued at once), then dst_all/dst_current from the read-backs.
cd "$(dirname "$0")/../.." && source scripts/env.sh projects/grand-line-jacket >/dev/null
python3 -W ignore art_size.py XS S M L XL XXL 3XL > art_all_log.txt 2>&1 || { echo ART_FAIL; exit 1; }
for sz in M XS S L XL XXL 3XL; do
  ../../scripts/heavy.sh python3 -W ignore build_size.py $sz > size_${sz}_log.txt 2>&1 &
done
wait
grep -h "DONE" size_*_log.txt
grep -L "DONE" size_*_log.txt | sed 's/^/MISSING DONE: /'
python3 -W ignore make_current.py | tail -n 8
echo SIZES_DONE
