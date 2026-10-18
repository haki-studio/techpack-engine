#!/bin/bash
# documents, in LESSONS D3 order: readbacks -> keep-outs -> views/compare -> specs -> pattern -> packs -> package
set -e; cd "$(dirname "$0")"; source ../../scripts/env.sh projects/castle-falls-jacket >/dev/null
python3 make_current.py > out/make_current.log
python3 emb_place.py | tail -1
python3 views.py M
python3 compare.py
python3 run_spec.py
python3 pattern_cf.py qa dxf pdf | tail -3
python3 build_all.py
python3 finish.py
