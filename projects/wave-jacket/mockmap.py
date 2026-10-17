"""Mockup (inputs/back.png 620x886, inputs/front.png 640x886) <-> garment mm, per size.

The render is one low-res AI image (~1.4 mm per px), not a flat pattern: its body is narrower + longer than the Drum
Island block and its sleeves are long and narrow. Landmarks (read off the zoomed mockup):
  back : CB x = 305 px, CB neck seam y = 164 px, hem-rib seam y = 677 px (585 mm on M), hem rib 395 px wide (= D 580 mm)
  front: CF x = 329 px, CF neck seam y = 250 px, hem-rib seam y = 660 px (510 mm on M), hem rib 394 px wide
Body pieces: x and y scale separately (SX 1.45 mm/px from the rib width, SY from neck -> hem seam) so the art keeps its
place on the panel. Motifs that must stay round (foam crests, spray drops) are moved by that map but keep their own
shape at the mean scale S = sqrt(SX*SY) (no oval curls).
Sleeves: the visible half of each sleeve in the render (armhole seam -> cuff seam) is mapped onto that half of the
sleeve PATTERN with a Coons patch whose top edge is the size's own armhole (pattern armhole drawn back into the image),
so art that crosses the armhole on the render meets the cap seam where the body art leaves it, on every size.
Every size uses its own pattern (art grade A/B/C scales the body map about the neck point, LESSONS A5)."""
import math, functools
import numpy as np
from PIL import Image
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import transform
import pattern as PT, drum

GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
VIEW = {
    "back":  dict(img="inputs/back.png",  cx=305.0, ny=164.0, SX=1.45, SY=585.0 / (677 - 164)),
    "front": dict(img="inputs/front.png", cx=329.0, ny=250.0, SX=1.45, SY=510.0 / (660 - 250)),
}
# cuff-seam corners of each visible sleeve half in the render (px): (outer fold end, inner end)
CUFF_PX = {("back", "L"): ((8, 762), (120, 751)), ("back", "R"): ((592, 768), (486, 760)),
           ("front", "R"): ((38, 768), (145, 760)), ("front", "L"): ((600, 778), (493, 758))}
# which sleeve + which half shows in each view. Pattern S01 = RIGHT sleeve (back half x < 0), S02 = LEFT (mirror: back half x > 0)
# side letters: wearer's R / L. Back view: wearer's L on the viewer's left. Front view: wearer's R on the viewer's left.
HALF = {("back", "L"): ("S02", +1), ("back", "R"): ("S01", -1), ("front", "R"): ("S01", +1), ("front", "L"): ("S02", -1)}

@functools.lru_cache(maxsize=None)
def silhouette(view):
    """jacket mask of the render (background = near-white)"""
    from scipy import ndimage as ndi
    a = np.asarray(Image.open(VIEW[view]["img"]).convert("RGB")).astype(float)
    near_white = (a.min(-1) > 238) & ((a.max(-1) - a.min(-1)) < 10)       # studio background (foam is <= 240 and warmer)
    lab, n = ndi.label(near_white); edge = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    bg = np.isin(lab, edge[edge > 0]) | (a.min(-1) > 249)
    bg = ndi.binary_opening(bg, iterations=1)
    m = ndi.binary_fill_holes(ndi.binary_opening(~bg, iterations=2))
    lab, n = ndi.label(m); sz = ndi.sum(m, lab, range(1, n + 1)); m = lab == (np.argmax(sz) + 1)
    m[:, 625:] &= view != "front"            # front.png shows a sliver of the back view at x >= 630
    return m

def outer_contour(view, side, y0, y1, step=6):
    """outer fold of a sleeve on the render: the silhouette's outermost pixel per row, from y0 down to y1"""
    m = silhouette(view); left = (view == "back") == (side == "L")       # sleeve on the viewer's left?
    out = []
    for y in np.arange(y0, y1, step).tolist() + [y1]:
        xs = np.nonzero(m[int(round(y))])[0]
        if len(xs): out.append((float(xs.min() if left else xs.max()), float(y)))
    return out

def S_of(view): v = VIEW[view]; return math.sqrt(v["SX"] * v["SY"])

@functools.lru_cache(maxsize=None)
def draft(size): return PT.draft(size)

def body_tf(view, size="M"):
    """(f, finv): render px -> garment mm on this size's body piece (and back). Grade scales about the neck point."""
    v = VIEW[view]; g = GRADE[size][1]
    def f(px, py): return ((np.asarray(px) - v["cx"]) * v["SX"] * g, (np.asarray(py) - v["ny"]) * v["SY"] * g)
    def finv(x, y): return (np.asarray(x) / (v["SX"] * g) + v["cx"], np.asarray(y) / (v["SY"] * g) + v["ny"])
    return f, finv

