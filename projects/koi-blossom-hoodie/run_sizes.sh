#!/bin/bash
# all per-size stitch files + splits, through the shared slot limiter (logs in out/logs/)
cd "$(dirname "$0")"; source ../../scripts/env.sh projects/koi-blossom-hoodie >/dev/null
mkdir -p out/logs
for s in "${@:-XS S M L XL XXL 3XL}"; do
  for sz in $s; do ../../scripts/heavy.sh python3 build_size.py $sz > out/logs/size_$sz.log 2>&1 & done
done
wait; echo ALL DONE
