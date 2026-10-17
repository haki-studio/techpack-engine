"""Garment model for the koi blossom hoodie — Drum Island body (hooded variant when the engine has it).
Garment coords (mm): fronts x from CF (+ = wearer's LEFT = viewer's right on a front view), y down from the CF neck seam.
Sleeves: pattern coords of S01 (wearer's right sleeve: cap top at y = -cap_h, underarm line y = 0, cuff seam y = Lu,
front half x > 0) and S02 (wearer's left sleeve = mirror, front half x < 0).
Keeps the API pattern.py expects from a project `front` module (WELT_L) plus keep-outs per size + piece, taken from that
size's drafted pattern (LESSONS C8)."""
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import drum, mockmap as MM

BLK = drum.Block("M")
HEM = BLK.f_hem
PANEL_R = BLK.front_panel(-1)
PANEL_L = BLK.front_panel(+1)
COLLAR_R = Polygon(); COLLAR_L = Polygon()            # hooded: no collar lying on the front

# Welt pockets at the mockup position + angle (front.png: FR welt (235,588)->(170,712), FL (510,600)->(578,722)),
# Drum Island welt size 1.4 x 13 cm. [PROPOSED]
_a, _b = np.array(MM.P(510, 600)), np.array(MM.P(578, 722))
_c = (_a + _b) / 2; _a2, _b2 = np.array(MM.P(235, 588)), np.array(MM.P(170, 712)); _c2 = (_a2 + _b2) / 2
WELT_C = ((abs(_c[0]) + abs(_c2[0])) / 2, (_c[1] + _c2[1]) / 2)
WELT_ANG = float(np.degrees(np.arctan2((_b - _a)[1], (_b - _a)[0]) + np.arctan2((_b2 - _a2)[1], -(_b2 - _a2)[0])) / 2)
WELT_LEN, WELT_W = 130.0, 14.0
def _welt(side):
    ux, uy = np.cos(np.radians(WELT_ANG)), np.sin(np.radians(WELT_ANG))
    c = np.array([WELT_C[0]*side, WELT_C[1]]); u = np.array([ux*side, uy])
    a, b = c - u*WELT_LEN/2, c + u*WELT_LEN/2
    return LineString([a, b]).buffer(WELT_W/2, cap_style="flat", join_style="mitre")
WELT_R = _welt(-1)
WELT_L = _welt(+1)

KEEP_CF, KEEP_SEAM, KEEP_HEM, KEEP_WELT, KEEP_NECK = 15.0, 15.0, 10.0, 6.0, 6.0
KEEP_CUFF, KEEP_CAP = 10.0, 15.0
MIN_FRONT = {"CF / zip": KEEP_CF, "armhole": KEEP_SEAM, "shoulder": KEEP_SEAM, "side": KEEP_SEAM, "hem": KEEP_HEM,
             "welt": KEEP_WELT, "neck": KEEP_NECK}
MIN_SLEEVE = {"cap": KEEP_CAP, "underarm front": KEEP_SEAM, "underarm back": KEEP_SEAM, "cuff": KEEP_CUFF}
def MIN(P): return MIN_FRONT if P in ("FR", "FL") else MIN_SLEEVE

VARIANT = None          # set by pieces(): "hooded" once engine/pattern.py has it, else the Drum Island draft
_PC = {}
def pieces(size):
    global VARIANT
    if size not in _PC:
        import pattern as PT
        try:
            _PC[size] = PT.draft(size, variant="hooded"); VARIANT = "hooded"
        except TypeError:
            _PC[size] = PT.draft(size); VARIANT = "drum-island"
    return _PC[size]

CODE = {"FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}
def keep_geoms(size, P):
    """named keep-out references for one piece of one size, from that size's pattern (sew lines)."""
    g, mt = pieces(size); pc = g[CODE[P]]
    out = {e.name: LineString(e.pts) for e in pc.edges}
    if P in ("FR", "FL"): out["welt"] = Polygon(pc.internal[0][1]).buffer(0)
    out["panel"] = pc.sew_poly()
    return out

def clip_for(size, P):
    """area art may occupy on one piece of one size (all keep-outs removed)."""
    k = keep_geoms(size, P); g = k["panel"]
    for nm, d in MIN(P).items():
        if nm in k: g = g.difference(k[nm].buffer(d))
    if P in ("SR", "SL"):           # visible front half of the sleeve only (the mockup shows nothing on the back half)
        g = g.intersection(box(0, -400, 400, 900) if P == "SR" else box(-400, -400, 0, 900))
    return g.buffer(0)

def clearances(geom, size, P):
    k = keep_geoms(size, P)
    return {nm: geom.distance(k[nm]) for nm in MIN(P) if nm in k}
