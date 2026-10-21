#!/bin/bash
# Rev C docs only (stitch files + QA already built): crops -> views -> covers -> compare -> pack -> finish
cd "$(dirname "$0")"; H=../../scripts/heavy.sh
( $H ./py.sh swatch.py > logs/swatch_rc.log 2>&1 )
./py.sh make_current.py > logs/qa_make_current.log 2>&1
./py.sh a14crops.py > logs/a14crops.log 2>&1
./py.sh views.py M > logs/docs_views.log 2>&1
./py.sh covers.py > logs/docs_covers.log 2>&1
$H ./py.sh compare.py M > logs/docs_compare.log 2>&1
$H ./py.sh build_all.py > logs/docs_pack.log 2>&1
./py.sh finish.py > logs/docs_finish.log 2>&1
tail -3 logs/docs_finish.log
echo DOCS_RC_DONE
