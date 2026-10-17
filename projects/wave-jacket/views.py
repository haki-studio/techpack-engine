"""Garment views (flat lay, as the render shows it) assembled from the per-size pattern-piece art: body pieces in their
own garment mm, each visible sleeve half carried back into the flat lay through its sleeve map (pattern -> render px ->
body mm). Used for the covers, G2, the element spec and the compare overview, so every picture of the jacket is the
real stitch art on the real pattern, laid out like the mockup.
  img, bbox, X = view_png("back", "M", ppm=2.0)      X(x, y) -> image px for garment mm"""
import wavecore as WC
import pickle, functools
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import stitchrender as SR, mockmap as MM, pieces as PC
import front as FRT

BODY = {"back": ["BK"], "front": ["FR", "FL"]}
SLEEVES = {"back": [("SL", "L"), ("SR", "R")], "front": [("SR", "R"), ("SL", "L")]}

@functools.lru_cache(maxsize=None)
def art(size): return pickle.load(open(f"art_{size}.pkl", "rb"))

def sleeve_to_view(view, side, size):
    sm = MM.sleeve_map(view, side, size); f, finv = MM.body_tf(view, size)
    def g(x, y):
        q = sm.inv(np.c_[np.atleast_1d(x), np.atleast_1d(y)]); return f(q[:, 0], q[:, 1])
    return sm, g

def view_regions(view, size):
    """[(region dict in view mm)], sleeve outline polys (view mm), body panels"""
    A = art(size); out = []
    pans = [PC.panel(size, P) for P in BODY[view]]
    for P in BODY[view]: out += [dict(r, _z=0) for r in A[P]]
    sl = []
    for P, side in SLEEVES[view]:
        sm, g = sleeve_to_view(view, side, size); f, _ = MM.body_tf(view, size)
        half = box(0, -400, 400, 900) if sm.sgn > 0 else box(-400, -400, 0, 900)
        q = np.array(sm.quad_px.exterior.coords); X, Y = f(q[:, 0], q[:, 1]); sl.append(Polygon(np.c_[X, Y]).buffer(0))
        for r in A[P]:
            gg = r["geom"].intersection(half)
            if gg.is_empty: continue
            out.append(dict(r, geom=MM.map_geom(gg, g, densify=1.0).buffer(0), _z=1))
    return out, sl, pans

def view_png(view, size="M", ppm=2.0, pad=12):
    regs, sl, pans = view_regions(view, size)
    g_, mt = MM.draft(size)
    hem = mt["hem_b"] if view == "back" else mt["hem_f"]
    U = unary_union(sl + pans); b = U.bounds; bb = (b[0] - pad, b[1] - pad - 60, b[2] + pad, max(hem + 90, b[3] + 80))
    W, H = int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm)
    T = lambda cs: [((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in cs]
    base = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(base)
    fab = tuple(int(WC.FABRIC[i:i + 2], 16) for i in (1, 3, 5)); rib = (30, 36, 52)
    # rib hem + cuffs
    sw = drum_sweep(size)
    d.rectangle([T([(-sw, hem)])[0], T([(sw, hem + 55)])[0]], fill=rib, outline=(80, 80, 90))
    for P, side in SLEEVES[view]:
        sm = MM.sleeve_map(view, side, size); f, _ = MM.body_tf(view, size)
        co, ci = MM.CUFF_PX[(view, side)]; a_ = np.array(f(*np.array([co, ci]).T)).T
        d.polygon(T([tuple(a_[0]), tuple(a_[1]), (a_[1][0], a_[1][1] + 70), (a_[0][0], a_[0][1] + 70)]), fill=rib, outline=(80, 80, 90))
    for p in pans: d.polygon(T(p.exterior.coords), fill=fab, outline=(70, 75, 95))
    # body art
    img = SR.render([r for r in regs if r["_z"] == 0], bb, ppm, base=WC.FABRIC)
    m = Image.new("L", (W, H), 0); md = ImageDraw.Draw(m)
    for p in pans: md.polygon(T(p.exterior.coords), fill=255)
    base.paste(img, (0, 0), m)
    if view == "front":
        for w_ in (FRT.WELT_R, FRT.WELT_L): d.polygon(T(w_.exterior.coords), fill=(22, 26, 40), outline=(110, 115, 135))
        d.rectangle([T([(-6, 0)])[0], T([(6, hem + 55)])[0]], fill=(160, 125, 60))
        for c in (FRT.COLLAR_R, FRT.COLLAR_L): d.polygon(T(c.exterior.coords), fill=(30, 35, 50), outline=(90, 95, 115))
    else:
        nk = [p for p in pans][0]; nb = nk.bounds
        d.polygon(T([(-100, -30), (100, -30), (95, 28), (0, 34), (-95, 28)]), fill=(30, 35, 50), outline=(90, 95, 115))
    # sleeves on top (the flat lay lays them over the body sides)
    simg = SR.render([r for r in regs if r["_z"] == 1], bb, ppm, base=WC.FABRIC)
    for s_ in sl:
        m2 = Image.new("L", (W, H), 0); ImageDraw.Draw(m2).polygon(T(s_.exterior.coords), fill=255)
        base.paste(simg, (0, 0), m2); d.line(T(s_.exterior.coords), fill=(70, 75, 95), width=2)
    X = lambda x, y: ((x - bb[0]) * ppm, (y - bb[1]) * ppm)
    return base, bb, X

def drum_sweep(size):
    import drum
    return drum.m("D", size) / 2

if __name__ == "__main__":
    import sys
    sz = sys.argv[1] if len(sys.argv) > 1 else "M"
    for v in ("back", "front"):
        im, bb, X = view_png(v, sz, 2.0); im.save(f"out/view_{v}_{sz}.png"); print(v, im.size)
