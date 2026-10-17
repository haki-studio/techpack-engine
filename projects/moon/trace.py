"""Tonal tracer: mockup crop -> stitch regions (Rev B, fidelity first).
The crop is upscaled x4 (Lanczos) only to read shapes and colour boundaries (it adds no detail, pipeline §0b);
every pixel is assigned to the nearest palette tone (CIE Lab), boundaries are smoothed with a majority filter,
and each tone becomes polygons (even-odd nesting -> holes). Thin parts of a 'line' tone become centre lines
(skeleton) for bean stitching. Coordinates out: mockup px (the caller maps px -> garment mm)."""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
from skimage import measure, morphology
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import unary_union
import tech

def lab_img(a):
    a = a / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    XYZ = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(XYZ > 0.008856, np.cbrt(XYZ), 7.787 * XYZ + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

def hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def label_map(img, box, tones, up=4, sigma=0.6, majority=7, mask=None):
    """tones: [(name, (r,g,b))]. Returns (labels[H,W] int, -1 outside mask), up."""
    x0, y0, x1, y1 = box
    c = img.crop(box).resize(((x1 - x0) * up, (y1 - y0) * up), Image.LANCZOS)
    if sigma: c = c.filter(ImageFilter.GaussianBlur(sigma * up))
    a = np.asarray(c.convert("RGB")).astype(float); L = lab_img(a)
    P = lab_img(np.array([t[1] for t in tones], float)[None, :, :])[0]
    best = np.full(L.shape[:2], np.inf); lab = np.zeros(L.shape[:2], int)
    for i, p in enumerate(P):
        d = ((L - p) ** 2).sum(-1); w = d < best; best[w] = d[w]; lab[w] = i
    if majority:
        oh = np.stack([ndi.uniform_filter((lab == i).astype(float), majority) for i in range(len(tones))], -1)
        lab = oh.argmax(-1)
    if mask is not None:
        m = mask(np.mgrid[0:lab.shape[0], 0:lab.shape[1]], up, box)
        lab = np.where(m, lab, -1)
    return lab, up

def polys_of(m, up, box, min_px=6, simplify=0.15):
    """binary mask (upscaled) -> shapely geometry in mockup px"""
    x0, y0 = box[0], box[1]
    m = morphology.remove_small_objects(m, min_px * up * up // 4) if m.any() else m
    m = morphology.remove_small_holes(m, min_px * up * up // 4) if m.any() else m
    rings = []
    for cnt in measure.find_contours(np.pad(m, 1).astype(float), 0.5):
        if len(cnt) < 4: continue
        p = Polygon([((c - 1 + 0.5) / up + x0, (r - 1 + 0.5) / up + y0) for r, c in cnt]).buffer(0)
        if not p.is_empty and p.area > 0: rings.append(p)
    if not rings: return Polygon()
    # even-odd nesting by containment depth (fast: STRtree), assembled level by level
    from shapely.strtree import STRtree
    tree = STRtree(rings); depth = []
    for i, p in enumerate(rings):
        rp = p.representative_point()
        depth.append(sum(1 for j in tree.query(rp, predicate="intersects") if j != i and rings[j].area > p.area and rings[j].contains(rp)))
    out = Polygon()
    for d in range(max(depth) + 1):
        lv = unary_union([p for p, dd in zip(rings, depth) if dd == d])
        out = out.union(lv) if d % 2 == 0 else out.difference(lv)
    return out.simplify(simplify).buffer(0)

def lines_of(m, up, box, min_len_px=3.0):
    """thin mask -> centre lines (mockup px)"""
    x0, y0 = box[0], box[1]
    sk = morphology.skeletonize(m)
    lab, n = ndi.label(sk, structure=np.ones((3, 3)))
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < min_len_px * up: continue
        # order the skeleton pixels along their principal axis (good enough for short strokes)
        P = np.c_[xs, ys].astype(float); c = P.mean(0); u = np.linalg.svd(P - c)[2][0]
        o = np.argsort((P - c) @ u); P = P[o]
        k = max(1, up); P = P[::k]
        if len(P) >= 2:
            ln = LineString([((x + 0.5) / up + x0, (y + 0.5) / up + y0) for x, y in P]).simplify(0.3)
            if ln.length >= min_len_px: out.append(ln)
    return out

def trace(img, box, tones, keep, line_tone=None, line_w_px=1.6, mask=None, up=4, sigma=0.6, majority=7, min_px=6, fill_holes_from=None):
    """returns {tone_name: geometry px} for tones in `keep`, + 'LINES': [LineString px] from the thin part of line_tone.
    fill_holes_from: tones whose pixels are re-assigned to the nearest kept tone (e.g. figure / fabric inside the moon)."""
    lab, up = label_map(img, box, tones, up, sigma, majority, mask)
    names = [t[0] for t in tones]
    if fill_holes_from:
        bad = np.isin(lab, [names.index(n) for n in fill_holes_from]) & (lab >= 0)
        good = np.isin(lab, [names.index(n) for n in keep])
        if bad.any() and good.any():
            _, (iy, ix) = ndi.distance_transform_edt(~good, return_indices=True)
            lab = np.where(bad, lab[iy, ix], lab)
    out = {}; lines = []
    for n in keep:
        m = lab == names.index(n)
        if n == line_tone:
            r = max(1, int(line_w_px * up / 2))
            thick = morphology.binary_opening(m, morphology.disk(r))
            thin = m & ~morphology.binary_dilation(thick, morphology.disk(1))
            lines = lines_of(thin, up, box)
            m = thick
        out[n] = polys_of(m, up, box, min_px)
    out["LINES"] = lines
    out["_lab"] = (lab, up)
    return out

def dark_lines(img, box, size=9, thr=16, min_len_px=6.0, mask=None):
    """thin dark strokes (scale-row lines, crater rays, wood grain) from the UNsmoothed image: black top-hat on
    luminance -> threshold -> skeleton -> polylines (mockup / close-up px). mask(xx, yy) -> bool limits the area."""
    x0, y0, x1, y1 = box
    a = np.asarray(img.crop(box).convert("L")).astype(float)
    a = ndi.gaussian_filter(a, 0.7)
    th = ndi.grey_closing(a, size=(size, size)) - a
    m = th > thr
    if mask is not None:
        yy, xx = np.mgrid[y0:y1, x0:x1]; m &= mask(xx, yy)
    m = morphology.remove_small_objects(m, 8)
    return lines_of(m, 1, box, min_len_px)

def fill_inside(lab, keep_ids, region):
    """inside `region` (bool), every pixel not in keep_ids takes the nearest keep label (no holes of fabric in a motif)"""
    good = np.isin(lab, keep_ids)
    if not good.any(): return lab
    _, (iy, ix) = ndi.distance_transform_edt(~good, return_indices=True)
    return np.where(region & ~good, lab[iy, ix], lab)
