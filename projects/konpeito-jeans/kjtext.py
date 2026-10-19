"""Lettering traced from the mockup, drawn as clean strokes.

The traced text pixels are a blurred, ~1 px/stroke-edge picture of AI-rendered thread, so their outline is not a good
satin column. Each character is therefore REGISTERED on the traced pixels: a Zen Maru Gothic glyph (the mockup lettering
is a rounded gothic hand) is moved / scaled / rotated per character until it overlaps the traced character best (IoU),
and the per-character IoU is reported (qa.motif_match on the compare sheet). Position, size, tilt and weight per
character come from the mockup; the stroke outline comes from the font."""
import math
import numpy as np
from PIL import Image, ImageDraw
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import affinity

FONTS = {"bold": "inputs/fonts/ZenMaruGothic-Bold.ttf", "black": "inputs/fonts/ZenMaruGothic-Black.ttf"}
_F = {}

def bez(p0, p1, p2, p3, n=12):
    t = np.linspace(0, 1, n)[:, None]; p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return ((1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t**2*p2 + t**3*p3).tolist()

class FlatPen(BasePen):
    def __init__(self, gs): super().__init__(gs); self.contours = []; self.cur = []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, p1, p2, p3): self.cur += bez(self.cur[-1], p1, p2, p3, 12)[1:]
    def _qCurveToOne(self, p1, p2):
        p0 = np.array(self.cur[-1]); p1 = np.array(p1); p2 = np.array(p2)
        for t in np.linspace(0, 1, 10)[1:]: self.cur.append(tuple((1-t)**2*p0 + 2*(1-t)*t*p1 + t**2*p2))
    def _closePath(self):
        if len(self.cur) > 2: self.contours.append(self.cur)
        self.cur = []
    _endPath = _closePath

def glyph(ch, weight="bold"):
    """glyph outline, y down, height-normalised: ink box height = 1.0, centred on (0, 0)."""
    if weight not in _F:
        tt = TTFont(FONTS[weight]); _F[weight] = (tt.getGlyphSet(), tt.getBestCmap())
    gs, cmap = _F[weight]
    pen = FlatPen(gs); gs[cmap[ord(ch)]].draw(pen)
    g = Polygon()
    for c in sorted([Polygon(c).buffer(0) for c in pen.contours], key=lambda p: -p.area):
        g = g.symmetric_difference(c)
    g = affinity.scale(g.buffer(0), 1, -1, origin=(0, 0))
    b = g.bounds; h = b[3] - b[1]
    g = affinity.translate(g, -(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2)
    return affinity.scale(g, 1 / h, 1 / h, origin=(0, 0)), (b[2] - b[0]) / h

def raster(g, x0, y0, Wp, Hp, ppm):
    im = Image.new("L", (Wp, Hp), 0); d = ImageDraw.Draw(im)
    T = lambda cs: [((x - x0) * ppm, (y - y0) * ppm) for x, y in cs]
    for p in getattr(g, "geoms", [g]):
        if p.geom_type != "Polygon" or p.is_empty: continue
        d.polygon(T(p.exterior.coords), fill=255)
        for q in p.interiors: d.polygon(T(q.coords), fill=0)
    return np.array(im) > 127

def fit_line(text, mask, ppm, box, weight="bold", tilt=0.0):
    """mask: traced pixels of this text line (whole mockup grid, mm = px / ppm); box: (x0, y0, x1, y1) of the line in mm.
    Returns [dict(ch, geom, iou)] with each glyph registered on the traced pixels."""
    x0, y0, x1, y1 = box; H = y1 - y0
    gl = [glyph(c, weight) for c in text]
    # first guess: glyphs at line height, advance by width, spread over the box
    ws = [a for _, a in gl]; tot = sum(ws) * H * 0.92
    gap = ((x1 - x0) - tot) / max(1, len(text) - 1)
    # character centres: 1-D k-means of the traced pixels' x (weighted by the font advance for the start)
    ys_, xs_ = np.nonzero(mask); X = xs_ / ppm; Y = ys_ / ppm
    cs = []; x = x0
    for a in ws:
        w = a * H * 0.92; cs.append(x + w / 2); x += w + gap
    cs = np.array(cs)
    for _ in range(25):
        lab = np.argmin(np.abs(X[:, None] - cs[None, :]), 1)
        cs = np.array([X[lab == k].mean() if (lab == k).any() else cs[k] for k in range(len(cs))])
    out = []
    for k, (ch, (g, a)) in enumerate(zip(text, gl)):
        sel = lab == k
        cy = float((Y[sel].min() + Y[sel].max()) / 2) if sel.any() else (y0 + y1) / 2
        hh = float(Y[sel].max() - Y[sel].min()) if sel.any() else H
        st = dict(cx=float(cs[k]), cy=cy, s=max(H * 0.45, min(H * 1.2, hh)), r=tilt)
        out.append(dict(ch=ch, g=g, st=st))
    # coordinate descent per glyph on dice overlap with the traced pixels
    for it in range(2):
      for i, o in enumerate(out):
        st = o["st"]
        xa = (out[i-1]["st"]["cx"] + st["cx"]) / 2 if i else -1e9
        xb = (out[i+1]["st"]["cx"] + st["cx"]) / 2 if i + 1 < len(out) else 1e9
        def score(p, xa=xa, xb=xb, o=o):
            g = affinity.translate(affinity.rotate(affinity.scale(o["g"], p["s"], p["s"], origin=(0, 0)), p["r"], origin=(0, 0)), p["cx"], p["cy"])
            b = g.bounds; pad = 0.6
            bx0, by0 = b[0] - pad, b[1] - pad
            c0, r0 = int(bx0 * ppm), int(by0 * ppm)
            Wp, Hp = int((b[2] - b[0] + 2 * pad) * ppm) + 2, int((b[3] - b[1] + 2 * pad) * ppm) + 2
            gm = raster(g, c0 / ppm, r0 / ppm, Wp, Hp, ppm)
            mm = np.zeros_like(gm); sub = mask[max(0, r0):r0 + Hp, max(0, c0):c0 + Wp]
            mm[:sub.shape[0], :sub.shape[1]] = sub
            xs = (np.arange(Wp) + c0) / ppm; mm[:, (xs < xa) | (xs > xb)] = False
            inter = (gm & mm).sum(); return 2 * inter / max(gm.sum() + mm.sum(), 1) - 0.0, g
        best, _ = score(st)
        for step in (1.0, 0.5, 0.25, 0.12):
            improved = True
            while improved:
                improved = False
                for k, dv in (("cx", step), ("cx", -step), ("cy", step), ("cy", -step), ("s", step * 0.6), ("s", -step * 0.6),
                              ("r", step * 6), ("r", -step * 6)):
                    p = dict(st); p[k] += dv
                    if not (H * 0.42 < p["s"] < H * 1.35) or abs(p["r"] - tilt) > 14: continue
                    sc, _ = score(p)
                    if sc > best + 1e-4: best, st, improved = sc, p, True
        o["st"] = st; _, o["geom"] = score(st); o["dice"] = round(float(best), 3)
    return out
