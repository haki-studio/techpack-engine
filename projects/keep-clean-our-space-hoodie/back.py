"""Back piece for the Rev H back star field (pattern B01, founder 21 Oct 2026: stars only on the back, hood plain).
Back coords from the pattern: x from CB (+ = wearer's right on a back view), y down from the CB neck seam.
Keep-outs from the sew lines of each size's drafted B01 (LESSONS C8): hood / neck seam 10, shoulder 15, armhole 15,
side seams 15, hem-band seam 10 — the same distances as the fronts."""
import kccore
from shapely.geometry import LineString
import front as F

KEEP = {"neck": 10.0, "shoulder L": 15.0, "shoulder R": 15.0, "armhole L": 15.0, "armhole R": 15.0,
        "side L": 15.0, "side R": 15.0, "hem": 10.0}
MIN = dict(KEEP)
LABEL = {"neck": "hood neck", "shoulder L": "shoulder", "shoulder R": "shoulder", "armhole L": "armhole", "armhole R": "armhole",
         "side L": "side", "side R": "side", "hem": "hem band"}

def piece(size): g, mt = F.pieces(size); return g["B01"]

def keep_geoms(size):
    pc = piece(size)
    out = {e.name: LineString(e.pts) for e in pc.edges}
    out["panel"] = pc.sew_poly()
    return out

def clip_for(size):
    k = keep_geoms(size); g = k["panel"]
    for nm, d in KEEP.items(): g = g.difference(k[nm].buffer(d))
    return g.buffer(0)

def clearances(geom, size):
    k = keep_geoms(size)
    return {nm: geom.distance(k[nm]) for nm in MIN}

def ratio(size):
    """(kx, ky, top_M, top_size): star positions follow the back width and the neck -> hem length"""
    a = piece("M").sew_poly().bounds; b = piece(size).sew_poly().bounds
    return (b[2] - b[0]) / (a[2] - a[0]), (b[3] - b[1]) / (a[3] - a[1]), a[1], b[1]
