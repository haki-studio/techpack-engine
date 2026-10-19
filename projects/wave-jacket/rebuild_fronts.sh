#!/bin/bash
# welt moved to the block position: rebuild art for every size, then the FR + FL + SL stitch files (front trace changed)
cd "$(dirname "$0")"
for s in XS S M L XL XXL 3XL; do
  ( ../../scripts/heavy.sh ./py.sh waveart.py $s > logs/art_$s.log 2>&1 &&
    for P in FR FL SL; do ../../scripts/heavy.sh ./py.sh build_size.py $s $P > logs/size_${s}_$P.log 2>&1 & done; wait ) &
done
wait; echo FRONTS_DONE > logs/fronts.log
