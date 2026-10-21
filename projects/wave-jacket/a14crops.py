"""PR #27 review (round 4, item 2): every failing A14 row shown as a crop - the reference (mockup / close-up tone classes,
the same pixels the gate reads) next to the shipped DST (every stitch, live view) at the same scale, the reference motif
outlined in red on both - so 'drop merged into a crest', 'inside a redrawn seam band' and 'MISSING' can be checked by eye.
usage: ./py.sh a14crops.py   (after qa_chain.sh: reads gates_M.json)  ->  out/a14_rows.png + a14_rows.json"""
import sys
sys.argv = [sys.argv[0], "--nodir"]
import json
import numpy as np
from PIL import Image, ImageDraw
import gates as G, wavetrace as WT, wavecore as WC, live

PPM = 6.0; HALF = 9.0          # crop: 18 x 18 mm around the row, 6 px / mm
GJ = json.load(open("gates_M.json"))
COL = {i: t[1] for i, t in enumerate(WT.TONES)}
fab = tuple(int(WC.FABRIC[i:i + 2], 16) for i in (1, 3, 5))
rows = []
for P in WC.PIECES:
    bad = [(fam, x) for fam in ("curls", "drops", "stripes") for x in GJ["pieces"][P][fam]["rows"] if not x.get("ok", True)]
    if not bad: continue
    cls, bb = G.ref_classes(P); gp = G.PPM
    for fam, x in bad:
        r = max(HALF, np.sqrt(x["area_mm2"] / np.pi) + 4.0)
        cb = (x["x_mm"] - r, x["y_mm"] - r, x["x_mm"] + r, x["y_mm"] + r)
        i0, i1 = int((cb[1] - bb[1]) * gp), int((cb[3] - bb[1]) * gp); j0, j1 = int((cb[0] - bb[0]) * gp), int((cb[2] - bb[0]) * gp)
        sub = cls[max(0, i0):i1, max(0, j0):j1]
        ref = np.zeros(sub.shape + (3,), np.uint8); ref[:] = fab
        for k, c in COL.items():
            if WT.NAMES[k] in WT.FABRIC: continue
            ref[sub == k] = c
        size = (int(2 * r * PPM), int(2 * r * PPM))
        im_r = Image.fromarray(ref).resize(size, Image.NEAREST)
        im_d = live.live_piece(P, cb, PPM).convert("RGB").resize(size)
        for im in (im_r, im_d):
            d = ImageDraw.Draw(im); rr = np.sqrt(x["area_mm2"] / np.pi) * PPM; c = r * PPM
            d.ellipse([c - rr - 3, c - rr - 3, c + rr + 3, c + rr + 3], outline=(230, 40, 40), width=2)
        rows.append(dict(piece=P, family=fam, x_mm=x["x_mm"], y_mm=x["y_mm"], area_mm2=x["area_mm2"], iou=x["iou"], why=x.get("why"), ims=(im_r, im_d)))
# sheet: 4 pairs per row, each sheet row as tall as its tallest crop
per = 4; W = max(max(a.width for a in r_["ims"]) for r_ in rows) if rows else 100; cw = 2 * W + 30
lines = [rows[i:i + per] for i in range(0, len(rows), per)]
hs = [max(r_["ims"][0].height for r_ in ln) + 40 for ln in lines]
sheet = Image.new("RGB", (per * cw + 20, sum(hs) + 50), "white"); d = ImageDraw.Draw(sheet)
d.text((10, 10), f"A14 failing rows (size M, shipped DSTs): {len(rows)} - left = reference (mockup / close-up tone classes the gate reads), right = DST live view; red ring = the reference motif", fill=(0, 0, 0))
y0 = 40; k = 0
for ln, h in zip(lines, hs):
    for c, r_ in enumerate(ln):
        x0 = 10 + c * cw; w_ = r_["ims"][0].width
        sheet.paste(r_["ims"][0], (x0, y0 + 30)); sheet.paste(r_["ims"][1], (x0 + w_ + 6, y0 + 30))
        d.text((x0, y0 + 2), f"{k + 1}. {r_['piece']} {r_['family']} ({r_['x_mm']:.0f}, {r_['y_mm']:.0f}) {r_['area_mm2']:.0f} mm2 IoU {r_['iou']:.2f}", fill=(0, 0, 0))
        d.text((x0, y0 + 15), (r_["why"] or "")[:70], fill=(180, 60, 0)); k += 1
    y0 += h
sheet.save("out/a14_rows.png")
json.dump([{k: v for k, v in r_.items() if k != "ims"} for r_ in rows], open("a14_rows.json", "w"), indent=1, default=float)
print("a14 rows", len(rows), sheet.size)
