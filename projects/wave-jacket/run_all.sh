#!/bin/bash
# all sizes: art (waveart.py) then the five stitch files + splits (build_size.py), each through the slot limiter
cd "$(dirname "$0")"; mkdir -p logs
SIZES="${@:-XS S M L XL XXL 3XL}"
for s in $SIZES; do
  ( ../../scripts/heavy.sh ./py.sh waveart.py $s > logs/art_$s.log 2>&1 &&
    for P in BK FR FL SR SL; do ../../scripts/heavy.sh ./py.sh build_size.py $s $P > logs/size_${s}_$P.log 2>&1 & done; wait; echo DONE $s >> logs/run_all.log ) &
done
wait; echo ALLDONE >> logs/run_all.log
