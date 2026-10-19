"""Motif silhouettes traced from the mockup (LESSONS A14): every bar, heart, star, dot and sparkle is fitted to its own
component in the mockup — not a hand-typed size. The mockup (inputs/flat.png, ~1 px/mm, no close-ups) is upsampled x4
(bicubic) around the motif and thresholded per colour family half-way between fabric and thread (the same classes the
gates use, gates.FAM), so the traced edge is the half-max edge. Each component gives: centroid (mockup px), area,
principal axis angle, length + mean width along it, bounding extents, and the angle of its farthest point (a star tip).
  comps(fam, box)            -> [component dicts] in mockup px
  snap(fam, px, py, r=6)     -> the component nearest (px, py) within r px (searching a box round it), or None"""
import math
import numpy as np
from scipy import ndimage as ndi
from PIL import Image

UP = 4
_IM = None
def _im():
    global _IM
    if _IM is None: _IM = Image.open("inputs/flat.png").convert("RGB")
    return _IM

FAM = {   # same colour classes as gates.FAM (mockup RGB), + 'mintx' = mint without the blue bars
    "mint":   lambda r, g, b: (g > 120) & (g - r > 45) & (b > 90) & (g >= b - 15),
    "blue":   lambda r, g, b: (b > 120) & (b - r > 70) & (b - g > 20),
    "red":    lambda r, g, b: (r > 140) & (r - g > 70) & (r - b > 60),
    "yellow": lambda r, g, b: (r > 140) & (g > 110) & (r - b > 45),         # pale lemon cores reach r-b ~70
    "white":  lambda r, g, b: (r > 140) & (g > 140) & (b > 140) & (np.abs(r - b) < 45),
}

def comps(fam, box, min_area=1.0):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    c = _im().crop((x0, y0, x1, y1)); c = c.resize((c.width * UP, c.height * UP), Image.BICUBIC)
    a = np.asarray(c).astype(float); m = FAM[fam](a[..., 0], a[..., 1], a[..., 2])
    lab, n = ndi.label(m); out = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        ys, xs = np.nonzero(lab[sl] == k)
        A = len(ys) / UP**2
        if A < min_area: continue
        # pixel-CENTRE convention (pixel i is centred at i), as scipy map_coordinates / the mockup resampling use
        X = (xs + sl[1].start + 0.5) / UP + x0 - 0.5; Y = (ys + sl[0].start + 0.5) / UP + y0 - 0.5
        cx, cy = X.mean(), Y.mean()
        C = np.cov(np.vstack([X - cx, Y - cy])) if len(X) > 2 else np.eye(2)
        ev, V = np.linalg.eigh(C); u = V[:, 1]; ang = math.degrees(math.atan2(u[1], u[0]))
        t = (X - cx) * u[0] + (Y - cy) * u[1]; L = t.max() - t.min() + 1 / UP
        d = np.hypot(X - cx, Y - cy); j = int(np.argmax(d))
        out.append(dict(cx=float(cx), cy=float(cy), area=float(A), ang=float(ang), L=float(L), W=float(A / max(L, 1e-6)),
                        ext_w=float(X.max() - X.min() + 1 / UP), ext_h=float(Y.max() - Y.min() + 1 / UP),
                        tip_ang=float(math.degrees(math.atan2(Y[j] - cy, X[j] - cx))), rmax=float(d.max())))
    return out

def snap(fam, px, py, r=6.0, box_r=22):
    cs = comps(fam, (px - box_r, py - box_r, px + box_r, py + box_r))
    best = None
    for c in cs:
        dd = math.hypot(c["cx"] - px, c["cy"] - py)
        if dd <= r and (best is None or dd < best[0]): best = (dd, c)
    return best[1] if best else None

def axis_near(ang, ref):
    """the principal-axis direction (ang or ang+180) closest to a reference angle"""
    a = ang
    while a - ref > 90: a -= 180
    while ref - a > 90: a += 180
    return a

