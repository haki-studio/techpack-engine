#!/bin/bash
cd "$(dirname "$0")"
until grep -q "^3XL " back_size_log.txt || grep -q Traceback back_size_log.txt; do sleep 15; done
# wait for grade A/B front builds to stop
while pgrep -f "build_dst3.py [AB]" > /dev/null; do sleep 15; done
printf "%s\n" "dst3 C 02R 02L 03 04 nosplit" "size M" "size XS" "size 3XL" "size S" "size L" "size XL" "size XXL" | \
  xargs -P 2 -I{} sh -c 'set -- {}; if [ "$1" = dst3 ]; then shift; python3 build_dst3.py "$@" > dst3_C_log.txt 2>&1; else python3 build_size.py $2 > size_$2_log.txt 2>&1; fi'
echo ALLDONE > queue_done.txt
