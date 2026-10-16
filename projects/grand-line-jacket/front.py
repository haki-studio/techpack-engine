"""Garment model for the front scene — Drum Island block (same jacket silhouette, same pattern).
Garment coords (mm): x from CF (+ = wearer's LEFT = viewer's right on a front view), y down from the CF neck seam.
Keeps the API the engine expects from a project `front` module (pattern.py reads WELT_L; techflat reads COLLAR_*,
WELT_*), with the Drum Island welt + collar geometry unchanged (the pattern is shared)."""
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import drum

BLK = drum.Block("M")
HEM = BLK.f_hem
PANEL_R = BLK.front_panel(-1)
PANEL_L = BLK.front_panel(+1)
ARM_R = unary_union([BLK.front_shoulder_line(-1), BLK.front_arm_line(-1)])
SIDE_R = BLK.front_side_line(-1)
_neck = [(-x, y) for x, y in drum.curve((0, 0), BLK.f_hps, 28, 16)]
COLLAR_R = Polygon(_neck + [(-176, -76), (-150, -30), (-72, 66), (-14, 22)]).buffer(0)    # collar lying flat (Drum Island)
COLLAR_L = affinity.scale(COLLAR_R, -1, 1, origin=(0, 0))

# Welt pockets: Drum Island welt size (1.4 x 13 cm, pattern.py WELT_L/WELT_W) at THIS mockup's angle (38 deg) and
# position, moved 18 mm toward CF so the outer end clears the side seam by ~43 mm (the render draws it touching the seam).
# pattern.py derives every size's welt box from WELT_L (centre graded with the chest, height kept above the hem).
WELT_C, WELT_ANG, WELT_LEN, WELT_W = (205.0, 347.0), 38.0, 130.0, 14.0         # wearer's left; right = mirror  [PROPOSED]
def _welt(side):
    ux, uy = np.cos(np.radians(WELT_ANG)), np.sin(np.radians(WELT_ANG))
    c = np.array([WELT_C[0]*side, WELT_C[1]]); u = np.array([ux*side, uy])
    a, b = c - u*WELT_LEN/2, c + u*WELT_LEN/2          # top-inner -> bottom-outer
    return LineString([a, b]).buffer(WELT_W/2, cap_style="flat", join_style="mitre")
WELT_R = _welt(-1)
WELT_L = _welt(+1)

KEEP_CF, KEEP_SEAM, KEEP_HEM, KEEP_WELT, KEEP_COLLAR = 15.0, 15.0, 10.0, 6.0, 6.0
KEEP = {"CF / zip": KEEP_CF, "armhole": KEEP_SEAM, "shoulder": KEEP_SEAM, "side": KEEP_SEAM, "hem": KEEP_HEM}

_PC = {}
def pieces(size):
    if size not in _PC:
        import pattern as PT
        _PC[size] = PT.draft(size)
    return _PC[size]

def keep_geoms(size, side):
    """named keep-out references for one front piece of one size, from that size's pattern (sew lines)."""
    g, mt = pieces(size); pc = g["F02" if side == "R" else "F01"]
    out = {e.name: LineString(e.pts) for e in pc.edges}
    out["welt"] = Polygon(pc.internal[0][1]).buffer(0)
    out["collar"] = COLLAR_R if side == "R" else COLLAR_L
    out["panel"] = pc.sew_poly()
    return out

MIN = {"CF / zip": KEEP_CF, "armhole": KEEP_SEAM, "shoulder": KEEP_SEAM, "side": KEEP_SEAM, "hem": KEEP_HEM,
       "welt": KEEP_WELT, "collar": KEEP_COLLAR}

def clip_for(size, side):
    """area art may occupy on one front piece of one size (all keep-outs removed)."""
    k = keep_geoms(size, side)
    g = k["panel"]
    for nm, d in KEEP.items(): g = g.difference(k[nm].buffer(d))
    g = g.difference(k["welt"].buffer(KEEP_WELT)).difference(k["collar"].buffer(KEEP_COLLAR))
    g = g.difference(k["neck"].buffer(KEEP_COLLAR))
    return g.buffer(0)

def clearances(geom, size, side):
    k = keep_geoms(size, side)
    return {nm: geom.distance(k[nm]) for nm in MIN}
