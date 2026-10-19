"""Rev C (final) clouds — traced from the close-ups as STITCH STRUCTURE (LESSONS A12 + A13; review item 4), replacing the
Rev C WIP contour-offset scallops (moonmotifs.cloud_contour), whose silhouettes came out jagged and flat.

For each close-up cloud (connected lavender component of the close-up):
  silhouette — the close-up mask, closed/opened by 1 px and smoothed by 1.2 px: domed lobes + the WHOLE tapering tails.
  tones      — close-up pixels (smoothed 1.4 px) -> nearest of the 5 cloud threads: pale white-pink caps on every lobe
               top -> lavender -> periwinkle -> violet -> deep indigo underside; tones overlap 0.3 mm (no fabric between).
  rows       — the close-up's own stitch direction (structure tensor) as evenly spaced streamlines 0.45 mm apart, sewn
               as tatami rows ALONG them: the stitches curve with each scallop row exactly as on the close-up, no grid.
  scallops   — the dark indigo scallop / lobe-overlap lines of the close-up (black top-hat skeleton) as bean lines on top.
  tails      — parts of the silhouette narrower than 3.2 mm: turning satin along the tail (taper kept, blunt tip >= 1 mm).
Returns region dicts in mm via f (close-up px -> mm), s = mm per close-up px."""
import math
import numpy as np
from scipy import ndimage as ndi
from skimage import morphology, measure
from shapely.geometry import Point, Polygon, LineString, MultiLineString, box
from shapely.ops import unary_union, transform
from motifs2 import R
import trace as TR
import moon3

TONES = {"c1": (232, 215, 225), "c2": (185, 172, 198), "c3": (145, 138, 176), "c4": (105, 107, 153), "c5": (73, 77, 124)}   # k-means of the back close-up clouds
CODE = {"c1": "CL-hl", "c2": "CL-top", "c3": "CL", "c4": "CL-mid", "c5": "CL-shade"}

def polys(g): return moon3.polys(g)

def masks(img, box_px):
    """lavender components of a close-up window (px). Returns (label image, n, crop array)"""
    x0, y0, x1, y1 = box_px
    a = np.asarray(img.crop(box_px).convert("RGB")).astype(float)
    lum = a.mean(2)
    m = (a[..., 2] - a[..., 0] > -16) & (lum > 62) & (a[..., 2] > 95) & (lum < 238)      # < 238: never the white studio background (sleeve close-up)          # lavender + the pale pink-white caps (moon is r >> b, pole grey r > b)
    m = ndi.binary_closing(m, iterations=2); m = ndi.binary_fill_holes(m); m = morphology.binary_opening(m, morphology.disk(1))
    m = morphology.remove_small_objects(m, 300)
    lab, n = ndi.label(m)
    return lab, n, a

class PxField:
    def __init__(self, a, sig=4.0):
        lum = a.mean(2); g = ndi.gaussian_filter(lum, 1.0); gx = ndi.sobel(g, 1); gy = ndi.sobel(g, 0)
        Jxx = ndi.gaussian_filter(gx * gx, sig); Jyy = ndi.gaussian_filter(gy * gy, sig); Jxy = ndi.gaussian_filter(gx * gy, sig)
        th = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy) + np.pi / 2
        self.c = np.cos(2 * th); self.s = np.sin(2 * th); self.H, self.W = th.shape
    def __call__(self, x, y):
        x = min(max(x, 0), self.W - 1.001); y = min(max(y, 0), self.H - 1.001)
        i, j = int(y), int(x); fy, fx = y - i, x - j
        def bl(A): return (A[i, j] * (1 - fx) * (1 - fy) + A[i, j + 1] * fx * (1 - fy) + A[i + 1, j] * (1 - fx) * fy + A[i + 1, j + 1] * fx * fy)
        t = 0.5 * math.atan2(bl(self.s), bl(self.c)); return math.cos(t), math.sin(t)

