"""Garment model — Drum Island body (brief: hooded variant; the hood replaces the collar, body pieces unchanged).
Garment coords (mm): fronts x from CF (+ = wearer's LEFT = viewer's right on a front view), y down from the CF neck seam.
Sleeves: S01 (wearer's right) / S02 (wearer's left) pattern coords (pattern.py): y = 0 at the underarm line, cap top at
y = -cap_h, cuff seam at y = Lu; S01 front half x > 0, S02 front half x < 0.
Keeps the API pattern.py expects from a project `front` module (WELT_L)."""
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import drum

BLK = drum.Block("M")
HEM = BLK.f_hem
PANEL_R = BLK.front_panel(-1)
PANEL_L = BLK.front_panel(+1)

# Welt pockets: Drum Island welt size (1.4 x 13 cm, pattern.py WELT_L/WELT_W) at THIS mockup's angle (61.6 deg from
# horizontal, top end toward CF). Mockup centre (196.7, 391) puts the FL welt under the beast's lower jaw (render
# artefact: you can't embroider across a welt opening) -> moved by the smallest move that clears the head by 6 mm
# (welt_solve.py writes welt.json). Both sides symmetric. [PROPOSED]
import json, os
_W = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "welt.json"))) if os.path.exists(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "welt.json")) else {"c": [196.7, 391.0], "ang": 61.6}
WELT_MOCK_C = (196.7, 391.0)
WELT_C, WELT_ANG, WELT_LEN, WELT_W = tuple(_W["c"]), float(_W["ang"]), 130.0, 14.0
def _welt(side, c=None, ang=None):
    c = c or WELT_C; ang = WELT_ANG if ang is None else ang
    ux, uy = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    cc = np.array([c[0]*side, c[1]]); u = np.array([ux*side, uy])
    a, b = cc - u*WELT_LEN/2, cc + u*WELT_LEN/2          # top-inner -> bottom-outer
    return LineString([a, b]).buffer(WELT_W/2, cap_style="flat", join_style="mitre")
WELT_R = _welt(-1)
WELT_L = _welt(+1)

KEEP_CF, KEEP_SEAM, KEEP_HEM, KEEP_WELT, KEEP_NECK = 15.0, 15.0, 10.0, 6.0, 10.0
KEEP_CUFF = 10.0
KEEP = {"CF / zip": KEEP_CF, "armhole": KEEP_SEAM, "shoulder": KEEP_SEAM, "side": KEEP_SEAM, "hem": KEEP_HEM, "neck": KEEP_NECK}
MIN = dict(KEEP, welt=KEEP_WELT)
SKEEP = {"cap": KEEP_SEAM, "underarm front": KEEP_SEAM, "underarm back": KEEP_SEAM, "cuff": KEEP_CUFF}

# Rev B: the founder chose the zip-hoodie block (engine/hoodie.py: Drum Island body + 3-panel hood + elastic hem/cuff
# bands, 19 Oct 2026). The moved welt goes into the pattern itself (per-design override, engine 08ef40a) [PROPOSED].
WELT_SPEC = dict(cx=WELT_C[0], cy=WELT_C[1], angle=WELT_ANG, length=WELT_LEN, width=WELT_W)
_PC = {}
def pieces(size):
    if size not in _PC:
        import hoodie as HD
        _PC[size] = HD.draft(size, welt=WELT_SPEC)
    return _PC[size]
def block():
    import hoodie as HD
    return HD.Variant(welt=WELT_SPEC)

def keep_geoms(size, side):
    """named keep-out references for one front piece of one size, from that size's pattern (sew lines, LESSONS C8)."""
    g, mt = pieces(size); pc = g["F02" if side == "R" else "F01"]
    out = {e.name: LineString(e.pts) for e in pc.edges}
    out["welt"] = Polygon(pc.internal[0][1]).buffer(0)          # the pattern's own (moved, PROPOSED) welt
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
    g, mt = pieces(size); pc = g["S01" if side == "R" else "S02"]
    out = {e.name: LineString(e.pts) for e in pc.edges}
    out["panel"] = pc.sew_poly()
    return out

def sleeve_clip(size, side):
    k = sleeve_geoms(size, side); g = k["panel"]
    for nm, d in SKEEP.items(): g = g.difference(k[nm].buffer(d))
    return g.buffer(0)

def sleeve_clearances(geom, size, side):
    k = sleeve_geoms(size, side)
    return {nm: geom.distance(k[nm]) for nm in SKEEP}

def piece_clip(size, P):
    return clip_for(size, P[1]) if P[0] == "F" else sleeve_clip(size, P[1])
def piece_clear(geom, size, P):
    return clearances(geom, size, P[1]) if P[0] == "F" else sleeve_clearances(geom, size, P[1])
def piece_min(P): return MIN if P[0] == "F" else SKEEP