def armhole_mm(view, side, size="M"):
    """this size's armhole sew line on the body piece, shoulder point -> underarm (garment mm)"""
    g, mt = draft(size)
    if view == "back":
        e = next(x for x in g["B01"].edges if x.name == ("armhole R" if side == "R" else "armhole L"))
        pts = e.pts if side == "L" else e.pts[::-1]          # armhole L runs sp -> ua; armhole R runs ua -> sp
    else:
        pc = g["F02" if side == "R" else "F01"]
        pts = next(x for x in pc.edges if x.name == "armhole").pts      # sp -> ua
    if math.hypot(*np.subtract(pts[0], pts[-1])) and pts[0][1] > pts[-1][1]: pts = pts[::-1]
    return [tuple(p) for p in pts]

def cap_half(size, piece, sgn):
    """sleeve pattern half: cap from the top (0,-h) down to the underarm (sgn*W, 0), underarm seam to the cuff, cuff."""
    g, mt = draft(size); pc = g[piece]
    cap = next(e for e in pc.edges if e.name == "cap").pts
    top = min(range(len(cap)), key=lambda i: cap[i][1])
    half = cap[top::-1] if (cap[0][0] * sgn > 0) else cap[top:]          # from the top toward the sgn side
    half = [tuple(p) for p in half]
    if half[0][1] > half[-1][1]: half = half[::-1]
    W, Ww, Lu = mt["W"], mt["Ww"], mt["Lu"]
    return half, (sgn * Ww, Lu), (0.0, Lu)

def _arc(pts, n):
    pts = np.asarray(pts, float); d = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    s = np.linspace(0, d[-1], n); return np.c_[np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])]

def _ext(curve, u):
    """curve sampled at u in [0,1] (n points), extended linearly outside"""
    n = len(curve); t = np.linspace(0, 1, n)
    u = np.asarray(u, float); out = np.empty((len(u), 2))
    for k in range(2): out[:, k] = np.interp(u, t, curve[:, k])
    lo, hi = u < 0, u > 1
    if lo.any(): out[lo] = curve[0] + (curve[1] - curve[0]) * (u[lo, None] * (n - 1))
    if hi.any(): out[hi] = curve[-1] + (curve[-1] - curve[-2]) * ((u[hi, None] - 1) * (n - 1))
    return out

def coons(T, B, L, R, u, v):
    """T(u) top, B(u) bottom, L(v) at u=0, R(v) at u=1 (each sampled on [0,1]); returns P(u, v) for arrays u, v"""
    Tu, Bu, Lv, Rv = _ext(T, u), _ext(B, u), _ext(L, v), _ext(R, v)
    P00, P10, P01, P11 = T[0], T[-1], B[0], B[-1]
    u_, v_ = np.asarray(u)[:, None], np.asarray(v)[:, None]
    return (1 - v_) * Tu + v_ * Bu + (1 - u_) * Lv + u_ * Rv - ((1 - u_) * (1 - v_) * P00 + u_ * (1 - v_) * P10 + (1 - u_) * v_ * P01 + u_ * v_ * P11)

