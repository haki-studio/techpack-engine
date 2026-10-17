"""compare_<element>.png: close-up (tracing reference) | our stitch preview (size M art), matched scale, + zoom rows."""
import pickle
from PIL import Image, ImageDraw
import moonpal, closeart as CA, stitchrender as SR, moonpattern, pattern as PT
A = pickle.load(open("art_M.pkl", "rb")); G = pickle.load(open("art_graded.pkl", "rb"))
cx, cy, r = CA.CU_MOON; s0 = 120.0 / r          # close-up px -> back mm (moon registration)
def bmm(px, py): return ((px - cx) * s0, 244 + (py - cy) * s0)
def pair(name, img, pxbox, vis, mmbox, ppm, rows=None):
    ours = SR.render(vis, mmbox, ppm, base=moonpal.FABRIC)
    cu = img.crop(pxbox).resize(ours.size, Image.LANCZOS)
    out = Image.new("RGB", (ours.width * 2 + 20, ours.height + 24), "white"); d = ImageDraw.Draw(out)
    out.paste(cu, (0, 24)); out.paste(ours, (ours.width + 20, 24))
    d.text((4, 4), f"{name}: CLOSE-UP (left, tracing reference) | OURS (right, stitch preview of the size-M art)", fill=(200, 0, 0))
    out.save(f"out/compare_{name}.png"); return out
vb = A["back"] + A["moonbox"]
for nm, box in (("01_moon", (440, 10, 1010, 580)), ("01_pole", (430, 480, 1040, 1086)), ("01_clouds_left", (20, 160, 660, 740)), ("01_clouds_right", (880, 260, 1448, 660))):
    a = bmm(box[0], box[1]); b = bmm(box[2], box[3]); pair(nm, CA.CB, box, vb, (a[0], a[1], b[0], b[1]), 4)
# front: whole panels side by side (garment x from CF), close-up framing approx (zip at x 727 px)
g, mt = PT.draft("M")
fv = A["F03L"] + A["F03R"] + G["02R"] + G["02L"]
pair("02_03_front", CA.CF, (0, 0, 1448, 1086), fv, (-300, 60, 300, 512), 2.5)
for k in ("04R", "04L"):
    b = G[k] and __import__("shapely.ops", fromlist=["unary_union"]).unary_union([r_["geom"] for r_ in G[k]]).bounds
    sp = g["S01" if k == "04R" else "S02"].sew_poly().bounds
    pair(f"04_{k}", CA.CS, (0, 0, 724, 1086) if k == "04R" else (724, 0, 1448, 1086), G[k], (sp[0], sp[1], sp[2], sp[3]), 2.5)
print("ok")
