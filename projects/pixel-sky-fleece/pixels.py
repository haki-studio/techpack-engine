"""Colour classes of the mockup (per pixel) and garment-detail masks (LESSONS A15: zip, pockets, bindings, collar are
masked out before tracing and filled from the surrounding design)."""
import numpy as np
from functools import lru_cache
from shapely.geometry import Point, Polygon, LineString
import mockmap as MM

CLASSES = ["sky", "cream", "black", "yellow", "gold"]
CENTRES = np.array([[128, 174, 247], [241, 234, 226], [40, 34, 31], [250, 236, 60], [226, 182, 40]], float)
SKY, CREAM, BLACK, YELLOW, GOLD, DETAIL, OUT = 0, 1, 2, 3, 4, 5, 6

@lru_cache(None)
def labels():
    """per-pixel class 0..4, DETAIL (garment hardware / bindings / collar), OUT (background)"""
    a = MM.img(); H, W, _ = a.shape
    d = ((a[:, :, None, :] - CENTRES[None, None]) ** 2).sum(-1)
    lab = d.argmin(-1).astype(np.int8)
    from scipy import ndimage as ndi
    br = a.min(2) > 232; L_, _ = ndi.label(br)                    # background = bright region connected to the border
    edge = np.unique(np.r_[L_[0], L_[-1], L_[:, 0], L_[:, -1]]); edge = edge[edge > 0]
    bg = np.isin(L_, edge); lab[bg] = OUT
    fringe = ndi.binary_dilation(bg, iterations=6) & ~bg          # silhouette fringe: lit pile tips read as cream
    det = detail_mask(); lab[det & ~bg] = DETAIL
    # black counts only inside the bird's box; elsewhere it is a seam / fold shadow (DETAIL)
    yy, xx = np.mgrid[0:H, 0:W]
    birdbox = (xx > 425) & (xx < 680) & (yy > 600) & (yy < 820)
    # pile shading (dark curls in the cream, deep blue curls in the sky) must not read as black: outside the bird's box
    # sky vs cream is decided by blueness alone (b - r), never by the dark centre
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    sc = np.where(b - r > 45, SKY, CREAM).astype(np.int8)
    fix = (lab == BLACK) & ~birdbox
    lab[fix] = sc[fix]
    keep = (lab == SKY) | (lab == CREAM)
    lab[keep] = sc[keep]
    lab[bg] = OUT; lab[det & ~bg] = DETAIL; lab[fringe] = DETAIL
    return lab

@lru_cache(None)
def detail_mask():
    a = MM.img(); H, W, _ = a.shape
    yy, xx = np.mgrid[0:H, 0:W]
    m = np.zeros((H, W), bool)
    m |= (np.abs(xx - MM.CFX) <= 24) & (yy >= 300)                                   # CF zip + its shadow
    m |= yy >= MM.HEMY - 16                                                           # hem binding
    m |= (yy <= 372) & (np.abs(xx - MM.CFX) < 240)                                   # collar + collar-seam piping
    for (x0, y0), (x1, y1) in POCKETS_PX:                                             # pocket zips + navy tape + pulls
        L = LineString([(x0, y0 - 6), (x1, y1 + 4)]).buffer(15)
        x_, y_, X_, Y_ = [int(v) for v in L.bounds]
        sub = np.array([[L.contains(Point(x, y)) for x in range(x_, X_ + 1)] for y in range(y_, Y_ + 1)])
        m[y_:Y_ + 1, x_:X_ + 1] |= sub
    for x0, y0, x1, y1 in PULLS_PX: m[y0:y1, x0:x1] = True                          # blue zip pulls (read as sky otherwise)
    # neck: collar-seam piping curve continues to the shoulders (y < 372 + small band near the collar)
    r = np.hypot((xx - MM.CFX) / 230.0, (yy - 230) / 150.0); m |= (r < 1.0)
    # sleeve cuff bindings
    m |= (yy >= 1325)
    return m

# pocket zips (top, bottom) in front.png px, read off the render (navy tape, blue pull at the top)
PULLS_PX = [(376, 940, 418, 1102), (1070, 944, 1114, 1102)]
POCKETS_PX = [((395, 948), (430, 1222)), ((1088, 952), (1050, 1222))]

def frac(px0, py0, px1, py1, lab=None):
    """class fractions (0..4) inside an image-pixel rectangle, ignoring DETAIL / OUT; returns (fractions, valid share)"""
    lab = labels() if lab is None else lab
    x0, y0, x1, y1 = int(round(px0)), int(round(py0)), int(round(px1)), int(round(py1))
    sub = lab[max(y0, 0):max(y1, y0 + 1), max(x0, 0):max(x1, x0 + 1)]
    if sub.size == 0: return np.zeros(5), 0.0
    v = sub[sub < 5]
    if v.size == 0: return np.zeros(5), 0.0
    return np.bincount(v, minlength=5)[:5] / v.size, v.size / sub.size
