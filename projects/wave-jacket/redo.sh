#!/bin/bash
# rebuild every size/piece that check_runs.py lists as missing or stale
cd "$(dirname "$0")"
for sp in $(./py.sh check_runs.py | grep ^TODO | cut -d' ' -f2-); do
  s=${sp%%:*}; P=${sp##*:}
  ../../scripts/heavy.sh ./py.sh build_size.py $s $P > logs/size_${s}_$P.log 2>&1 &
done
wait; echo REDO_DONE > logs/redo.log
