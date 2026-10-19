#!/bin/bash
# Rev B: one heavy slot per chain of sizes (usage: run_sizes.sh M:splitsonly XS S ...)
for a in "$@"; do
  sz="${a%%:*}"; ex=""; [ "$a" != "$sz" ] && ex="${a#*:}"
  python3 rbst_stitch.py $sz $ex > size_${sz}_log.txt 2>&1 || echo "FAIL $sz" >> size_${sz}_log.txt
done
