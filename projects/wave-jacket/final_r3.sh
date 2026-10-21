#!/bin/bash
# fix round 3: seam lobes -> close-up grain -> 5 size-M files + swatch -> QA chain -> docs -> pack -> finish (shrink + zip + A2 on the zip)
cd "$(dirname "$0")"; H=../../scripts/heavy.sh
./py.sh seamedge.py M > logs/seamedge_r3.log 2>&1 || { echo SEAMEDGE_FAIL; exit 1; }
$H ./py.sh grainfield.py M > logs/grain_r3.log 2>&1 || { echo GRAIN_FAIL; exit 1; }
for P in BK FR FL SR SL; do ( $H ./py.sh build_size.py M $P > logs/size_M_$P.log 2>&1 ) & done
( $H ./py.sh swatch.py > logs/swatch_r3.log 2>&1 ) &
wait
grep -h "M .. primary {" logs/size_M_*.log | cut -c1-160
$H ./qa_chain.sh > logs/qa_chain_r3.log 2>&1
./py.sh views.py M > logs/docs_views.log 2>&1
./py.sh covers.py > logs/docs_covers.log 2>&1
$H ./py.sh compare.py M > logs/docs_compare.log 2>&1
$H ./py.sh build_all.py > logs/docs_pack.log 2>&1
./py.sh finish.py > logs/docs_finish.log 2>&1
tail -2 logs/docs_finish.log
echo FINAL_R3_DONE
