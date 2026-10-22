#!/bin/bash
# fix round 2: 5 size-M files -> QA chain -> compare sheets -> covers -> pack -> shrink -> package
cd "$(dirname "$0")"; H=../../scripts/heavy.sh
for P in BK FR FL SR SL; do ( $H ./py.sh build_size.py M $P > logs/size_M_$P.log 2>&1 ) & done; wait
grep -h "M .. primary {" logs/size_M_*.log | cut -c1-160
$H ./qa_chain.sh > logs/qa_chain_r2.log 2>&1
./py.sh views.py M > logs/docs_views.log 2>&1
./py.sh covers.py > logs/docs_covers.log 2>&1
$H ./py.sh compare.py M > logs/docs_compare.log 2>&1
$H ./py.sh build_all.py > logs/docs_pack.log 2>&1
./py.sh finish.py > logs/docs_finish.log 2>&1
echo FINAL_R2_DONE
