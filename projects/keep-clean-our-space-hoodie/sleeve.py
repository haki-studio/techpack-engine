"""Sleeve pieces for the star field (pattern S01 = right sleeve, S02 = left sleeve; sleeve coords from pattern.py:
x across (S01: back of cap x < 0, front x > 0; S02 mirrored), y down from the underarm line, cap top at y < 0).
Keep-outs from the sew lines: cap (armhole) seam 15, underarm seams 15, cuff seam 10 (self-fabric cuff, never embroidered)."""
import kccore
from shapely.geometry import LineString, Polygon
import front as F

KEEP = {"cap": 15.0, "underarm front": 15.0, "underarm back": 15.0, "cuff": 10.0}
MIN = dict(KEEP)

def piece(size, P):
    g, mt = F.pieces(size); return g[kccore.PIECE_CODE[P]]

def keep_geoms(size, P):
    pc = piece(size, P)
    out = {e.name: LineString(e.pts) for e in pc.edges}
    out["panel"] = pc.sew_poly()
    return out

def clip_for(size, P):
    k = keep_geoms(size, P); g = k["panel"]
    for nm, d in KEEP.items(): g = g.difference(k[nm].buffer(d))
    return g.buffer(0)

def clearances(geom, size, P):
    k = keep_geoms(size, P)
    return {nm: geom.distance(k[nm]) for nm in MIN}

def ratio(size, P):
    """(kx, ky, top_M, top_size): star positions follow the sleeve width at the underarm and the cap-top -> cuff length"""
    a = piece("M", P).sew_poly().bounds; b = piece(size, P).sew_poly().bounds
    return (b[2] - b[0]) / (a[2] - a[0]), (b[3] - b[1]) / (a[3] - a[1]), a[1], b[1]
