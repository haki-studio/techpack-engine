import time, pickle, sys
t0=time.time()
import front as F
from motifs2 import HEX, FABRIC
from render import geom_to_path
import cairosvg
from shapely import affinity
print('items', len(F.items), f'{time.time()-t0:.1f}s', flush=True)
vis = {p: F.build(p) for p in F.PIECES}
print({k: len(v) for k, v in vis.items()}, f'{time.time()-t0:.1f}s', flush=True)
pickle.dump(vis, open('front_vis.pkl','wb'))
x0,y0,x1,y1 = -320, -110, 320, 530
o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{(x1-x0)*3}" height="{(y1-y0)*3}">',
   f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#FFFFFF"/>']
for pnl in (F.PANEL_R, F.PANEL_L):
    o.append(f'<path d="{geom_to_path(pnl)}" fill="{FABRIC}" stroke="#555" stroke-width="0.8"/>')
for g, c in ((F.COLLAR_R, "#5A3B2A"), (F.COLLAR_L, "#5A3B2A")):
    o.append(f'<path d="{geom_to_path(g)}" fill="{c}" fill-opacity="0.25" stroke="#5A3B2A" stroke-width="0.5" stroke-dasharray="2 1.5"/>')
for w in (F.WELT_R, F.WELT_L):
    o.append(f'<path d="{geom_to_path(w)}" fill="#C9B48A" stroke="#7a6a4a" stroke-width="0.5"/>')
o.append(f'<rect x="-6" y="0" width="12" height="{F.HEM}" fill="#9a7a40"/>')
for p, v in vis.items():
    for r in v:
        o.append(f'<path d="{geom_to_path(r["geom"])}" fill="{HEX[r["col"]]}" fill-rule="evenodd"/>')
o.append('</svg>')
cairosvg.svg2png(bytestring="".join(o).encode(), write_to='front_flat.png', output_width=1800)
print('marks', F.zip_marks(), f'{time.time()-t0:.1f}s')
