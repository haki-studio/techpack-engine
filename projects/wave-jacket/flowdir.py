"""Stitch direction by construction (PR #27 review 3, LESSONS A16): every stripe row runs ALONG its stripe and every foam
row ALONG its crest, whatever shape the traced region has.

Before: a stripe region sewed at the tangent of its own centreline (only when the region was elongated) or at its box
axis (blob-shaped tone regions, merged patches, gap fills), and narrow stripes as turning satin, i.e. ACROSS the stripe.
The close-ups show the opposite: long threads along every band (SR: 37 of 268 off-grain stripe tiles were across-satin,
the rest blob axes and centreline wobble).

STRIPES: one flow field per piece, built from the stripe GEOMETRY (not from any reference image): every boundary between
two stripe tones and every rope cord runs along the wave, so the field at a point is the doubled-angle average of those
edge segments within ~6 mm (Gaussian weight, cords x3). Each stripe region is cut into 6 mm cells and each cell is sewn
as tatami at the field angle + the cord twist of its tone (wavecore.CORD_TWIST, alternating per tone). Narrow stripes
(the old turning satins) are sewn the same way (rows along).
FOAM (lockstitch alternate; chenille is the primary look): padded foam cells (4 mm) sew parallel to the nearest crest
outline - the contour-cord look of the close-ups - instead of tangents around a guessed eye.
Source of every angle: 'outline' (built from the art's own region edges; LESSONS A28 bucket).
usage: import flowdir; flowdir.install(vis) before dst2.make_pattern (build_size.py)."""
import math
import numpy as np
from shapely.geometry import box, Point, LineString
from shapely.ops import unary_union
from scipy.spatial import cKDTree

CELL_WV, CELL_FM, SIG = 6.0, 4.0, 4.0
_F = {"tree": None}

def _segs_of(g, step=1.0):
    out = []
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        if p.is_empty or p.length < step: continue
        q = p.segmentize(step); cs = np.array(q.coords)
        if len(cs) > 1: out.append(cs)
    return out

def build_field(vis):
    """flow field of the stripes: (midpoints, doubled-angle unit vectors, weights) of the tone edges + rope cords"""
    wv = [r for r in vis if r["grp"] == "WV"]; rp = [r for r in vis if r["grp"] == "RP"]
    by = {}
    for r in wv: by.setdefault(r["col"], []).append(r["geom"])
    U = {c: unary_union(g).buffer(0) for c, g in by.items()}
    lines = []
    cols = list(U)
    for i, a in enumerate(cols):                       # edges between two stripe tones
        for b in cols[i + 1:]:
            e = U[a].buffer(0.3).intersection(U[b].buffer(0.3))
            if e.is_empty: continue
            sk = e.boundary
            lines += [(cs, 1.0) for cs in _segs_of(sk)]
    for r in rp:                                       # rope cords: their long sides run along the stripe
        lines += [(cs, 3.0) for cs in _segs_of(r["geom"].exterior if r["geom"].geom_type == "Polygon" else r["geom"].boundary)]
    if not lines:                                      # fall back to the stripes' own outlines
        for g in U.values(): lines += [(cs, 1.0) for cs in _segs_of(g.boundary)]
    M, V, W = [], [], []
    for cs, w in lines:
        d = np.diff(cs, axis=0); L = np.hypot(d[:, 0], d[:, 1]); ok = L > 1e-6
        a = np.arctan2(d[ok, 1], d[ok, 0])
        M.append((cs[:-1][ok] + cs[1:][ok]) / 2); V.append(np.c_[np.cos(2 * a), np.sin(2 * a)]); W.append(L[ok] * w)
    M, V, W = np.concatenate(M), np.concatenate(V), np.concatenate(W)
    _F.update(tree=cKDTree(M), M=M, V=V, W=W)
    return len(M)

def field_angle(x, y):
    t = _F["tree"]
    if t is None: return None
    idx = t.query_ball_point([x, y], 3 * SIG)
    if not idx:
        d, i = t.query([x, y]); idx = [i]
    idx = np.array(idx); d2 = ((_F["M"][idx] - [x, y]) ** 2).sum(1)
    w = _F["W"][idx] * np.exp(-d2 / (2 * SIG * SIG)) + 1e-12
    c, s = (w[:, None] * _F["V"][idx]).sum(0)
    return math.degrees(0.5 * math.atan2(s, c))

def cells(p, size):
    b = p.bounds; out = []
    for x in np.arange(b[0], b[2], size):
        for y in np.arange(b[1], b[3], size):
            q = p.intersection(box(x, y, x + size, y + size))
            for g in (q.geoms if hasattr(q, "geoms") else [q]):
                if g.geom_type == "Polygon" and g.area > 0.05: out.append(g)
    return out

def outline_angle(p, c):
    """direction of the region outline nearest to point c (rows parallel to the crest edge)"""
    bd = p.exterior
    s = bd.project(c); L = bd.length
    a, b = bd.interpolate((s - 0.8) % L), bd.interpolate((s + 0.8) % L)
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x))

def wv_parts(p, twist):
    return [(q, field_angle(*q.representative_point().coords[0]) + twist) for q in cells(p, CELL_WV)]

def fm_parts(p):
    return [(q, outline_angle(p, q.representative_point())) for q in cells(p, CELL_FM)]

LOG = {"wv_cells": 0, "fm_cells": 0, "field_pts": 0}
def install(vis):
    """call once per piece before stitching: builds the stripe field from this piece's art"""
    LOG["field_pts"] = build_field(vis)
