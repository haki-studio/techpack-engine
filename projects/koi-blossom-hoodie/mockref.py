"""Mockup reference for the flora (LESSONS A14/A15), shared by scene.py (tracing) and fidelity.py (gates).
flora_mask(P): the mockup's embroidered flora pixels on piece P's size-M grid (piece mm), with garment details masked out
FIRST (A15): everything outside the art keep-outs (zip + its shadow, side / shoulder / armhole seams, hem band, cuff),
the white background, the inner 28 % of each sleeve's front half (the body shows there in the front view), the welt boxes (+4 mm), thin line features (topstitching, seam shadows: opening 2 mm) and the mockup koi (replaced by
tetras — excluded so they are not traced as flora). Embroidery = colour far from the fabric AND blue (or light).
tones(P): the same grid quantised into 4 thread tones by the mockup's own luminance quartiles inside the flora."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union
from skimage import measure
import qa, mockmap as MM, front as F

PPM = 5.0
BB = {"FR": (-300, -60, 0, 520), "FL": (0, -60, 300, 520), "SR": (-10, -110, 260, 470), "SL": (-260, -110, 10, 470)}
TONE_KEYS = ["kb_cobalt", "kb_royal", "kb_sky", "kb_ice"]

def raster(geoms, bb, ppm=PPM):
    from PIL import Image, ImageDraw
    H, W = int((bb[3] - bb[1]) * ppm), int((bb[2] - bb[0]) * ppm); im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    T = lambda cs: [((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in cs]
    for g in geoms:
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.geom_type != "Polygon" or p.is_empty: continue
            d.polygon(T(p.exterior.coords), fill=255)
            for h in p.interiors: d.polygon(T(h.coords), fill=0)
    return np.array(im) > 127

def koi_footprints(koi_mm):
    """koi_mm: [(head mm, tail mm)] of the mockup koi on this piece"""
    out = []
    for hd, tl in koi_mm:
        hd, tl = np.array(hd), np.array(tl); L = np.hypot(*(hd - tl)); u = (hd - tl) / max(L, 1e-6)
        out.append(LineString([tuple(tl - u * 0.12 * L), tuple(hd + u * 0.08 * L)]).buffer(0.15 * L))
    return out

_C = {}
def flora_mask(P, koi_mm, ppm=PPM, mt=None):
    key = (P, ppm)
    if key in _C: return _C[key]
    bb = BB[P]; mt = mt or F.pieces("M")[1]
    mk = np.array(MM.warp_piece(P, bb, ppm, mt)).astype(float)
    area = raster([F.clip_for("M", P)], bb, ppm)
    if P in ("FR", "FL"): area &= ~raster([F.keep_geoms("M", P)["welt"].buffer(4)], bb, ppm)
    area &= ~raster(koi_footprints(koi_mm), bb, ppm)
    bg = (mk.min(-1) > 196) & ((mk[..., 2] - mk[..., 0]) < 22)          # the white studio background around the garment
    lb, nb = ndi.label(bg); edge = np.unique(np.r_[lb[0], lb[-1], lb[:, 0], lb[:, -1]]); bg = np.isin(lb, edge[edge > 0])   # only where it reaches the edge
    area &= ~ndi.binary_dilation(bg, iterations=int(2 * ppm))
    if P in ("SR", "SL"):          # the inner sleeve edge overlaps the body in the front-view mockup: body vine leaves show there
        H, W = area.shape; xs = bb[0] + (np.arange(W) + 0.5) / ppm; ys = bb[1] + (np.arange(H) + 0.5) / ppm
        XX, YY = np.meshgrid(xs, ys); hw = mt["W"] + (mt["Ww"] - mt["W"]) * np.clip(YY, 0, None) / mt["Lu"]
        area &= (np.abs(XX) / hw) < 0.72
    fab = np.median(mk[area], axis=0)
    dist = np.sqrt(((mk - fab) ** 2).sum(-1)); L = mk.mean(-1); blue = mk[..., 2] - mk[..., 0]
    emb = area & (dist > 28) & ((blue > 40) | (L > 135)) & (mk[..., 0] < mk[..., 2] + 25)
    emb = ndi.binary_opening(emb, structure=qa.disk(2.0, ppm))              # topstitching / seam lines are thinner than 2 mm
    emb = ndi.binary_fill_holes(ndi.binary_closing(emb, structure=qa.disk(1.6, ppm))) & area
    # tones: luminance quartiles of the flora pixels, mode-filtered
    Ls = ndi.gaussian_filter(L, 0.8 * ppm)
    q = np.quantile(Ls[emb], [0.25, 0.5, 0.75]) if emb.any() else [0, 0, 0]
    tone = np.digitize(Ls, q)
    oh = np.stack([ndi.uniform_filter((tone == k).astype(float), int(3 * ppm) | 1) for k in range(4)], -1)
    tone = np.where(emb, oh.argmax(-1), -1)
    _C[key] = (emb, tone, bb)
    _L[key] = L
    return _C[key]

_L = {}
def lum(P, ppm=PPM): return _L[(P, ppm)]

def polys_of(mask, bb, ppm=PPM, min_mm2=4.0, smooth=0.5):
    """bool mask -> list of shapely polygons in piece mm (contours, holes kept), smoothed"""
    lab, n = ndi.label(mask); out = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        m = np.pad(lab[sl] == k, 2)
        if m.sum() / ppm**2 < min_mm2: continue
        rings = measure.find_contours(m.astype(float), 0.5)
        if not rings: continue
        y0, x0 = sl[0].start - 2, sl[1].start - 2
        P = [Polygon([(bb[0] + (x0 + c[1]) / ppm, bb[1] + (y0 + c[0]) / ppm) for c in r]).buffer(0) for r in rings if len(r) > 3]
        P = sorted([p for p in P if not p.is_empty], key=lambda p: -p.area)
        if not P: continue
        g = P[0]
        for h in P[1:]:
            if g.contains(h.representative_point()): g = g.difference(h)
        sm = min(smooth, 0.08 * g.area ** 0.5)            # small motifs keep their traced shape
        g = g.buffer(sm, join_style=1).buffer(-sm, join_style=1).simplify(0.1).buffer(0) if sm > 0.05 else g.simplify(0.1).buffer(0)
        if not g.is_empty: out.append(g)
    return out
