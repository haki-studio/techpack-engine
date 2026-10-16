"""Cover / colourway images: technical flats (size M) with the stitch-rendered embroidery placed on them.
Sleeve clouds (sleeve pattern coords) are mapped onto the flat sleeves (front view = front half, back view = back half).
-> cover_front.png, cover_back.png"""
import pickle, io
import numpy as np
import cairosvg
from PIL import Image, ImageFilter
from shapely import affinity
from shapely.ops import transform
import moonpal, moonpattern, pattern as PT
import techflat as TF, stitchrender as SR

F = TF.Flat("M"); b = TF.bounds_front(F); ppm = 3.0
A = pickle.load(open("art_M.pkl", "rb")); G = pickle.load(open("art_graded.pkl", "rb"))
g, mt = PT.draft("M")

def flat_png(body):
    TF.K = 1.0 / ppm * 2.2
    W, H = b[2] - b[0] + 20, b[3] - b[1] + 20
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{b[0]-10} {b[1]-10} {W} {H}" width="{int(W*ppm)}" height="{int(H*ppm)}">'
           f'<rect x="{b[0]-10}" y="{b[1]-10}" width="{W}" height="{H}" fill="#fff"/>{body}</svg>')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")

def emb_layer(vis):
    rr = SR.Renderer(b[0] - 10, b[1] - 10, b[2] + 10, b[3] + 10, ppm)
    for r in vis: rr.region(r)
    im = rr.image(); a = im.split()[3]
    sh = Image.new("RGBA", im.size, (10, 12, 24, 0)); sh.putalpha(a.point(lambda v: int(v * 0.5))); sh = sh.filter(ImageFilter.GaussianBlur(1.2))
    base = Image.new("RGBA", im.size, (0, 0, 0, 0)); base.paste(sh, (1, 2))
    return Image.alpha_composite(base, im)

def sleeve_map(vis, side, half):
    """sleeve pattern coords -> flat sleeve (side +1 = viewer's right). half +1: x > 0 is the visible half."""
    sp = np.array(F.sp) * [side, 1]; ua = np.array(F.ua) * [side, 1]
    co = np.array(F.cuff_out) * [side, 1]; ci = np.array(F.cuff_in) * [side, 1]
    L = mt["cap_h"] + mt["Lu"]
    def f(x, y, z=None):
        xs, ys = np.atleast_1d(x), np.atleast_1d(y)
        t = np.clip((ys + mt["cap_h"]) / L, 0, 1)
        Wy = mt["W"] + (mt["Ww"] - mt["W"]) * np.clip(ys / mt["Lu"], 0, 1)
        fr = np.clip(half * xs / Wy, 0, 1)
        outer = sp[None, :] + (co - sp)[None, :] * t[:, None]; inner = ua[None, :] + (ci - ua)[None, :] * np.clip((ys) / mt["Lu"], 0, 1)[:, None]
        P = outer * (1 - fr[:, None]) + inner * fr[:, None]
        return P[:, 0], P[:, 1]
    # each cloud keeps its shape: centre mapped onto the flat sleeve, shape scaled to the flat sleeve width and turned with
    # the sleeve axis (pattern y runs along the sleeve). Indicative only — positions per size are on T13.
    from shapely.ops import unary_union as _uu
    sc = 0.5
    slv = F.sleeve(side).buffer(-4)
    ang = np.degrees(np.arctan2(*(co - sp)[::-1])) - 90
    clusters = [q for q in getattr(_uu([r["geom"].buffer(1.5) for r in vis]), "geoms", [_uu([r["geom"].buffer(1.5) for r in vis])])]
    out = []
    for q in clusters:
        c = q.centroid
        if half * c.x <= 0: continue
        X, Y = f(c.x, c.y); X, Y = float(X[0]), float(Y[0])
        for r in vis:
            if not q.contains(r["geom"].representative_point()): continue
            gg = affinity.translate(r["geom"], -c.x, -c.y)
            gg = affinity.scale(gg, sc, sc, origin=(0, 0))
            gg = affinity.rotate(gg, ang, origin=(0, 0))
            out.append(dict(r, geom=affinity.translate(gg, X, Y).buffer(0).intersection(slv)))
    return out

front_vis = [dict(r, geom=affinity.translate(r["geom"], 0, F.fnd)) for k in ("02R", "02L") for r in G[k]] + \
            [dict(r, geom=affinity.translate(r["geom"], 0, F.fnd)) for k in ("F03L", "F03R") for r in A[k]]
front_vis += sleeve_map(G["04R"], -1, +1) + sleeve_map(G["04L"], +1, -1)
fr = flat_png(TF.draw_front(F)); fr = Image.alpha_composite(fr, emb_layer(front_vis)); fr.convert("RGB").save("cover_front.png")
back_vis = [dict(r, geom=affinity.translate(r["geom"], 0, F.bnd)) for r in A["back"]]
back_vis += sleeve_map(G["04R"], +1, -1) + sleeve_map(G["04L"], -1, +1)
bk = flat_png(TF.draw_back(F)); bk = Image.alpha_composite(bk, emb_layer(back_vis))
# licensed-figure placeholder box drawn on the back cover
from PIL import ImageDraw
x0, y0, x1, y1 = A["info"]["box"]; y0 += F.bnd; y1 += F.bnd
P = lambda x, y: ((x - b[0] + 10) * ppm, (y - b[1] + 10) * ppm)
d = ImageDraw.Draw(bk); d.rectangle([P(x0, y0), P(x1, y1)], outline=(255, 45, 155, 255), width=3)
d.line([P(x0, y0), P(x1, y1)], fill=(255, 45, 155, 255), width=1); d.line([P(x1, y0), P(x0, y1)], fill=(255, 45, 155, 255), width=1)
bk.convert("RGB").save("cover_back.png"); print(fr.size)
