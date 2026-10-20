#!/bin/bash
# Rev B QA chain on the shipped size-M files: readback -> keep-outs -> DST coverage -> A14/A15 gates -> seam continuity -> placement plot
cd "$(dirname "$0")"
./py.sh make_current.py > logs/qa_make_current.log 2>&1 && echo "make_current ok"
./py.sh emb_place.py 2>&1 | grep -v Warn | tail -1 | cut -c1-400 > logs/qa_keepouts.log; tail -c 300 logs/qa_keepouts.log
./py.sh coverage.py M > logs/qa_coverage.log 2>&1; tail -1 logs/qa_coverage.log
./py.sh gates.py > logs/qa_gates.log 2>&1; grep -v Warn logs/qa_gates.log | tail -45
./py.sh discont.py > logs/qa_discont.log 2>&1; grep -v Warn logs/qa_discont.log | tail -2
./py.sh crops.py > logs/qa_crops.log 2>&1; tail -1 logs/qa_crops.log
./py.sh continuity.py M > logs/qa_continuity.log 2>&1; grep -v Warn logs/qa_continuity.log | tail -14
./py.sh placement.py > logs/qa_placement.log 2>&1; grep -v Warn logs/qa_placement.log | tail -2
echo QA_CHAIN_DONE
