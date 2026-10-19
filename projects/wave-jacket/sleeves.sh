#!/bin/bash
# sleeve fold fix (19 Oct): art for every size, then SR + SL stitch files + splits, each through the slot limiter
cd "$(dirname "$0")"; mkdir -p logs; rm -f logs/sleeves.log
for s in ${@:-XS S M L XL XXL 3XL}; do
  ( ../../scripts/heavy.sh ./py.sh waveart.py $s > logs/art_$s.log 2>&1 &&
    for P in SR SL; do ../../scripts/heavy.sh ./py.sh build_size.py $s $P > logs/size_${s}_$P.log 2>&1 & done; wait; echo DONE $s >> logs/sleeves.log ) &
done
wait; echo SLEEVES_DONE >> logs/sleeves.log
