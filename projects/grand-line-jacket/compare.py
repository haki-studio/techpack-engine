"""Fidelity sheets: out/compare_FR.png + out/compare_FL.png (mockup crop | stitch render at the same scale, + 4 zoomed pairs,
mockup zooms Lanczos x4 from the source), and out/compare_<size>.png (both pieces).  usage: python3 compare.py [size]"""
import glcore, pickle, sys
from PIL import Image, ImageDraw, ImageFilter
import stitchrender as SR, mockmap as MM

size = sys.argv[1] if len(sys.argv) > 1 else "M"
D = pickle.load(open(f"front_{size}.pkl", "rb"))
ZOOMS = {"FR": [((-270, 70, -200, 130), "bank top: lobe rows + tones"), ((-220, 190, -150, 250), "bank base + sea under it"),
                ((-120, 300, -50, 360), "islets + dashed rays"), ((-200, 30, -130, 90), "stars")],
         "FL": [((20, 150, 90, 210), "sun, burst, glow"), ((190, 100, 260, 160), "bank top: lobe rows + tones"),
                ((30, 220, 100, 280), "glitter path + sea dashes"), ((80, 340, 150, 400), "bottom islet + lower sea")]}

import front as F, json, os
import pyembroidery as pe
from PIL import ImageDraw as _ID2
_PATS = {}
def dst_pats():
    """the SHIPPED full stitch files of this size (+ origins from result json): what the factory gets"""
    if not _PATS:
        for P in ("FR", "FL"):
            r = json.load(open(f"out/01_front-scene/{size}/result_{P}.json"))["full"]
            from motifs2 import HEX as _HX
            dp = pe.read(r["file"] + ".dst")
            cols = [_HX[s["col"]] for s in r["per_stop"]]          # colour per DST stop from the read-back record (PES dedupes repeats)
            _PATS[P] = (dp, cols, r["origin"], os.path.getmtime(r["file"] + ".dst"))
    return _PATS
def dst_render(bb, ppm):
    """stitch-by-stitch render of the shipped DSTs (travel stitches included, jumps/trims not drawn)"""
    x0, y0, x1, y1 = bb; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    im = Image.new("RGB", (W, H), tuple(int(glcore.FABRIC[i:i+2], 16) for i in (1, 3, 5))); d = _ID2.Draw(im)
    lw = max(1, int(round(0.42*ppm)))
    for P, (p, cols, (ox, oy), _) in dst_pats().items():
        ci = 0; prev = None
        for x, y, cmd in p.stitches:
            k = cmd & pe.COMMAND_MASK; q = ((x/10 + ox - x0)*ppm, (y/10 + oy - y0)*ppm)
            if k == pe.STITCH:
                if prev is not None: d.line([prev, q], fill=cols[min(ci, len(cols)-1)], width=lw)
                prev = q
            elif k == pe.COLOR_CHANGE: ci += 1; prev = None
            elif k in (pe.TRIM, pe.JUMP): prev = None
    return im
from PIL import ImageDraw as _ID
def pair(bb, ppm, vis):
    st = dst_render(bb, ppm)
    d_ = _ID.Draw(st)
    for s_ in "RL":           # welt boxes of this size (keep-out holes are the pockets)
        w_ = F.keep_geoms(size, s_)["welt"]
        d_.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in w_.exterior.coords], fill=(30, 35, 52), outline=(120, 130, 150))
    mk = MM.warp(bb, ppm / 4.0).resize(st.size, Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
    return mk, st

def sheet(P):
    vis = D[P]; b = (-300, -40, -5, 470) if P == "FR" else (5, -40, 300, 470); ppm = 2.0
    mk, st = pair(b, ppm, vis)
    W, H = st.size; zw = 420
    out = Image.new("RGB", (W*2 + 40 + zw*2 + 20, max(H, 4*(zw*6//7 + 30)) + 40), (255, 255, 255))
    out.paste(mk, (10, 30)); out.paste(st, (W + 30, 30)); d = ImageDraw.Draw(out)
    d.text((10, 10), f"MOCKUP {P} (front.png mapped to size-M mm)", fill=(0, 0, 0)); d.text((W + 30, 10), f"SHIPPED DST {P} size {size} (same scale)", fill=(0, 0, 0))
    x0 = W*2 + 50; y = 30
    for (zb, cap) in ZOOMS[P]:
        zp = zw / (zb[2] - zb[0])
        a, s_ = pair(zb, zp, vis); hh = a.height
        out.paste(a, (x0, y)); out.paste(s_, (x0 + zw + 10, y)); d.text((x0, y - 14), f"{cap}  x {zb[0]}..{zb[2]}, y {zb[1]}..{zb[3]} mm  (mockup x4 | render)", fill=(0, 0, 0))
        for (X, Y) in ((10, 30), (W + 30, 30)):
            d.rectangle([X + (zb[0]-b[0])*ppm, Y + (zb[1]-b[1])*ppm, X + (zb[2]-b[0])*ppm, Y + (zb[3]-b[1])*ppm], outline=(255, 60, 60), width=2)
        y += hh + 30
    out.save(f"out/compare_{P}.png"); return out.size

if __name__ == "__main__":
    print(sheet("FR"), sheet("FL"))
    bb = (-300, -60, 300, 480); ppm = 2.0
    st = dst_render(bb, ppm); mk = MM.warp(bb, ppm)
    _d = ImageDraw.Draw(st)
    for s_ in "RL":
        w_ = F.keep_geoms(size, s_)["welt"]; _d.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in w_.exterior.coords], fill=(30, 35, 52), outline=(120, 130, 150))
    _d.rectangle([(-6 - bb[0])*ppm, (0 - bb[1])*ppm, (6 - bb[0])*ppm, (480 - bb[1])*ppm], fill=(160, 125, 60))
    W, H = st.size; out = Image.new("RGB", (W*2 + 20, H + 30), (255, 255, 255)); out.paste(mk, (0, 30)); out.paste(st, (W + 20, 30))
    d = ImageDraw.Draw(out); d.text((10, 8), "MOCKUP (mapped to size M mm)", fill=(0, 0, 0)); d.text((W + 30, 8), f"SHIPPED DST FILES size {size} (stitch-by-stitch)", fill=(0, 0, 0))
    out.save(f"out/compare_{size}.png"); st.save(f"out/render_{size}.png")
