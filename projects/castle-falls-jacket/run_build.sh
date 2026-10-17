#!/bin/bash
# stitch files for the given sizes, every piece, through the shared slot limiter. usage: ./run_build.sh M [L XL ...]
cd "$(dirname "$0")"; source ../../scripts/env.sh projects/castle-falls-jacket >/dev/null
for sz in "$@"; do for P in BK SR SL FR FL; do echo "$sz $P"; done; done | \
  xargs -P 5 -n 2 sh -c '../../scripts/heavy.sh python3 build_size.py "$0" "$1" > "out/build_$0_$1.log" 2>&1; echo "finished $0 $1: $(tail -1 out/build_$0_$1.log)"'
echo ALLDONE
