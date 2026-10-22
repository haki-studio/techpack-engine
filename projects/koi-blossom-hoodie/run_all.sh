#!/bin/bash
# Full rebuild (Rev D: + rfq.py factory summary / techpack / internal) after the size-M gates pass: per-size art, 28 stitch files + splits (slot limiter), current json,
# gates + compare sheets, element specs, embroidery pack, garment pages, merged pack + zip.  Logs in out/logs/.
cd "$(dirname "$0")"; source ../../scripts/env.sh projects/koi-blossom-hoodie >/dev/null
set -e
mkdir -p out/logs
# clean checkout: the traced scene is not in git (scene.pkl, trace/*.pkl) — trace it first (floratrace -> fishtrace -> scene)
[ -f scene.pkl ] || { python3 floratrace.py > out/logs/flora.log 2>&1; python3 fishtrace.py > out/logs/fish.log 2>&1; python3 scene.py > out/logs/scene.log 2>&1; }
../../scripts/heavy.sh python3 art_size.py XS S M L XL XXL 3XL > out/logs/art.log 2>&1
for sz in XS S M L XL XXL 3XL; do ../../scripts/heavy.sh python3 build_size.py $sz > out/logs/size_$sz.log 2>&1 & done
wait
for sz in XS S M L XL XXL 3XL; do grep -q "^DONE $sz" out/logs/size_$sz.log || { echo "BUILD FAILED $sz"; exit 1; }; done
python3 make_current.py > out/logs/current.log 2>&1
python3 fidelity.py > out/logs/fidelity.log 2>&1
python3 compare.py > out/logs/compare.log 2>&1
../../scripts/heavy.sh python3 run_spec.py > out/logs/spec.log 2>&1
../../scripts/heavy.sh python3 pack.py > out/logs/pack.log 2>&1
../../scripts/heavy.sh python3 garment.py > out/logs/garment.log 2>&1
../../scripts/heavy.sh python3 finish.py > out/logs/finish.log 2>&1
../../scripts/heavy.sh python3 rfq.py > out/logs/rfq.log 2>&1
echo ALL DONE
