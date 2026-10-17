"""The five embroidered pattern pieces of the wave jacket, their keep-outs and clearance checks (per size, from the
drafted pattern — LESSONS A3, C8: keep-out lines come from the pattern piece, never from the block).

  BK  B01 back                 FR  F02 wearer's right front     FL  F01 wearer's left front
  SR  S01 right sleeve         SL  S02 left sleeve
Keep-outs (mm from the sew line): side seams 15, CF / zip 15, shoulder 15, hem-rib seam 10, welt box 6, collar lying
flat 6, neck 6, sleeve underarm seams 15, cuff seam 10. ARMHOLE / CAP = 3 (wrap seam, LESSONS A4: the wave crosses
the armhole on the render, so it stops 3 short of the seam on both pieces and lines up across it)."""
import functools
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid
import mockmap as MM
import front as FR

PIECES = ["BK", "FR", "FL", "SR", "SL"]
CODE = {"BK": "B01", "FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}
NAME = {"BK": "back", "FR": "wearer's right front", "FL": "wearer's left front", "SR": "right sleeve", "SL": "left sleeve"}
WRAP = 3.0
KEEP = {
    "BK": {"side L": 15, "side R": 15, "shoulder L": 15, "shoulder R": 15, "hem": 10, "neck": 6, "armhole L": WRAP, "armhole R": WRAP},
    "FR": {"CF / zip": 15, "side": 15, "shoulder": 15, "hem": 10, "neck": 6, "armhole": WRAP, "welt": 6, "collar": 6},
    "FL": {"CF / zip": 15, "side": 15, "shoulder": 15, "hem": 10, "neck": 6, "armhole": WRAP, "welt": 6, "collar": 6},
    "SR": {"cap": WRAP, "underarm front": 15, "underarm back": 15, "cuff": 10},
    "SL": {"cap": WRAP, "underarm front": 15, "underarm back": 15, "cuff": 10},
}
MIN = KEEP

def draft(size): return MM.draft(size)

@functools.lru_cache(maxsize=None)
def refs(size, P):
    """named keep-out references (sew lines / welt box / collar) for one piece of one size"""
    g, mt = draft(size); pc = g[CODE[P]]
    out = {e.name: LineString(e.pts) for e in pc.edges}
    if P in ("FR", "FL"):
        out["welt"] = Polygon(pc.internal[0][1]).buffer(0)
        out["collar"] = FR.COLLAR_R if P == "FR" else FR.COLLAR_L
    out["panel"] = pc.sew_poly()
    return out

@functools.lru_cache(maxsize=None)
def clip_for(size, P):
    """area the art may occupy on one piece of one size (all keep-outs removed)"""
    r = refs(size, P); g = r["panel"]
    for nm, d in KEEP[P].items(): g = g.difference(r[nm].buffer(d))
    return make_valid(g).buffer(0)

def clearances(geom, size, P):
    r = refs(size, P)
    return {nm: geom.distance(r[nm]) for nm in KEEP[P]}

def panel(size, P): return refs(size, P)["panel"]
