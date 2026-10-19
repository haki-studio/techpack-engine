"""Fidelity sheets: out/compare_<piece>.png (mockup crop | stitch render at the same scale, + 4 zoomed pairs; mockup zooms
Lanczos x4 from the source) and out/compare_<size>.png (both fronts).  usage: python3 compare.py [size]"""
import cccore, pickle, sys, os
from PIL import Image, ImageDraw, ImageFilter
import stitchrender as SR, mockmap as MM
import front as F

size = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "art" else "M"
FROM_DST = "art" not in sys.argv
import json, math
import numpy as np
import pyembroidery as pe
_DST = {}
def _stitches(P):
    if P not in _DST:
        rp = f"{cccore.edir(P)}/{size}/result_{P}.json"
        r = json.load(open(rp))["full"]; ox, oy = r["origin"]
        d = pe.read(r["file"] + ".dst"); cols = [t.hex_color() for t in pe.read(r["file"] + ".pes").threadlist]
        segs = []; ci = 0; prev = None
        for x, y, c in d.stitches:
            cmd = c & pe.COMMAND_MASK
            X, Y = x / 10.0 + ox, y / 10.0 + oy
            if cmd == pe.STITCH:
                if prev is not None: segs.append((prev, (X, Y), ci))
                prev = (X, Y)
            elif cmd == pe.COLOR_CHANGE: ci += 1; prev = None
            elif cmd in (pe.JUMP, pe.TRIM): prev = None if cmd == pe.TRIM else (X, Y)
        _DST[P] = (segs, cols)
    return _DST[P]
def dst_render(Ps, bb, ppm, base=None):
    k = 2; W, H = int((bb[2]-bb[0])*ppm*k), int((bb[3]-bb[1])*ppm*k)
    fab = SR.fabric(W, H, ppm*k, base=cccore.FABRIC) if hasattr(SR, "fabric") else None
    im = (fab.convert("RGB") if fab is not None else Image.new("RGB", (W, H), cccore.FABRIC))
    d = ImageDraw.Draw(im); lw = max(1, int(round(0.32*ppm*k)))
    for P in Ps:
        segs, cols = _stitches(P)
        for (a, b, ci) in segs:
            if max(a[0], b[0]) < bb[0] or min(a[0], b[0]) > bb[2] or max(a[1], b[1]) < bb[1] or min(a[1], b[1]) > bb[3]: continue
            if math.hypot(b[0]-a[0], b[1]-a[1]) > 7.6: continue
            col = cols[min(ci, len(cols)-1)]
            d.line([((a[0]-bb[0])*ppm*k, (a[1]-bb[1])*ppm*k), ((b[0]-bb[0])*ppm*k, (b[1]-bb[1])*ppm*k)], fill=col, width=lw)
    return im.resize((W//k, H//k), Image.LANCZOS)
D = pickle.load(open(f"art_{size}.pkl", "rb"))
ZOOMS = {"FR": [((-200, 20, -110, 95), "stars + meteor"), ((-75, 200, 5, 275), "comet head through the clouds"),
                ((-215, 130, -125, 205), "cloud tones"), ((-250, 400, -150, 500), "city, railing, bicycle")],
         "FL": [((60, 20, 180, 120), "comet tail strands"), ((30, 230, 110, 305), "falling star + clouds"),
                ((20, 380, 110, 490), "figure at the railing, windows"), ((190, 290, 290, 400), "lamp post, bush, far towers")],
         "SR": [((0, 60, 110, 160), "stars + meteor"), ((0, 300, 110, 400), "plant rosettes + fireflies"), ((60, 200, 170, 300), "clouds")],
         "SL": [((-110, 20, 0, 120), "stars"), ((-110, 300, 0, 400), "plant rosettes"), ((-170, 160, -60, 260), "clouds + leaves")]}

def welts(img, bb, ppm, P):
    if P not in ("FR", "FL"): return
    d_ = ImageDraw.Draw(img); w_ = F.keep_geoms(size, "R" if P == "FR" else "L")["welt"]
    d_.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in w_.exterior.coords], fill=(26, 32, 48), outline=(120, 130, 150))

