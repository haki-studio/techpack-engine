"""Render WRITTEN stitch files (DST read back, thread colours from the PES) in garment mm — the only renderer the compare
sheets use (review Rev A item 1: nothing on a compare sheet is drawn from the art regions).
Each sewn stitch is drawn as a thread: a 0.42 mm line at 80 % of the thread colour under a 0.20 mm core at 110 %, so satin direction,
crossing rows and fans are visible exactly as the machine will sew them. Jumps/trims are not drawn.
  img = dstview.image(["out/stitch/M/HAKI_KCOS_FR_M"], bbox_mm, ppm, origins=[(cx, cy)])
usage: python3 dstview.py <base> <x0> <y0> <x1> <y1> <out.png> [ppm]   (garment mm; origin read from result json)"""
import json, os, sys
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw

FABRIC = (25, 28, 36)

def _shade(hexc, k):
    c = tuple(int(hexc[i:i+2], 16) for i in (1, 3, 5))
    if k >= 1: return tuple(int(v + (255 - v)*(k - 1)) for v in c)
    return tuple(int(v*k) for v in c)

def origin_of(base):
    """the garment-mm point the DST is centred on (result_<P>.json 'origin' for the full file or the split section)."""
    d = os.path.dirname(base); P = os.path.basename(base).split("_")[2]
    rp = os.path.join(d if not d.endswith("splits") else os.path.dirname(d), f"result_{P}.json")
    r = json.load(open(rp))
    if os.path.normpath(r["full"]["file"]) == os.path.normpath(base): return tuple(r["full"]["origin"])
    for s in r.get("splits", {}).get("sections", {}).values():
        if os.path.normpath(s["file"]) == os.path.normpath(base): return tuple(s["origin"])
    raise KeyError(base)

def strokes(base, origin=None):
    """[(colour hex, [(x_mm, y_mm), ...] runs)] in garment mm"""
    cx, cy = origin or origin_of(base)
    cols = [t.hex_color() for t in pe.read(base + ".pes").threadlist]
    p = pe.read(base + ".dst"); ci = 0; run = []; out = []
    for x, y, cmd in p.stitches:
        c = cmd & pe.COMMAND_MASK
        if c == pe.STITCH: run.append((x/10 + cx, y/10 + cy)); continue
        if len(run) > 1: out.append((cols[min(ci, len(cols)-1)], run))
        run = []
        if c == pe.COLOR_CHANGE: ci += 1
        elif c == pe.END: break
    if len(run) > 1: out.append((cols[min(ci, len(cols)-1)], run))
    return out

def image(bases, bbox, ppm, origins=None, bg=FABRIC, ss=2):
    """bg=None -> RGBA with a transparent background (stitches only, for placing on flats)"""
    x0, y0, x1, y1 = bbox; W, H = int((x1 - x0)*ppm), int((y1 - y0)*ppm)
    S = ppm*ss; im = Image.new("RGBA" if bg is None else "RGB", (W*ss, H*ss), (0, 0, 0, 0) if bg is None else bg); d = ImageDraw.Draw(im)
    we, wc = max(1, int(round(0.42*S))), max(1, int(round(0.20*S)))
    for i, b in enumerate(bases):
        for col, run in strokes(b, origins[i] if origins else None):
            pts = [((x - x0)*S, (y - y0)*S) for x, y in run]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            if max(xs) < 0 or min(xs) > W*ss or max(ys) < 0 or min(ys) > H*ss: continue
            dk, lt = _shade(col, 0.80), _shade(col, 1.10)
            for a, c in zip(pts, pts[1:]):
                d.line([a, c], fill=dk, width=we)
            for a, c in zip(pts, pts[1:]):
                d.line([a, c], fill=lt, width=wc)
    return im.resize((W, H), Image.LANCZOS) if ss > 1 else im

if __name__ == "__main__":
    a = sys.argv
    image([a[1]], tuple(map(float, a[2:6])), float(a[7]) if len(a) > 7 else 8).save(a[6])
