"""Compose 01 back -> back_vis.pkl + out/art/back_flat.png (flat colours) + back_compare.png (stitch render beside the mockup)."""
import time, pickle, sys, os
t0 = time.time()
import fbcore
import back as B
from motifs2 import HEX
from render import geom_to_path
import cairosvg, dst2
import stitchrender as SR
from PIL import Image, ImageDraw
os.makedirs("out/art", exist_ok=True)
print("items", len(B.items), f"{time.time()-t0:.1f}s", flush=True)
vb = B.build()
import fmotifs as FM
vb, nd = FM.drop_floating(vb); print("floating pieces dropped (A1)", nd)
vb = FM.ridge_cleanup(dst2.clean_vis(vb))
print("vis", len(vb), f"{time.time()-t0:.1f}s", flush=True)
pickle.dump({"back": vb}, open("back_vis.pkl", "wb"))
x0, y0, x1, y1 = -320, -40, 320, 600
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{(x1-x0)*3}" height="{(y1-y0)*3}">',
     f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#FFFFFF"/>',
     f'<path d="{geom_to_path(B.PANEL)}" fill="{fbcore.FABRIC}" stroke="#555" stroke-width="0.8"/>',
     f'<path d="{geom_to_path(B.CLIP)}" fill="none" stroke="#C25000" stroke-width="0.4" stroke-dasharray="2 1.5"/>',
     f'<path d="{geom_to_path(B.COLLAR_B)}" fill="#111" fill-opacity="0.5"/>']
for v in vb:
    o.append(f'<path d="{geom_to_path(v["geom"])}" fill="{HEX[v["col"]]}" fill-rule="evenodd"/>')
o.append('</svg>')
cairosvg.svg2png(bytestring="".join(o).encode(), write_to="out/art/back_flat.png", output_width=1600)
if "sr" in sys.argv:
    ppm = 3.0; bx = (-305, -30, 305, 590)
    img = SR.render(vb, bx, ppm, base=fbcore.FABRIC)
    mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).polygon([((x-bx[0])*ppm, (y-bx[1])*ppm) for x, y in B.PANEL.exterior.coords], fill=255)
    bg = Image.new("RGB", img.size, (255, 255, 255)); bg.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(bg); bb = B.PH_BOX.bounds
    d.rectangle([((bb[0]-bx[0])*ppm, (bb[1]-bx[1])*ppm), ((bb[2]-bx[0])*ppm, (bb[3]-bx[1])*ppm)], outline=(0, 163, 255), width=3)
    bg.save("out/art/sr_back.png")
    mock = Image.open("inputs/back.png").convert("RGB").crop((60, 40, 670, 720)).resize((int(610*bg.height/680), bg.height))
    cmp_ = Image.new("RGB", (mock.width + bg.width + 20, bg.height), (255, 255, 255)); cmp_.paste(mock, (0, 0)); cmp_.paste(bg, (mock.width + 20, 0))
    cmp_.save("out/art/back_compare.png")
print("done", f"{time.time()-t0:.1f}s")