def mock(P, bb, ppm):
    if P in ("FR", "FL"): return MM.warp(bb, ppm)
    return MM.swarp("R" if P == "SR" else "L", bb, ppm)

def pair(P, bb, ppm, vis):
    st = dst_render([P], bb, ppm) if FROM_DST else SR.render(vis, bb, ppm, base=cccore.FABRIC)
    welts(st, bb, ppm, P)
    mk = mock(P, bb, ppm / 4.0).resize(st.size, Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
    return mk, st

def sheet(P, zooms=None):
    vis = D[P]
    if P == "FR": b = (-300, -40, -5, 515)
    elif P == "FL": b = (5, -40, 300, 515)
    else:
        bx = D["info"][P]["bbox"]; b = (bx[0] - 10, bx[1] - 10, bx[2] + 10, bx[3] + 10)
    ppm = 2.0
    mk, st = pair(P, b, ppm, vis)
    W, H = st.size; zw = 420
    zooms = ZOOMS.get(P) if zooms is None else zooms
    out = Image.new("RGB", (W*2 + 40 + (zw*2 + 20 if zooms else 0), max(H + 40, 4*(zw*6//7 + 40) + 40)), (255, 255, 255))
    out.paste(mk, (10, 30)); out.paste(st, (W + 30, 30)); d = ImageDraw.Draw(out)
    d.text((10, 10), f"MOCKUP {P} (mapped to size-M mm)", fill=(0, 0, 0)); d.text((W + 30, 10), f"{'DST STITCHES' if FROM_DST else 'ART RENDER'} {P} size {size} (same scale, read from the written .dst)", fill=(0, 0, 0))
    x0 = W*2 + 50; y = 30
    for (zb, cap) in zooms:
        zp = zw / (zb[2] - zb[0])
        a, s_ = pair(P, zb, zp, vis); hh = a.height
        out.paste(a, (x0, y)); out.paste(s_, (x0 + zw + 10, y)); d.text((x0, y - 14), f"{cap}  x {zb[0]}..{zb[2]}, y {zb[1]}..{zb[3]} mm  (mockup x4 | render)", fill=(0, 0, 0))
        for (X, Y) in ((10, 30), (W + 30, 30)):
            d.rectangle([X + (zb[0]-b[0])*ppm, Y + (zb[1]-b[1])*ppm, X + (zb[2]-b[0])*ppm, Y + (zb[3]-b[1])*ppm], outline=(255, 60, 60), width=2)
        y += hh + 30
    os.makedirs("out", exist_ok=True)
    out.save(f"out/compare_{P}.png"); return out.size

if __name__ == "__main__":
    print(sheet("FR"), sheet("FL"))
    for P in ("SR", "SL"):
        if P in D: print(sheet(P))
    bb = (-300, -60, 300, 520); ppm = 2.0
    st = dst_render(["FR", "FL"], bb, ppm) if FROM_DST else SR.render(D["FR"] + D["FL"], bb, ppm, base=cccore.FABRIC)
    mk = MM.warp(bb, ppm)
    welts(st, bb, ppm, "FR"); welts(st, bb, ppm, "FL")
    _d = ImageDraw.Draw(st); _d.rectangle([(-6 - bb[0])*ppm, (0 - bb[1])*ppm, (6 - bb[0])*ppm, (520 - bb[1])*ppm], fill=(160, 125, 60))
    W, H = st.size; out = Image.new("RGB", (W*2 + 20, H + 30), (255, 255, 255)); out.paste(mk, (0, 30)); out.paste(st, (W + 20, 30))
    d = ImageDraw.Draw(out); d.text((10, 8), "MOCKUP (mapped to size M mm)", fill=(0, 0, 0)); d.text((W + 30, 8), f"{'DST STITCHES (read from the written files)' if FROM_DST else 'ART RENDER'} size {size}", fill=(0, 0, 0))
    out.save(f"out/compare_{size}.png"); st.save(f"out/render_{size}.png")
