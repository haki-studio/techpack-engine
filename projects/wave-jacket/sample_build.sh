#!/bin/bash
# EMBROIDERY SAMPLING package (size M): gates -> compare -> element spec + G pages + F1 -> shrink -> zip. No garment pages.
cd "$(dirname "$0")"; set -e
./py.sh make_current.py
./py.sh emb_place.py | tail -1
./py.sh coverage.py M | tail -1
./py.sh compare.py M
./py.sh -c "import espec; espec.build(); import pack; pack.build()"
F=out/HAKI_WAVE_EMBROIDERY-PACK_RevA.pdf
./py.sh shrink.py $F ${F%.pdf}_small.pdf 3000 82 && ls -la $F ${F%.pdf}_small.pdf
./py.sh finish.py
echo SAMPLE_DONE
