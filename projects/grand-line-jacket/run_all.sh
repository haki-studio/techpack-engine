#!/bin/bash
# Rev E2 full rebuild: trace -> scene -> per-size art -> per-size stitch files + splits (each through the slot limiter)
set -e
cd "$(dirname "$0")/../.." && source scripts/env.sh projects/grand-line-jacket >/dev/null
python3 -W ignore closetrace.py > out/closetrace_info.json
python3 -W ignore scene.py
../../scripts/heavy.sh python3 -W ignore art_size.py XS S M L XL XXL 3XL > art_all_log.txt 2>&1
for sz in M XS S L XL XXL 3XL; do
  ../../scripts/heavy.sh python3 -W ignore build_size.py $sz > size_${sz}_log.txt 2>&1 &
done
wait
grep -h "DONE" size_*_log.txt
python3 -W ignore make_current.py | tail -8
