"""Garment model — Drum Island body (same fronts, back, sleeves), hood instead of the collar.
Garment coords (mm): fronts x from CF (+ = wearer's LEFT = viewer's right on a front view), y down from the CF neck seam.
Sleeves: pattern coords of S01 (right sleeve; x < 0 = back half of the cap, x > 0 = front half, y = 0 underarm line,
cap top at y < 0, cuff seam at the bottom). The left sleeve S02 is the mirror (front half at x < 0).
Keeps the API the engine expects from a project `front` module (pattern.py reads WELT_L; techflat reads COLLAR_*, WELT_*).

Hood: the hooded block is being added to the engine (pattern.draft(size, variant="hooded")). pieces() uses it as soon
as the engine has it; until then the Drum Island pieces are used (the body pieces are the same block)."""
import inspect
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import drum

BLK = drum.Block("M")
HEM = BLK.f_hem
PANEL_R = BLK.front_panel(-1)
PANEL_L = BLK.front_panel(+1)
# no collar on this jacket: empty placeholders keep techflat / pattern happy (the hood is drawn separately)
COLLAR_R = Polygon(); COLLAR_L = Polygon()

# Welt pockets: Drum Island welt size (1.4 x 13 cm, pattern.py WELT_L/WELT_W) at THIS mockup's angle + position
# (mockup welts: centre 218 mm from CF, 352 mm below the CF neck, 54° from horizontal)  [PROPOSED]
WELT_C, WELT_ANG, WELT_LEN, WELT_W = (218.0, 352.0), 54.0, 130.0, 14.0         # wearer's left; right = mirror
def _welt(side):
    ux, uy = np.cos(np.radians(WELT_ANG)), np.sin(np.radians(WELT_ANG))
    c = np.array([WELT_C[0]*side, WELT_C[1]]); u = np.array([ux*side, uy])
    a, b = c - u*WELT_LEN/2, c + u*WELT_LEN/2          # top-inner -> bottom-outer
    return LineString([a, b]).buffer(WELT_W/2, cap_style="flat", join_style="mitre")
WELT_R = _welt(-1)
WELT_L = _welt(+1)

KEEP_CF, KEEP_SEAM, KEEP_HEM, KEEP_WELT, KEEP_NECK = 15.0, 15.0, 10.0, 6.0, 10.0
KEEP = {"CF / zip": KEEP_CF, "armhole": KEEP_SEAM, "shoulder": KEEP_SEAM, "side": KEEP_SEAM, "hem": KEEP_HEM, "neck": KEEP_NECK}
MIN = dict(KEEP, welt=KEEP_WELT)
# sleeves: cap seam 15, underarm seams 15, cuff seam 10; art only on the front-facing half (+ 30 mm past the
# shoulder line so the art reaches the outer silhouette as in the mockup) [PROPOSED]
SKEEP = {"cap": KEEP_SEAM, "underarm front": KEEP_SEAM, "underarm back": KEEP_SEAM, "cuff": KEEP_HEM}
SMIN = dict(SKEEP)
SLEEVE_BACK_REACH = 30.0

def hooded_available():
    import pattern as PT
    try: return "variant" in inspect.signature(PT.draft).parameters
    except (TypeError, ValueError): return False

_PC = {}
def pieces(size):
    if size not in _PC:
        import pattern as PT
        _PC[size] = PT.draft(size, variant="hooded") if hooded_available() else PT.draft(size)
    return _PC[size]

def keep_geoms(size, side):
    """named keep-out references for one front piece of one size, from that size's pattern (sew lines)."""
    g, mt = pieces(size); pc = g["F02" if side == "R" else "F01"]
    out = {e.name: LineString(e.pts) for e in pc.edges}
    out["welt"] = Polygon(pc.internal[0][1]).buffer(0)
    out["panel"] = pc.sew_poly()
    return out

def clip_for(size, side):
    """area art may occupy on one front piece of one size (all keep-outs removed)."""
    k = keep_geoms(size, side)
    g = k["panel"]
    for nm, d in KEEP.items(): g = g.difference(k[nm].buffer(d))
    g = g.difference(k["welt"].buffer(KEEP_WELT))
    return g.buffer(0)

def clearances(geom, size, side):
    k = keep_geoms(size, side)
    return {nm: geom.distance(k[nm]) for nm in MIN}

# ---------------------------------------------------------------- sleeves
def sleeve_geoms(size, side):
    """side 'R' = S01 (front half x > 0), 'L' = S02 (mirror, front half x < 0)"""
    g, mt = pieces(size); pc = g["S01" if side == "R" else "S02"]
    out = {e.name: LineString(e.pts) for e in pc.edges}
    out["panel"] = pc.sew_poly()
    return out

def sleeve_clip(size, side):
    k = sleeve_geoms(size, side); g = k["panel"]
    for nm, d in SKEEP.items(): g = g.difference(k[nm].buffer(d))
    sgn = 1 if side == "R" else -1
    g = g.intersection(box(-SLEEVE_BACK_REACH, -400, 400, 900) if sgn > 0 else box(-400, -400, SLEEVE_BACK_REACH, 900))
    return g.buffer(0)

def sleeve_clearances(geom, size, side):
    k = sleeve_geoms(size, side)
    return {nm: geom.distance(k[nm]) for nm in SMIN}
