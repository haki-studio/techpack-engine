"""compare_<element>.png from the FINAL stitch files (size M / grade B): close-up (tracing reference) | the DST itself
drawn stitch by stitch (thread colours, 0.42 mm thread width), same scale, same framing; plus a row of zoomed regions
(close-up | DST pairs at 3x the sheet scale). Back: one registration (moon) for close-up px -> mm.
Front / sleeves: the close-up and our placement differ (mockup placement), so zooms are framed per object."""
import json, math
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw
import moonpal, closeart as CA

A = json.load(open("out/results/all.json")); M = A["sizes"]["M"]; B = A["grades"]["B"]
_cache = {}
def dst_img(entries, mmbox, ppm, bg=(37, 48, 77)):
    x0, y0, x1, y1 = mmbox
    im = Image.new("RGB", (int((x1 - x0) * ppm), int((y1 - y0) * ppm)), bg); d = ImageDraw.Draw(im)
    w = max(1, int(round(0.42 * ppm)))
    for r in entries:
        if r["file"] not in _cache: _cache[r["file"]] = pe.read(r["file"] + ".pes")
        p = _cache[r["file"]]; cx, cy = r["centre"]; cols = [t.hex_color() for t in p.threadlist]; ci = 0; prev = None
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

def sheet(name, img, pxbox, entries, mmbox, ppm, zooms=(), note=""):
    """zooms: [(label, close-up px box, mm box)] — each drawn at 3x ppm"""
    ours = dst_img(entries, mmbox, ppm); cu = img.crop(pxbox).resize(ours.size, Image.LANCZOS)
    W = ours.width * 2 + 20
    zs = []
    for lab, zb, mb in zooms:
        zo = dst_img(entries, mb, ppm * 3); zc = img.crop(zb).resize(zo.size, Image.LANCZOS); zs.append((lab, zc, zo))
    zh = max([z[1].height for z in zs], default=0)
    # fit the zoom pairs in rows of the sheet width
    rows, cur, cw = [], [], 0
    for z in zs:
        w_ = z[1].width * 2 + 30
        if cur and cw + w_ > W: rows.append(cur); cur, cw = [], 0
        cur.append(z); cw += w_
    if cur: rows.append(cur)
    H = ours.height + 30 + sum(max(z[1].height for z in rw) + 26 for rw in rows)
    out = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(out)
    d.text((4, 4), f"{name}: CLOSE-UP (left) | FINAL DST size M / grade B, drawn stitch by stitch (right), same scale {ppm:g} px/mm. {note}", fill=(200, 0, 0))
    out.paste(cu, (0, 24)); out.paste(ours, (ours.width + 20, 24))
    y = ours.height + 30
    for rw in rows:
        x = 0
        for lab, zc, zo in rw:
            d.text((x + 2, y), f"zoom {lab} (x3): close-up | DST", fill=(200, 0, 0))
            out.paste(zc, (x, y + 14)); out.paste(zo, (x + zc.width + 6, y + 14)); x += zc.width * 2 + 30
        y += max(z[1].height for z in rw) + 26
    out.save(f"out/compare_{name}.png")

def bz(lab, px0, py0, px1, py1):
    a = bmm(px0, py0); b = bmm(px1, py1); return (lab, (px0, py0, px1, py1), (a[0], a[1], b[0], b[1]))

back = [M["back"], M["moonbox"]]
def bsheet(nm, box, zooms, ppm=4):
    a = bmm(box[0], box[1]); b = bmm(box[2], box[3]); sheet(nm, CA.CB, box, back, (a[0], a[1], b[0], b[1]), ppm, zooms)
bsheet("01_moon", (440, 10, 1010, 580), [bz("star crater", 600, 80, 700, 180), bz("cell rim ring", 450, 240, 550, 340),
                                          bz("star + centre", 800, 190, 900, 290), bz("swirl ground", 650, 330, 750, 430)])
bsheet("01_pole", (430, 480, 1040, 1086), [bz("pins + crossarm", 790, 520, 950, 640), bz("coil + spool", 450, 720, 610, 820),
                                            bz("drum transformer", 750, 660, 870, 870), bz("cone insulator", 760, 890, 880, 980)])
bsheet("01_clouds_left", (20, 160, 660, 740), [bz("dome + scales", 270, 180, 450, 280), bz("tail", 440, 280, 640, 340),
                                                bz("lower cloud", 150, 560, 400, 680)])
bsheet("01_clouds_right", (880, 260, 1448, 660), [bz("dome", 1100, 270, 1300, 380), bz("lower dome", 1080, 480, 1280, 580),
                                                  bz("tail", 1250, 560, 1440, 620)])
sheet("02_03_front", CA.CF, (0, 0, 1448, 1086), [M["03L"], M["03R"], B["02R"], B["02L"]], (-300, 60, 300, 512), 2.5,
      note="Front: our placement follows the mockup (close-up is framed differently) - compare shapes, not positions.")
import moonpattern, pattern as PT
g, mt = PT.draft("M")
for k, half in (("04R", (0, 0, 724, 1086)), ("04L", (724, 0, 1448, 1086))):
    sp = g["S01" if k == "04R" else "S02"].sew_poly().bounds
    sheet(f"04_{k}", CA.CS, half, [B[k]], sp, 2.5, note="Sleeve: 2 close-up views per sleeve -> one sleeve piece (back half | front half).")
print("ok")