def register_glyph(g, ref_fn, ppm=4.0, steps=((1.0, 2.0, 0.04), (0.5, 1.0, 0.02), (0.25, 0.5, 0.01)), rounds=3, aspect=False, starts=None, drop_frag=False, size_rule=True):
    """fit a font glyph (shapely, garment mm) to the mockup's silhouette of the same glyph: coordinate search on
    (dx, dy, rotation, scale) maximising IoU against ref_fn(bbox, ppm) -> bool mask (the mockup family mask on a garment
    grid). Returns (glyph, dict(dx, dy, rot, scale, iou_before, iou_after))."""
    from shapely import affinity
    from PIL import Image, ImageDraw
    b = g.bounds; pad = 4.0; bb = (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)
    ref = ref_fn(bb, ppm); c = g.centroid
    if not ref.any(): return g, dict(dx=0, dy=0, rot=0, scale=1, aspect=1, iou_before=0, iou_after=0, M=[1, 0, 0, 1, 0, 0], w_scale=1.0)
    def rast(q):
        W, H = ref.shape[1], ref.shape[0]; im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
        for p in getattr(q, "geoms", [q]):
            if p.geom_type != "Polygon": continue
            d.polygon([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in p.exterior.coords], fill=255)
            for r in p.interiors: d.polygon([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in r.coords], fill=0)
        return np.array(im) > 127
    mrr = list(g.minimum_rotated_rectangle.exterior.coords)
    e = max(((mrr[i], mrr[i + 1]) for i in range(2)), key=lambda q: math.dist(*q)); th0 = math.degrees(math.atan2(e[1][1] - e[0][1], e[1][0] - e[0][0]))
    def mat(p):
        """affine (shapely order a, b, d, e, xoff, yoff): stretch p[4] along the motif axis th0, scale p[3], rotate p[2] about c, shift"""
        t0 = math.radians(th0); A = np.eye(3)
        def R(t): return np.array([[math.cos(t), -math.sin(t), 0], [math.sin(t), math.cos(t), 0], [0, 0, 1]])
        T = lambda x, y: np.array([[1, 0, x], [0, 1, y], [0, 0, 1]]); Sx = np.diag([p[3] * p[4], p[3] / p[4], 1])
        A = T(c.x + p[0], c.y + p[1]) @ R(math.radians(p[2])) @ R(t0) @ Sx @ R(-t0) @ T(-c.x, -c.y)
        return [A[0, 0], A[0, 1], A[1, 0], A[1, 1], A[0, 2], A[1, 2]]
    def tf(p): return affinity.affine_transform(g, mat(p))
    # only the reference components this glyph overlaps (its neighbours stay out of the fit)
    lab, _ = ndi.label(ref); m0 = rast(g)
    ids = np.unique(lab[m0 & (lab > 0)])
    if not len(ids): ids = np.unique(lab[ndi.binary_dilation(m0, iterations=int(ppm)) & (lab > 0)])
    if drop_frag and len(ids) > 1:                    # stars / dots: drop reference fragments < 25 % of the main component
        ar = {int(i): int((lab == i).sum()) for i in ids}; top = max(ar.values()); ids = [i for i in ids if ar[int(i)] >= 0.25 * top]
    ref = np.isin(lab, ids) & (lab > 0)
    def ext(m, ax):
        idx = np.nonzero(m.any(axis=ax))[0]; return (idx[-1] - idx[0] + 1) if len(idx) else 0
    rw, rh = max(ext(ref, 0), 1), max(ext(ref, 1), 1)
    def iou(p):
        """IoU, minus a penalty when the width / height ratio leaves 0.8-1.25 (the gate's size rule, qa.motif_match)"""
        m = rast(tf(p)); v = (m & ref).sum() / max((m | ref).sum(), 1)
        for q in ((ext(m, 0) / rw, ext(m, 1) / rh) if size_rule else ()):
            q = max(q, 1e-6); bad = max(0.0, abs(math.log(q)) - math.log(1.2)); v -= 1.5 * bad
        return v
    i0 = iou([0.0, 0.0, 0.0, 1.0, 1.0]); best, p = None, None
    for st0 in (starts or [(0.0, 1.0)]):
      q0 = [0.0, 0.0, st0[0], st0[1], 1.0]; v0 = iou(q0)
      bq, bv = q0, v0
      for st_xy, st_r, st_s in steps:
        for _ in range(rounds):
            moved = False
            for k, st in ((0, st_xy), (1, st_xy), (2, st_r), (3, st_s)) + (((4, st_s),) if aspect else ()):
                for sgn in (-1, 1):
                    q = list(bq); q[k] += sgn * st
                    if k < 2 and abs(q[k]) > 4.0: continue
                    if k == 2 and abs(q[k] - st0[0]) > 14: continue
                    if k == 3 and not (0.75 <= q[k] <= 1.35): continue
                    if k == 4 and not (0.6 <= q[k] <= 1.6): continue
                    v = iou(q)
                    if v > bv + 1e-4: bv, bq, moved = v, q, True
            if not moved: break
      if best is None or bv > best: best, p = bv, bq
    return tf(p).buffer(0), dict(dx=round(p[0], 2), dy=round(p[1], 2), rot=round(p[2], 1), scale=round(p[3], 3), aspect=round(p[4], 3),
                                 iou_before=round(float(i0), 3), iou_after=round(float(best), 3), cx=float(c.x), cy=float(c.y), M=mat(p),
                                 w_scale=p[3] / p[4])          # a column across the motif axis (bar width) scales by this

