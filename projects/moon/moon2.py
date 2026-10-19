"""Rev C moon (LESSONS A13): the close-up's STITCH STRUCTURE as objects, not tone patches.
  ground  — warm tone (cream / highlight / pale gold, from the smoothed close-up colour) in 7 mm tiles, each tile sewn at
            the local stitch direction measured from the close-up (structure tensor) -> the swirling thread rows;
            ground items are 'under': cells and craters sit ON TOP of them (no knockout, raised cells, no navy gaps).
  cells   — every raised oval cell of the close-up (bright blobs between the dark stitch gaps): its own satin object along
            its long axis, tone from its own pixels, + a light rim run on its upper-left edge.
  craters — the 3 grey-green star silhouettes traced from the close-up, filled radially in crater dark, pale centre ring.
Close-up px -> back mm: centre (724.5, 295.5) -> (0, 244), r 275 px -> 120 mm."""
import math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure, morphology
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from motifs2 import R
import trace as TR

CX, CY, RPX = 724.5, 295.5, 275.0
RMM = 120.0; K = RMM / RPX
def to_mm(x, y): return ((np.asarray(x) - CX) * K, 244 + (np.asarray(y) - CY) * K)
TONES = {"m1": (243, 224, 196), "m2": (240, 210, 162), "m3": (226, 190, 140)}       # warm ground tones (close-up, smoothed)
CELL_TONES = {"m1": (247, 232, 205), "m2": (242, 212, 165), "m3": (228, 192, 140), "m4": (205, 170, 120)}
STARS = [(650, 118), (650, 224), (848, 235)]

def lab(c):
    return TR.lab_img(np.array(c, float)[None, None, :])[0, 0]

def nearest(rgb, tones):
    L = lab(rgb); return min(tones, key=lambda k: float(((lab(tones[k]) - L) ** 2).sum()))

