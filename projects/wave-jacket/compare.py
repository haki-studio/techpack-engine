"""Fidelity sheets: out/compare_<piece>.png = the render mapped into that piece's pattern mm (same map the art uses) |
stitch preview of the region art at the same scale, + 4 zoomed pairs (render zooms Lanczos x4 from the source, which adds
no detail). Plus out/compare_<size>.png with all five pieces.  usage: ./py.sh compare.py [size]"""
import wavecore as WC
import pickle, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import box
from shapely.ops import unary_union
import stitchrender as SR, mockmap as MM, pieces as PC

size = sys.argv[1] if len(sys.argv) > 1 else "M"
D = pickle.load(open(f"art_{size}.pkl", "rb"))
VIEWS = {"BK": [("back", None)], "FR": [("front", None)], "FL": [("front", None)],
         "SR": [("back", "R"), ("front", "R")], "SL": [("back", "L"), ("front", "L")]}

def mock(P, bb, ppm):
    W, H = int((bb[2]-bb[0])*ppm), int((bb[3]-bb[1])*ppm)
    if P in ("BK", "FR", "FL"):
        im = MM.warp_body(VIEWS[P][0][0], size, bb, ppm)
    else:
        out = np.full((H, W, 3), 255, np.uint8)
        XX, YY = np.meshgrid(bb[0] + (np.arange(W) + 0.5) / ppm, bb[1] + (np.arange(H) + 0.5) / ppm)
        for view, side in VIEWS[P]:
            sm = MM.sleeve_map(view, side, size); a = np.asarray(MM.warp_sleeve(view, side, size, bb, ppm))
            q = sm.inv(np.c_[XX.ravel(), YY.ravel()])
            from shapely import contains_xy
            m = ((XX * sm.sgn) >= 0) & contains_xy(sm.quad_px, q[:, 0], q[:, 1]).reshape(XX.shape)
            out[m] = a[m]
        im = Image.fromarray(out)
    # outside the panel: white
    pan = PC.panel(size, P); msk = Image.new("L", im.size, 0); d = ImageDraw.Draw(msk)
    d.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in pan.exterior.coords], fill=255)
    wh = Image.new("RGB", im.size, (255, 255, 255)); wh.paste(im, (0, 0), msk)
    return wh

def stitch(P, bb, ppm):
    st = SR.render(D[P], bb, ppm, base=WC.FABRIC)
    pan = PC.panel(size, P); msk = Image.new("L", st.size, 0); d = ImageDraw.Draw(msk)
    d.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in pan.exterior.coords], fill=255)
    wh = Image.new("RGB", st.size, (255, 255, 255)); wh.paste(st, (0, 0), msk)
    d2 = ImageDraw.Draw(wh)
    d2.line([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in PC.clip_for(size, P).exterior.coords], fill=(255, 80, 80), width=1)
    return wh

def zooms(P, n=4, w=70.0, h=60.0):
    vis = D[P]; foam = unary_union([r["geom"] for r in vis if r["grp"] in ("FM", "FM-sh", "FM-gr")])
    band = unary_union([r["geom"] for r in vis if r["grp"] in ("WV", "RP")]); drop = unary_union([r["geom"] for r in vis if r["grp"] == "DR"])
    b = unary_union([r["geom"] for r in vis]).bounds; cands = []
    for x in np.arange(b[0], b[2] - w * 0.6, w / 3):
        for y in np.arange(b[1], b[3] - h * 0.6, h / 3):
            bx = box(x, y, x + w, y + h)
            fa, ba, da = foam.intersection(bx).area, band.intersection(bx).area, drop.intersection(bx).area
            cands.append((fa * 1.0 + ba * 0.6 + da * 3 + 2 * min(fa, ba), bx))
    cands.sort(key=lambda t: -t[0]); out = []
    for sc, bx in cands:
        if all(not bx.buffer(-5).intersects(o) for o in out): out.append(bx)
        if len(out) == n: break
    return [o.bounds for o in out]

def sheet(P, ppm=1.6):
    b0 = PC.panel(size, P).bounds; bb = (b0[0] - 5, b0[1] - 5, b0[2] + 5, b0[3] + 5)
    mk, st = mock(P, bb, ppm), stitch(P, bb, ppm)
    W, H = st.size; zw = 360; Z = zooms(P)
    out = Image.new("RGB", (W*2 + 40 + zw*2 + 30, max(H + 40, 4*(zw*6//7 + 34) + 30)), (255, 255, 255))
    out.paste(mk, (10, 30)); out.paste(st, (W + 30, 30)); d = ImageDraw.Draw(out)
    d.text((10, 10), f"RENDER {P} {PC.NAME[P]} (mockup mapped to size-{size} pattern mm)", fill=(0, 0, 0))
    d.text((W + 30, 10), f"STITCH PREVIEW {P} size {size} (same scale; red = keep-out line)", fill=(0, 0, 0))
    x0 = W*2 + 50; y = 30
    for zb in Z:
        zp = zw / (zb[2] - zb[0])
        a = mock(P, zb, zp / 4.0).resize((zw, int((zb[3]-zb[1])*zp)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
        s_ = stitch(P, zb, zp)
        out.paste(a, (x0, y)); out.paste(s_, (x0 + zw + 10, y))
        d.text((x0, y - 13), f"x {zb[0]:.0f}..{zb[2]:.0f}, y {zb[1]:.0f}..{zb[3]:.0f} mm  (render x4 | stitch preview)", fill=(0, 0, 0))
        for (X, Y) in ((10, 30), (W + 30, 30)):
            d.rectangle([X + (zb[0]-bb[0])*ppm, Y + (zb[1]-bb[1])*ppm, X + (zb[2]-bb[0])*ppm, Y + (zb[3]-bb[1])*ppm], outline=(255, 60, 60), width=2)
        y += a.height + 34
    out.save(f"out/compare_{P}.png"); return out.size

if __name__ == "__main__":
    for P in PC.PIECES: print(P, sheet(P))
