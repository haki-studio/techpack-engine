"""Garment model for the fronts — Drum Island block body (hooded variant: the collar is replaced by a hood sewn to the
neck seam). Garment coords (mm): x from CF (+ = wearer's LEFT = viewer's right on a front view), y down from the CF
neck seam. Keeps the API the engine expects from a project `front` module (pattern.py reads WELT_L).
Keep-outs are measured on the drafted pattern pieces of each size (LESSONS C8)."""
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import drum

BLK = drum.Block("M")
HEM = BLK.f_hem
PANEL_R = BLK.front_panel(-1)
PANEL_L = BLK.front_panel(+1)

# Welt pockets: Drum Island welt size (1.4 x 13 cm, pattern.py WELT_L/WELT_W) at THIS mockup's angle and position
# (steep slash welts beside the side seam; mockup welts mapped: centre (+/-252, 358), 58 deg). Centre moved 7 mm toward
# CF so the outer end clears the side seam by ~14 mm.  [PROPOSED]
WELT_C, WELT_ANG, WELT_LEN, WELT_W = (245.0, 360.0), 58.0, 130.0, 14.0         # wearer's left; right = mirror
def _welt(side):
    ux, uy = np.cos(np.radians(WELT_ANG)), np.sin(np.radians(WELT_ANG))
    c = np.array([WELT_C[0]*side, WELT_C[1]]); u = np.array([ux*side, uy])
    a, b = c - u*WELT_LEN/2, c + u*WELT_LEN/2          # top-inner -> bottom-outer
    return LineString([a, b]).buffer(WELT_W/2, cap_style="flat", join_style="mitre")
WELT_R = _welt(-1)
WELT_L = _welt(+1)
COLLAR_R = Polygon()          # hooded: no collar lies on the front (techflat compatibility)
COLLAR_L = Polygon()

KEEP_CF, KEEP_SEAM, KEEP_HEM, KEEP_WELT, KEEP_NECK = 15.0, 15.0, 10.0, 6.0, 10.0
KEEP = {"CF / zip": KEEP_CF, "armhole": KEEP_SEAM, "shoulder": KEEP_SEAM, "side": KEEP_SEAM, "hem": KEEP_HEM, "neck": KEEP_NECK}
MIN = dict(KEEP, welt=KEEP_WELT)

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
    # the merged engine block drafts the Drum Island welt (38 deg, centre ~170 from CF) — it sits on badges 03 / 04. Until
    # pattern.draft takes a welt override (ENGINE_NOTES 10) the keep-out uses THIS mockup's slash welt (as Rev A did).
    out["welt"] = WELT_R if side == "R" else WELT_L
    out["welt_engine"] = Polygon(pc.internal[0][1]).buffer(0)
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
