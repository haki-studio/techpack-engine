#!/bin/bash
# Rev C (art round): 5 size-M files + swatch -> QA chain -> docs -> pack -> finish (shrink + zip + A2 on the zip)
cd "$(dirname "$0")"; H=../../scripts/heavy.sh
for P in BK FR FL SR SL; do ( $H ./py.sh build_size.py M $P > logs/size_M_$P.log 2>&1 ) & done
( $H ./py.sh swatch.py > logs/swatch_rc.log 2>&1 ) &
wait
grep -h "M .. primary {" logs/size_M_*.log | cut -c1-160
$H ./qa_chain.sh > logs/qa_chain_rc.log 2>&1
./py.sh views.py M > logs/docs_views.log 2>&1
./py.sh covers.py > logs/docs_covers.log 2>&1
$H ./py.sh compare.py M > logs/docs_compare.log 2>&1
$H ./py.sh build_all.py > logs/docs_pack.log 2>&1
./py.sh finish.py > logs/docs_finish.log 2>&1
tail -2 logs/docs_finish.log
echo FINAL_RC_DONE