def cloud(a, comp, off, f, s, layer_tag=None, tail_w=4.6):
    """a: crop RGB array, comp: bool mask of ONE cloud in the crop, off: crop origin in close-up px,
    f: close-up px -> mm (vectorised), s: mm per px (abs). Returns (regions, silhouette mm)."""
    ox, oy = off
    ys, xs = np.nonzero(comp); pad = 6
    r0, r1, c0, c1 = max(0, ys.min() - pad), min(comp.shape[0], ys.max() + pad + 1), max(0, xs.min() - pad), min(comp.shape[1], xs.max() + pad + 1)
    A = a[r0:r1, c0:c1]; Mk = comp[r0:r1, c0:c1]
    bx = (ox + c0, oy + r0, ox + c1, oy + r1)
    M = lambda g: transform(lambda x, y, z=None: f(np.asarray(x), np.asarray(y)), g)
    sil_px = TR.polys_of(Mk, 1, bx, 30, simplify=0.3).buffer(1.2).buffer(-1.2)
    sil = M(sil_px).buffer(0)
    if sil.is_empty: return [], sil
    regs = []
    # tails: narrower than tail_w mm
    core = sil.buffer(-tail_w / 2).buffer(tail_w / 2 + 0.05).intersection(sil)
    tails = [p for p in polys(sil.difference(core)) if p.area > 1.5]
    # tones
    UP = 3                                                     # tone map on a x3 (cubic) upsample: smooth scale edges, no pixel steps
    Au = ndi.zoom(A, (UP, UP, 1), order=3); Mu = ndi.zoom(Mk.astype(float), UP, order=1) > 0.5
    ok = (Au.mean(2) >= 78).astype(float)                    # the black stitch gaps are shadow, not thread: tone from the threads
    sm = np.stack([ndi.gaussian_filter(Au[..., i] * ok, 1.3 * UP) for i in range(3)], -1) / (ndi.gaussian_filter(ok, 1.3 * UP)[..., None] + 1e-6)
    keys = list(TONES); P = np.stack([moon3.lab(TONES[k]) for k in keys])
    best = np.argmin(((TR.lab_img(sm)[:, :, None, :] - P[None, None]) ** 2).sum(-1), -1)
    best = ndi.median_filter(best, size=2 * UP + 1)
    _, (iy, ix) = ndi.distance_transform_edt(~Mu, return_indices=True); best = best[iy, ix]     # edge pixels from inside
    # flow rows (close-up stitch direction) in px, 0.45 mm apart
    F = PxField(A, sig=3.0)
    H_, W_ = Mk.shape; Mi = ndi.binary_dilation(Mk, iterations=1)
    inside = lambda x, y: 0 <= x < W_ and 0 <= y < H_ and Mi[int(y), int(x)]
    rows = moon3.streamlines(F, inside, (0, 0, W_, H_), dsep=0.45 / s, dtest=0.55, h=0.30 / s, min_len=1.0 / s)
    rows = [[(x + bx[0], y + bx[1]) for x, y in r] for r in rows if len(r) > 1]
    ML = M(MultiLineString(rows)) if rows else MultiLineString()
    body = sil.difference(unary_union(tails).buffer(0.05)) if tails else sil
    # ---- scallop rows: fish scales laid along streamlines of the close-up stitch direction, ROW mm apart, staggered;
    # each scale = satin arch in the close-up tone under its top, dark gap run on its arch, light rim run just inside.
    # Sewn top row first, so every lower scale overlaps the one above (the close-up's overlapping scale rows).
    ROW, SW, SH = 2.6, 9.5, 3.0
    rows2 = moon3.streamlines(F, inside, (0, 0, W_, H_), dsep=ROW / s, dtest=0.7, h=0.5 / s, min_len=SW / s)
    sc_ = []
    rng = np.random.RandomState(len(rows2))
    for rw in rows2:
        if len(rw) < 3: continue
        ln = LineString([(x + bx[0], y + bx[1]) for x, y in rw]); L = ln.length; step = SW / s * 0.92
        t0 = rng.uniform(0, step)
        while t0 < L:
            c = ln.interpolate(t0); a_ = ln.interpolate(max(0, t0 - 1)); b_ = ln.interpolate(min(L, t0 + 1))
            tx, ty = b_.x - a_.x, b_.y - a_.y; tl = math.hypot(tx, ty) or 1; tx, ty = tx / tl, ty / tl
            nx, ny = -ty, tx
            if ny > 0: nx, ny = -nx, -ny                       # normal points up (scales bulge up, close-up)
            w2, hh, dn = SW / s / 2, SH / s, 1.0 / s
            arch = [(c.x + tx * w2 * math.cos(q) + nx * hh * math.sin(q), c.y + ty * w2 * math.cos(q) + ny * hh * math.sin(q)) for q in np.linspace(0, math.pi, 13)]
            base = [(c.x - tx * w2 - nx * dn, c.y - ty * w2 - ny * dn), (c.x + tx * w2 - nx * dn, c.y + ty * w2 - ny * dn)]
            poly = Polygon(arch + base[::-1][::-1][::-1] if False else arch + [base[0], base[1]][::-1][::-1]).buffer(0)
            poly = Polygon([arch[0]] + arch[1:] + [base[0], base[1]]).buffer(0) if poly.is_empty else poly
            # tone under the upper half of the scale
            qx, qy = c.x + nx * hh * 0.45 - bx[0], c.y + ny * hh * 0.45 - bx[1]
            iy_, ix_ = int(min(max(qy * UP, 0), best.shape[0] - 1)), int(min(max(qx * UP, 0), best.shape[1] - 1))
            sc_.append((c.y, poly, LineString(arch), int(best[iy_, ix_])))
            t0 += step
    sc_.sort(key=lambda t: t[0])                                 # top rows first
    cover = []
    for y_, poly, arc, ti in sc_:
        P_ = M(poly).buffer(0).intersection(body)
        if P_.is_empty or P_.area < 2.0: continue
        k = keys[ti]
        regs.append(R(k, P_, "satin", "auto", CODE[k]))
        A_ = M(arc).intersection(body.buffer(-0.5))
        if not A_.is_empty and A_.length > 2:
            regs.append(R(keys[min(4, ti + 2)], A_.buffer(0.3, cap_style="round"), "run", None, "CL-line"))
            inner_arc = M(arc).parallel_offset(0.0, "left") if False else None
            rim = transform(lambda x, y, z=None: (np.asarray(x), np.asarray(y) + 0.6), A_).intersection(P_.buffer(-0.3))
            if not rim.is_empty and rim.length > 2: regs.append(R(keys[max(0, ti - 1)], rim.buffer(0.3, cap_style="round"), "run", None, "CL-line"))
        cover.append(P_)
    scal = unary_union(cover) if cover else Polygon()
    # ---- ground under the scales (smooth tone gradient, flow rows) only where no scale covers
    smb = np.stack([ndi.gaussian_filter(Au[..., i] * ok, 4.0 * UP) for i in range(3)], -1) / (ndi.gaussian_filter(ok, 4.0 * UP)[..., None] + 1e-6)
    bestb = np.argmin(((TR.lab_img(smb)[:, :, None, :] - P[None, None]) ** 2).sum(-1), -1); bestb = bestb[iy, ix]
    gap = body.difference(scal.buffer(-0.35)) if not scal.is_empty else body
    ground = []
    for i, k in enumerate(keys):
        g = M(TR.polys_of((bestb == i) & Mu, UP, bx, 4, simplify=0.2)).buffer(0.3).intersection(gap)
        for p in polys(g):
            if p.area < 0.4: continue
            w = 2 * p.area / max(p.length, 1e-6)
            if w < 1.2: ground.append(R(k, p, "satin", "auto", CODE[k])); continue
            r = R(k, p, "tatami", 0, CODE[k]); r["rows"] = ML.intersection(p.buffer(0.15)); ground.append(r)
    regs = ground + regs
    # tails: turning satin in the tail's own tone
    for t in tails:
        cx, cy = inv_sample(t, f, bx, Mk)
        tone = keys[int(best[min(cy * UP, best.shape[0] - 1), min(cx * UP, best.shape[1] - 1)])] if cx is not None else "c2"
        regs.append(R(tone if tone != "c5" else "c4", t.buffer(0.15).intersection(sil.buffer(0.1)), "satin", "auto", "CL-wisp"))
    return regs, sil