class SleeveMap:
    """render px of one visible sleeve half -> the sleeve pattern (piece coords), by an affine map that lays the render's
    outer fold (shoulder point -> outer cuff corner) on the sleeve centre line (cap top -> cuff) and keeps the art's
    width at the body's x scale (widened up to 1.45 so the render's inner sleeve edge meets the underarm keep-out). The render's drop-shoulder sleeves are long and only ~1/2 as wide as the pattern
    sleeve, so a seam-true map (armhole -> cap) would fold the patch; the art is placed by its position on the hanging
    sleeve instead (from the fold, down from the shoulder) and the armhole is a normal 15 mm keep-out. [PROPOSED]"""
    def __init__(self, view, side, size="M"):
        self.view, self.side, self.size = view, side, size
        self.piece, sgn = HALF[(view, side)]; self.sgn = sgn
        f, finv = body_tf(view, size); g_ = GRADE[size][1]
        arm = np.array(armhole_mm(view, side, size)); ax, ay = finv(arm[:, 0], arm[:, 1]); arm_px = np.c_[ax, ay]
        co, ci = CUFF_PX[(view, side)]
        oc = outer_contour(view, side, arm_px[0][1] + 25, co[1] - 8)
        g, mt = draft(size)
        sp = np.array(arm_px[0], float); d = np.array(co, float) - sp; Lpx = np.linalg.norm(d); d /= Lpx
        nrm = np.array([-d[1], d[0]])
        if np.dot(np.array(arm_px[-1]) - sp, nrm) < 0: nrm = -nrm          # lateral axis points to the inner (underarm) side
        self.sa = (mt["cap_h"] + mt["Lu"]) / Lpx                             # along: shoulder point -> cuff seam = sleeve length
        self.sc = VIEW[view]["SX"] * g_                                      # across: the body's x scale
        self.o, self.d, self.n, self.top = sp, d, nrm, (0.0, -mt["cap_h"])
        self.arm_px = arm_px
        Li = [tuple(arm_px[0])] + oc + [tuple(co)]
        # lateral is measured from the render's outer contour (the fold) at the same distance down the sleeve, so the
        # contour lands exactly on the sleeve centre line and the two halves never overlap across the fold
        L_ = np.array(Li) - sp; ca, cc = L_ @ d, L_ @ nrm; o_ = np.argsort(ca); self.ca, self.cc = ca[o_], cc[o_]
        # inner edge of the visible sleeve (armhole line, then underarm -> cuff) as lateral width per distance down:
        # the art is widened (x 1.0 .. 1.45) so that this edge lands on the underarm keep-out line, i.e. art cut by
        # the render's inner edge ends at a seam, not in the middle of the sleeve
        inner = np.r_[arm_px, np.linspace(arm_px[-1], ci, 20)] - sp
        ia = inner @ d; ic = inner @ nrm - np.interp(ia, self.ca, self.cc); o_ = np.argsort(ia)
        self.ia, self.ic = ia[o_], np.maximum(ic[o_], 1.0)
        self.W, self.Ww, self.Lu = mt["W"], mt["Ww"], mt["Lu"]
        self.quad_px = Polygon([tuple(p) for p in arm_px] + [tuple(ci)] + Li[::-1]).buffer(0)
    def __call__(self, px, py):
        q = np.c_[np.atleast_1d(px).astype(float), np.atleast_1d(py).astype(float)] - self.o
        a = q @ self.d; c = q @ self.n - np.interp(q @ self.d, self.ca, self.cc)
        y = self.top[1] + a * self.sa
        return self.sgn * c * self.sc * self.k(a, y), y
    def k(self, a, y):
        Wy = np.where(y > 0, self.W + (self.Ww - self.W) * np.clip(y / self.Lu, 0, 1), self.W)
        kk = (Wy - 15.0) / (np.interp(a, self.ia, self.ic) * self.sc)
        return np.where(y > 0, np.clip(kk, 1.0, 1.45), 1.0)
    def inv(self, P):
        P = np.atleast_2d(P); a = (P[:, 1] - self.top[1]) / self.sa; c = self.sgn * P[:, 0] / (self.sc * self.k(a, P[:, 1])) + np.interp(a, self.ca, self.cc)
        return self.o + np.outer(a, self.d) + np.outer(c, self.n)
    def jac(self, px, py, h=2.0):
        x0 = np.array(self(px, py)).ravel(); xa = np.array(self(px + h, py)).ravel(); xb = np.array(self(px, py + h)).ravel()
        return np.c_[(xa - x0) / h, (xb - x0) / h], x0

@functools.lru_cache(maxsize=None)
def sleeve_map(view, side, size="M"): return SleeveMap(view, side, size)

def map_geom(geom, f, densify=1.0):
    """apply a point map to a shapely geometry (densified first so curved maps stay smooth)"""
    if densify: geom = geom.segmentize(densify)
    def tf(x, y, z=None):
        X, Y = f(np.asarray(x), np.asarray(y)); return np.asarray(X), np.asarray(Y)
    return transform(tf, geom)

@functools.lru_cache(maxsize=None)
def image(view): return Image.open(VIEW[view]["img"]).convert("RGB")

def warp_body(view, size, bbox, ppm):
    """render resampled into this size's body garment mm (for compare sheets)"""
    from scipy.ndimage import map_coordinates
    f, finv = body_tf(view, size); x0, y0, x1, y1 = bbox; W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    XX, YY = np.meshgrid(x0 + (np.arange(W) + 0.5) / ppm, y0 + (np.arange(H) + 0.5) / ppm)
    px, py = finv(XX, YY); a = np.asarray(image(view)).astype(np.float32); out = np.zeros((H, W, 3), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=1, mode="nearest")
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))

def warp_sleeve(view, side, size, bbox, ppm):
    """render resampled into sleeve pattern mm (one visible half; other pixels white)"""
    from scipy.ndimage import map_coordinates
    sm = sleeve_map(view, side, size); x0, y0, x1, y1 = bbox; W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    XX, YY = np.meshgrid(x0 + (np.arange(W) + 0.5) / ppm, y0 + (np.arange(H) + 0.5) / ppm)
    q = sm.inv(np.c_[XX.ravel(), YY.ravel()]); px, py = q[:, 0].reshape(XX.shape), q[:, 1].reshape(XX.shape)
    bad = ~np.isfinite(px); px = np.where(bad, 0, px); py = np.where(bad, 0, py)
    a = np.asarray(image(view)).astype(np.float32); out = np.zeros((H, W, 3), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=1, mode="nearest")
    out[bad] = 255
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))
