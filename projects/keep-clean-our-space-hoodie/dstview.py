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

def strokes(base, origin=None, only=None):
    """[(colour hex, [(x_mm, y_mm), ...] runs)] in garment mm; only = set of thread hex colours to keep"""
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
    if only is not None:
        keep = {c.lower() for c in only}; out = [(c, r) for c, r in out if c.lower() in keep]
    return out

def mask_as_sewn(base, bbox, ppm, only=None, thread=0.42):
    """stitched coverage AS SEWN: each stop's stitches drawn at the thread width minus 2 x the pull compensation of the
    stop's codes (tech.RULES; the pull-in that pull compensation cancels on fabric); only = thread hex colours"""
    import tech, dst2
    rp = os.path.join(os.path.dirname(base) if not base.endswith("") else os.path.dirname(base), f"result_{os.path.basename(base).split('_')[2]}.json")
    try:
        R = json.load(open(rp)); st = R["full"] if os.path.normpath(R["full"]["file"]) == os.path.normpath(base) else None
    except Exception: st = None
    pulls = [min([dst2.pull_for(c) for c in ps.get("codes", []) if c in tech.RULES] or [0.0]) for ps in (st["per_stop"] if st else [])]
    cx, cy = origin_of(base)
    cols = [t.hex_color() for t in pe.read(base + ".pes").threadlist]
    p = pe.read(base + ".dst"); x0, y0, x1, y1 = bbox; W, H = int((x1 - x0)*ppm), int((y1 - y0)*ppm)
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); keep = {c.lower() for c in only} if only else None
    ci = 0; run = []
    def flush():
        if len(run) > 1 and (keep is None or cols[min(ci, len(cols)-1)].lower() in keep):
            pl = pulls[ci] if ci < len(pulls) else 0.0
            d.line([((x - x0)*ppm, (y - y0)*ppm) for x, y in run], fill=255, width=max(1, int(round(max(0.1, thread - 2*pl)*ppm))))
    for x, y, cmd in p.stitches:
        c = cmd & pe.COMMAND_MASK
        if c == pe.STITCH: run.append((x/10 + cx, y/10 + cy)); continue
        flush(); run = []
        if c == pe.COLOR_CHANGE: ci += 1
        elif c == pe.END: break
    flush()
    return np.array(im) > 127

def mask(bases, bbox, ppm, only=None, width=0.42, origins=None):
    """bool mask (H x W) of the stitches (thread width `width` mm) of the given thread colours on a garment-mm grid"""
    x0, y0, x1, y1 = bbox; W, H = int((x1 - x0)*ppm), int((y1 - y0)*ppm)
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); wpx = max(1, int(round(width*ppm)))
    for i, b in enumerate(bases):
        for col, run in strokes(b, origins[i] if origins else None, only=only):
            d.line([((x - x0)*ppm, (y - y0)*ppm) for x, y in run], fill=255, width=wpx)
    return np.array(im) > 127

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
