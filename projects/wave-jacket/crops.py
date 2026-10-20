"""Before / after crops of the areas the founder flagged on FL (19 Oct): under the collar fall, and the cut lines inside the
panel near the armhole / side (old seamfill band). Rendered from the DSTs (every stitch), before = the seamfill build kept
in out/before_seamfill/M, after = the shipped files.  usage: ./py.sh crops.py  ->  out/crops_FL_before_after.png"""
import wavecore as WC
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
import pyembroidery as pe, motifs2, pieces as PC

def render(root, P, bb, ppm):
    r = json.load(open(f"{root}/result_{P}.json"))["full"]; f_ = os.path.join(root, os.path.basename(r["file"]) + ".dst")
    p = pe.read(f_); cols = [motifs2.HEX[s["col"]] for s in r["per_stop"]]; ox, oy = r["origin"]
    im = Image.new("RGB", (int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm)), WC.FABRIC); d = ImageDraw.Draw(im)
    lw = max(1, int(round(0.4 * ppm))); ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; q = ((x / 10 + ox - bb[0]) * ppm, (y / 10 + oy - bb[1]) * ppm)
        if k == pe.STITCH:
            if prev is not None: d.line([prev, q], fill=cols[min(ci, len(cols) - 1)], width=lw)
            prev = q
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        else: prev = None
    pan = PC.panel("M", "FL" if P == "FL" else P)
    d.line([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in PC.clip_for("M", P).exterior.coords], fill=(255, 80, 80), width=1)
    return im

AREAS = {"FL": [("under the collar fall", (0, -95, 190, 80)), ("armhole / side band (old cut lines)", (150, -50, 305, 260))],
         "FR": [("under the collar fall", (-190, -95, 0, 80))], "BK": [("side R band", (180, 250, 305, 560))], "SR": [("underarm back", (-260, 0, -120, 300))]}
if __name__ == "__main__":
    ppm = 3.0; rows = []
    for P, ar in AREAS.items():
        for name, bb in ar:
            a = render("out/before_seamfill/M", P, bb, ppm); b = render("out/01_wave/M", P, bb, ppm)
            o = Image.new("RGB", (a.width * 2 + 30, a.height + 26), "white"); o.paste(a, (0, 26)); o.paste(b, (a.width + 30, 26))
            dd = ImageDraw.Draw(o); dd.text((4, 6), f"{P} {name}: BEFORE (seamfill band, collar V keep-out)", fill=(0, 0, 0)); dd.text((a.width + 34, 6), "AFTER (smooth seam warp, art under the collar)", fill=(0, 0, 0))
            rows.append(o)
    W = max(r.width for r in rows); H = sum(r.height + 10 for r in rows)
    out = Image.new("RGB", (W, H), "white"); y = 0
    for r in rows: out.paste(r, (0, y)); y += r.height + 10
    out.save("out/crops_before_after.png"); print(out.size)