def build(img, fig_exclude=True):
    a = np.asarray(img.convert("RGB")).astype(float); H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]; d = np.hypot(xx - CX, yy - CY)
    inside = d < RPX - 2
    lum = a.mean(2)
    figz = (np.abs(xx - 725) < 90) & (yy > 300)               # licensed figure + pole top: not traced (box covers it)
    disc = Point(0, 244).buffer(RMM, 360)
    vis = []
    # ---------------- direction field (structure tensor of the stitch rows)
    g = ndi.gaussian_filter(lum, 1.2); gx = ndi.sobel(g, 1); gy = ndi.sobel(g, 0)
    Jxx = ndi.gaussian_filter(gx * gx, 7); Jyy = ndi.gaussian_filter(gy * gy, 7); Jxy = ndi.gaussian_filter(gx * gy, 7)
    theta = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy) + np.pi / 2      # along the rows (perpendicular to the gradient)
    # ---------------- ground: smooth tone regions (colour smoothed over the cells), cut into 7 mm tiles sewn at the
    # local stitch direction of the close-up
    sm = np.stack([ndi.gaussian_filter(a[..., i], 8) for i in range(3)], -1)
    keys = list(TONES); P = np.stack([lab(TONES[k]) for k in keys]); Lsm = TR.lab_img(sm)
    best = np.argmin(((Lsm[:, :, None, :] - P[None, None]) ** 2).sum(-1), -1)
    best = np.where(figz, keys.index("m2"), best)
    best = ndi.median_filter(best, size=15)
    G = {k: TA_map(TR.polys_of((best == i) & inside, 1, (0, 0, W, H), 80)).buffer(0.8).buffer(-0.8).buffer(0.45).intersection(disc) for i, k in enumerate(keys)}   # +0.45: tone regions overlap
    tile = 7.0
    for ty in np.arange(244 - RMM, 244 + RMM, tile):
        for tx in np.arange(-RMM, RMM, tile):
            t = box(tx - 0.7, ty - 0.7, tx + tile + 0.7, ty + tile + 0.7)     # tiles overlap 0.7 mm: rows end inside the neighbour, no navy between tiles
            if not t.intersects(disc): continue
            c = t.centroid; px = int(round(CX + c.x / K)); py = int(round(CY + (c.y - 244) / K))
            px = min(max(px, 0), W - 1); py = min(max(py, 0), H - 1)
            ang = (math.degrees(math.atan2(c.y - 244, c.x)) + 90) if figz[py, px] else math.degrees(theta[py, px])
            for k in keys:
                q = G[k].intersection(t)
                for p in ([q] if q.geom_type == "Polygon" else [g_ for g_ in getattr(q, "geoms", []) if g_.geom_type == "Polygon"]):
                    if p.area < 0.3: continue
                    r = R(k, p, "tatami", ang, {"m1": "MN-hl", "m2": "MN", "m3": "MN-warm"}[k]); r["under"] = True; vis.append(r)
    rim = disc.difference(disc.buffer(-2.2))
    vis.append(R("m3", rim, "satin", "auto", "MN-warm"))
    # ---------------- cells: bright isotropic blobs (Hessian, 2 scales) = the raised oval cells of the close-up
    from skimage.feature import peak_local_max, hessian_matrix, hessian_matrix_eigvals
    blue = (a[..., 2] > a[..., 0]) | (lum < 90)
    allowed = inside & ~figz & ~ndi.binary_dilation(blue, iterations=4) & (np.hypot(xx - CX, yy - CY) < RPX - 7)
    cells = []
    for sg in (5.0, 3.5):
        Hm = hessian_matrix(lum, sigma=sg, order="rc", use_gaussian_derivatives=True); e = hessian_matrix_eigvals(Hm)
        st_ = np.where(e[0] < 0, -e[0] * sg * sg, 0)
        for y, x in peak_local_max(st_, min_distance=int(sg * 1.6), threshold_abs=4, labels=allowed.astype(int)):
            if any(math.hypot(x - cx_, y - cy_) < (sg + s_) * 1.2 for cx_, cy_, s_, _, _ in cells): continue
            hrr, hrc, hcc = Hm[0][y, x], Hm[1][y, x], Hm[2][y, x]
            w_, v_ = np.linalg.eigh(np.array([[hrr, hrc], [hrc, hcc]]))       # w_[1] = less negative = long axis
            vr, vc = v_[:, 1]; rot = math.degrees(math.atan2(vr, vc))
            el = min(1.8, math.sqrt(max(w_[0], -1e9) / min(w_[1], -1e-9))) if w_[1] < 0 else 1.6
            cells.append((x, y, sg, rot, el))
    n_cell = 0
    for x, y, sg, rot, el in cells:
        X0, Y0 = (float(v) for v in to_mm(x, y))
        b_ = max(1.0, sg * 1.25 * K); a_ = b_ * el
        ell = affinity.rotate(affinity.scale(Point(X0, Y0).buffer(1, 24), a_, b_), rot, origin=(X0, Y0)).intersection(disc.buffer(-1))
        if ell.is_empty or ell.area < 1.2: continue
        col = sm_cell(a, x, y, sg); tone = nearest(col, CELL_TONES)
        vis.append(R(tone, ell, "satin", rot + 90, "MN-crater" if tone == "m4" else {"m1": "MN-hl", "m2": "MN", "m3": "MN-warm"}[tone]))
        rimc = ell.exterior.intersection(box(X0 - 30, Y0 - 30, X0 + 0.3 * a_, Y0 + 0.3 * b_))
        if not rimc.is_empty and rimc.length > 1.5:
            vis.append(R("m1" if tone != "m1" else "m3", rimc.buffer(0.3, cap_style="round"), "run", None, "MN-ray"))
        n_cell += 1
    # ---------------- star craters + grey-green maria: traced silhouettes
    smc = np.stack([ndi.gaussian_filter(a[..., i], 1.5) for i in range(3)], -1)
    grey = ((smc[..., 0] - smc[..., 2]) < 62) & (smc.mean(2) < 205) & inside & ~blue & ~figz
    grey = morphology.remove_small_objects(morphology.binary_opening(grey, morphology.disk(2)), 150)
    labg = measure.label(grey)
    star_ids = set()
    for sx, sy in STARS:
        win = labg[sy - 6:sy + 7, sx - 6:sx + 7]; ids = win[win > 0]
        if len(ids): star_ids.add(int(np.bincount(ids).argmax()))
    for rp in measure.regionprops(labg):
        sil = TA_map(TR.polys_of(labg == rp.label, 1, (0, 0, W, H), 20)).buffer(0.35).buffer(-0.35).intersection(disc)
        if sil.is_empty or sil.area < 2: continue
        if rp.label in star_ids:
            yc, xc = min(STARS, key=lambda p: math.hypot(p[0] - rp.centroid[1], p[1] - rp.centroid[0]))[::-1]
            X0, Y0 = (float(v) for v in to_mm(xc, yc))
            vis.append(R("m5", sil, "satin", ("radial", X0, Y0), "MN-mare"))
            vis.append(R("m1", Point(X0, Y0).buffer(2.6, 32).difference(Point(X0, Y0).buffer(1.5, 32)), "satin", ("radial", X0, Y0), "MN-hl"))
            vis.append(R("m3", Point(X0, Y0).buffer(1.5, 24), "satin", "auto", "MN-warm"))
        else:
            for p in ([sil] if sil.geom_type == "Polygon" else [g_ for g_ in getattr(sil, "geoms", []) if g_.geom_type == "Polygon"]):
                if p.area > 2: vis.append(R("m4", p, "tatami", "auto", "MN-crater"))
    # painter order: ground, rim, maria, stars, then the raised cells on top of everything
    rank = lambda r: 0 if r.get("under") else (1 if r["grp"] in ("MN-crater",) and r["st"] == "tatami" else (2 if r["grp"] == "MN-mare" or isinstance(r["ang"], tuple) else 3))
    stars = unary_union([r["geom"] for r in vis if r["grp"] == "MN-mare" and isinstance(r["ang"], tuple)])
    if not stars.is_empty:     # cells never sit on the star craters (close-up: stars are clean grey-green)
        vis = [r for r in vis if not (rank(r) == 3 and r["geom"].centroid.within(stars.buffer(0.5)))]
    vis.sort(key=rank)
    return vis, disc, n_cell

def sm_cell(a, x, y, sg):
    r = int(max(2, sg)); p = a[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1].reshape(-1, 3); return p.mean(0)

def TA_map(g):
    from shapely.ops import transform
    return transform(lambda x, y, z=None: to_mm(x, y), g)
