"""Compose 02R/02L -> front_vis.pkl + out/art/front_flat.png + front_compare.png (stitch render beside the mockup)."""
import time, pickle, sys, os
t0 = time.time()
import fbcore
import front_scene as F
from motifs2 import HEX
from render import geom_to_path
import cairosvg, dst2
import stitchrender as SR
from PIL import Image, ImageDraw
os.makedirs("out/art", exist_ok=True)
print("items", len(F.items), f"{time.time()-t0:.1f}s", flush=True)
import fmotifs as FM
vis = {}
for p in F.PIECES:
    v, nd = FM.drop_floating(F.build(p)); vis[p] = FM.ridge_cleanup(dst2.clean_vis(v)); print(p, "floating pieces dropped (A1)", nd)
print({k: len(v) for k, v in vis.items()}, f"{time.time()-t0:.1f}s", flush=True)
pickle.dump(vis, open("front_vis.pkl", "wb"))
x0, y0, x1, y1 = -320, -110, 320, 530
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{(x1-x0)*3}" height="{(y1-y0)*3}">',
     f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#FFFFFF"/>']
for pnl in (F.PANEL_R, F.PANEL_L):
    o.append(f'<path d="{geom_to_path(pnl)}" fill="{fbcore.FABRIC}" stroke="#555" stroke-width="0.8"/>')
for s in ("R", "L"):
    o.append(f'<path d="{geom_to_path(F.clip_for(s))}" fill="none" stroke="#C25000" stroke-width="0.4" stroke-dasharray="2 1.5"/>')
for g in (F.COLLAR_R, F.COLLAR_L):
    o.append(f'<path d="{geom_to_path(g)}" fill="#111" fill-opacity="0.7" stroke="#000" stroke-width="0.5"/>')
for w in (F.WELT_R, F.WELT_L):
    o.append(f'<path d="{geom_to_path(w)}" fill="#24302A" stroke="#111" stroke-width="0.5"/>')
o.append(f'<rect x="-6" y="0" width="12" height="{F.HEM}" fill="#B08A3A"/>')
for p, v in vis.items():
    for r in v: o.append(f'<path d="{geom_to_path(r["geom"])}" fill="{HEX[r["col"]]}" fill-rule="evenodd"/>')
o.append('</svg>')
cairosvg.svg2png(bytestring="".join(o).encode(), write_to="out/art/front_flat.png", output_width=1600)
if "sr" in sys.argv:
    ppm = 3.0; bx = (x0, y0, x1, y1)
    img = SR.render([r for v in vis.values() for r in v], bx, ppm, base=fbcore.FABRIC)
    mask = Image.new("L", img.size, 0); d = ImageDraw.Draw(mask)
    for pnl in (F.PANEL_R, F.PANEL_L): d.polygon([((x-x0)*ppm, (y-y0)*ppm) for x, y in pnl.exterior.coords], fill=255)
    bg = Image.new("RGB", img.size, (255, 255, 255)); bg.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(bg)
    for g in (F.COLLAR_R, F.COLLAR_L): d.polygon([((x-x0)*ppm, (y-y0)*ppm) for x, y in g.exterior.coords], fill=(20, 20, 20))
    for g in (F.WELT_R, F.WELT_L): d.polygon([((x-x0)*ppm, (y-y0)*ppm) for x, y in g.exterior.coords], fill=(30, 40, 34))
    d.rectangle([((-5-x0)*ppm, (0-y0)*ppm), ((5-x0)*ppm, (F.HEM-y0)*ppm)], fill=(176, 138, 58))
    bg.save("out/art/sr_front.png")
    mock = Image.open("inputs/front.png").convert("RGB").crop((30, 40, 720, 720)).resize((int(690*bg.height/680), bg.height))
    c = Image.new("RGB", (mock.width + bg.width + 20, bg.height), (255, 255, 255)); c.paste(mock, (0, 0)); c.paste(bg, (mock.width + 20, 0))
    c.save("out/art/front_compare.png")
print("marks", F.zip_marks(), f"{time.time()-t0:.1f}s")
