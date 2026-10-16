import time, pickle, sys
t0=time.time()
import back2 as B
from motifs2 import HEX, FABRIC
from render import geom_to_path, f
import cairosvg
from shapely.geometry import box
print('items', len(B.items), f'{time.time()-t0:.1f}s', flush=True)
vb = B.build(B.BACK_CLIP); vs = B.build(B.SLEEVE_CLIP)
print('vis', len(vb), len(vs), f'{time.time()-t0:.1f}s', flush=True)
pickle.dump({"back": vb, "sleeve": vs}, open('back2_vis.pkl','wb'))
x0,y0,x1,y1 = -320, -30, 400, 700
o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{(x1-x0)*3}" height="{(y1-y0)*3}">',
   f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#FFFFFF"/>',
   f'<path d="{geom_to_path(B.SLEEVE_R)}" fill="#E6D6B8" stroke="#999" stroke-width="0.6"/>',
   f'<path d="{geom_to_path(B.PANEL)}" fill="{FABRIC}" stroke="#555" stroke-width="0.8"/>']
for v in vb + vs:
    o.append(f'<path d="{geom_to_path(v["geom"])}" fill="{HEX[v["col"]]}" fill-rule="evenodd"/>')
o.append(f'<path d="M{" L".join(f"{x:.1f} {y:.1f}" for x,y in B.ARM_R_LINE.coords)}" fill="none" stroke="#0A84D6" stroke-width="0.6" stroke-dasharray="3 2"/>')
o.append('</svg>')
cairosvg.svg2png(bytestring="".join(o).encode(), write_to=sys.argv[1] if len(sys.argv)>1 else 'back2_flat.png', output_width=1800)
print('done', f'{time.time()-t0:.1f}s')
