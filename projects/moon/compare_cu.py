"""compare_<element>.png from the FINAL stitch files: close-up (tracing reference) | the DST itself drawn stitch by stitch
(thread colours, 0.35 mm thread width), same scale, same framing."""
import json, math
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw
import moonpal, closeart as CA

A = json.load(open("out/results/all.json")); M = A["sizes"]["M"]; B = A["grades"]["B"]
def dst_img(entries, mmbox, ppm, bg=(37, 48, 77)):
    x0, y0, x1, y1 = mmbox
    im = Image.new("RGB", (int((x1 - x0) * ppm), int((y1 - y0) * ppm)), bg); d = ImageDraw.Draw(im)
    w = max(1, int(round(0.35 * ppm)))
    for r in entries:
        p = pe.read(r["file"] + ".pes"); cx, cy = r["centre"]; cols = [t.hex_color() for t in p.threadlist]; ci = 0; prev = None
        for x, y, c in p.stitches:
            k = c & pe.COMMAND_MASK; P = ((x / 10 + cx - x0) * ppm, (y / 10 + cy - y0) * ppm)
            if k == pe.STITCH:
                if prev: d.line([prev, P], fill=cols[min(ci, len(cols) - 1)], width=w)
                prev = P
            elif k == pe.COLOR_CHANGE: ci += 1; prev = None
            else: prev = None
    return im
cx, cy, r = CA.CU_MOON; s0 = 120.0 / r
def bmm(px, py): return ((px - cx) * s0, 244 + (py - cy) * s0)
def pair(name, img, pxbox, entries, mmbox, ppm):
    ours = dst_img(entries, mmbox, ppm); cu = img.crop(pxbox).resize(ours.size, Image.LANCZOS)
    out = Image.new("RGB", (ours.width * 2 + 20, ours.height + 24), "white"); d = ImageDraw.Draw(out)
    out.paste(cu, (0, 24)); out.paste(ours, (ours.width + 20, 24))
    d.text((4, 4), f"{name}: CLOSE-UP (left) | FINAL DST size M / grade B, drawn stitch by stitch (right)", fill=(200, 0, 0))
    out.save(f"out/compare_{name}.png")
back = [M["back"], M["moonbox"]]
for nm, box in (("01_moon", (440, 10, 1010, 580)), ("01_pole", (430, 480, 1040, 1086)), ("01_clouds_left", (20, 160, 660, 740)), ("01_clouds_right", (880, 260, 1448, 660))):
    a = bmm(box[0], box[1]); b = bmm(box[2], box[3]); pair(nm, CA.CB, box, back, (a[0], a[1], b[0], b[1]), 4)
pair("02_03_front", CA.CF, (0, 0, 1448, 1086), [M["03L"], M["03R"], B["02R"], B["02L"]], (-300, 60, 300, 512), 2.5)
import moonpattern, pattern as PT
g, mt = PT.draft("M")
for k, half in (("04R", (0, 0, 724, 1086)), ("04L", (724, 0, 1448, 1086))):
    sp = g["S01" if k == "04R" else "S02"].sew_poly().bounds
    pair(f"04_{k}", CA.CS, half, [B[k]], sp, 2.5)
print("ok")