def inv_sample(t, f, bx, Mk):
    """close-up px (in crop) of a point inside region t (mm): search the crop for the pixel that maps nearest"""
    c = t.representative_point()
    ys, xs = np.nonzero(Mk)
    X, Y = f(xs + bx[0], ys + bx[1]); d = (np.asarray(X) - c.x) ** 2 + (np.asarray(Y) - c.y) ** 2
    if not len(d): return None, None
    i = int(np.argmin(d)); return int(xs[i]), int(ys[i])

def dark_lines_arr(A, Mk, bx, size=9, thr=34, min_len_px=22):
    from skimage.morphology import skeletonize
    g = ndi.gaussian_filter(A.mean(2), 0.7)
    th = ndi.grey_closing(g, size=(size, size)) - g
    m = (th > thr) & ndi.binary_erosion(Mk, iterations=2)
    m = morphology.remove_small_objects(m, 8)
    return TR.lines_of(m, 1, bx, min_len_px)

def clouds_in(img, box_px, f, s, min_area_px=900):
    lab, n, a = masks(img, box_px)
    out = []
    for i in range(1, n + 1):
        comp = lab == i
        if comp.sum() < min_area_px: continue
        xs_ = np.nonzero(comp.any(0))[0]
        if xs_.max() - xs_.min() < 90: continue          # narrow light bits (pole highlights) are not clouds
        regs, sil = cloud(a, comp, box_px[:2], f, s)
        if regs:
            ys, xs = np.nonzero(comp)
            out.append(dict(vis=regs, sil=sil, px=(float(xs.mean() + box_px[0]), float(ys.mean() + box_px[1])), area_px=int(comp.sum())))
    return out