def apply(regs, info):
    """apply a fit (general affine info['M']) to every region of a motif: geometry, column centreline (+ width: rims keep
    their width, other columns scale by w_scale), stipple run points, radial centre, fixed satin angle (+ rotation)"""
    from shapely import affinity
    M = info["M"]; f = lambda p: (M[0] * p[0] + M[1] * p[1] + M[4], M[2] * p[0] + M[3] * p[1] + M[5])
    rot = math.degrees(math.atan2(M[2], M[0]))
    out = []
    for r in regs:
        r2 = dict(r, geom=affinity.affine_transform(r["geom"], M).buffer(0))
        if r.get("col_cl"):
            r2["col_cl"] = [f(p) for p in r["col_cl"]]
            if not r.get("rim") and not r.get("col_closed"): r2["col_w"] = r["col_w"] * info.get("w_scale", 1.0)
        if r.get("run_pts"): r2["run_pts"] = [f(p) for p in r["run_pts"]]
        if isinstance(r.get("ang"), tuple): q = f((r["ang"][1], r["ang"][2])); r2["ang"] = (r["ang"][0], q[0], q[1])
        elif isinstance(r.get("ang"), (int, float)): r2["ang"] = r["ang"] + rot
        out.append(r2)
    return out

def trace_polygon(ref_fn, cx, cy, r=5.0, ppm=10.0):
    """the reference silhouette itself (A14 'trace every motif'): the mockup component under (cx, cy) as a polygon (mm)"""
    from skimage import measure
    from shapely.geometry import Polygon as _P
    bb = (cx - r, cy - r, cx + r, cy + r); m = ref_fn(bb, ppm)
    lab, n = ndi.label(m)
    if not n: return None
    k = lab[int(r * ppm) - 3:int(r * ppm) + 4, int(r * ppm) - 3:int(r * ppm) + 4].max()
    if not k:
        cs = ndi.center_of_mass(m, lab, range(1, n + 1)); k = 1 + int(np.argmin([math.hypot(c[1] - r * ppm, c[0] - r * ppm) for c in cs]))
    cs = measure.find_contours(np.pad(lab == k, 1).astype(float), 0.5)
    if not cs: return None
    c = max(cs, key=len)
    poly = _P([(bb[0] + (x - 1 + 0.5) / ppm, bb[1] + (y - 1 + 0.5) / ppm) for y, x in c]).buffer(0)
    return poly.buffer(0.12).buffer(-0.12).simplify(0.05).buffer(0) if poly.area > 0.5 else None
