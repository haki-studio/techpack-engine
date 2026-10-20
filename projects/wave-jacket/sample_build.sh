#!/bin/bash
# EMBROIDERY SAMPLING package (size M), Rev B: QA chain -> compare -> element spec + G pages + F1 -> shrink -> zip.
cd "$(dirname "$0")"; set -e
./qa_chain.sh
./py.sh compare.py M
./py.sh -c "import espec; espec.build(); import pack; pack.build()"
F=out/HAKI_WAVE_EMBROIDERY-PACK_RevB.pdf
./py.sh shrink.py $F ${F%.pdf}_small.pdf 3000 82 && ls -la $F ${F%.pdf}_small.pdf
./py.sh finish.py
echo SAMPLE_DONE
