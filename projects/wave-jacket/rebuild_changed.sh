#!/bin/bash
# rebuild art for every size; rebuild only the stitch files whose art changed (unchanged pieces: files stay valid, marked fresh)
cd "$(dirname "$0")"; mkdir -p /tmp/claude-1000/prevart; cp art_*.pkl /tmp/claude-1000/prevart/
for s in XS S M L XL XXL 3XL; do ../../scripts/heavy.sh ./py.sh waveart.py $s > logs/art_$s.log 2>&1 & done; wait
./py.sh - <<'PY' > logs/changed.txt
import pickle, os, glob
for s in ['XS','S','M','L','XL','XXL','3XL']:
    a=pickle.load(open(f'/tmp/claude-1000/prevart/art_{s}.pkl','rb')); b=pickle.load(open(f'art_{s}.pkl','rb'))
    for P in ('BK','FR','FL','SR','SL'):
        same = len(a[P])==len(b[P]) and all(x['geom'].equals_exact(y['geom'],1e-6) and x['col']==y['col'] for x,y in zip(a[P],b[P]))
        if same:
            for f in glob.glob(f'out/01_wave/{s}/HAKI_WAVE_01_wave_{P}_{s}*') + glob.glob(f'out/01_wave/{s}/splits/HAKI_WAVE_01_wave_{P}_{s}_*'): os.utime(f)
        else: print(s, P)
PY
while read s P; do ../../scripts/heavy.sh ./py.sh build_size.py $s $P > logs/size_${s}_$P.log 2>&1 & done < logs/changed.txt; wait
echo CHANGED_DONE > logs/changed_done.log
