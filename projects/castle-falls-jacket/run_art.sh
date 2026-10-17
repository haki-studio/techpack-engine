#!/bin/bash
# art chain for size M: warps -> tonal trace -> scenes (parallel) -> per-size art. usage: ./run_art.sh [sizes...]
set -e; cd "$(dirname "$0")"; source ../../scripts/env.sh projects/castle-falls-jacket >/dev/null
python3 warps.py && python3 trace.py | cut -c1-60
for P in BK FR FL SR SL; do python3 scene.py $P & done; wait
python3 art_size.py ${@:-M}
