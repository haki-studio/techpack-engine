"""Tetra fish (founder change 19 Oct 2026: the fish are NOT koi) — drawn from inputs/reference_fish.png.
Side view, flat cel-shaded facets (angular polygons, no scales):
  body       3 faceted tones with their own stitch directions: silver-white lit flank (tatami, +25 deg to the axis),
             pale-ice dorsal + head facet (satin, turning), lavender-grey lower-flank / jaw shadow facet (tatami, -20 deg),
             light belly strip (white, satin)
  cyan line  crisp satin band along the upper flank, head -> mid-body (runs along the body axis)
  red stripe crisp satin wedge from mid-body to the tail root, widening toward the tail
  eye        small black dot on a white ring
  fins       small pointed dorsal, pectoral, pelvic + anal fins (ice, radial from the fin root)
  tail       forked; upper lobe white, lower lobe lavender-grey (radial from the peduncle)
Proportions measured on the reference (body depth ≈ 0.25 L, tail ≈ 0.25 L, L = snout -> tail-lobe tip).
Local frame: x from the snout (0) to the tail tip (L), y + = belly. fish(...) puts the head toward `ang` and keeps the
belly on the garment's lower side (mirrors when the fish swims leftward)."""
import math
import numpy as np
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely import affinity

# outline in units of L (x: snout 0 -> tail tip 1, y down = belly)
TOP = [(0.0, 0.015), (0.045, -0.055), (0.15, -0.11), (0.33, -0.128), (0.55, -0.095), (0.745, -0.04)]
BOT = [(0.745, 0.036), (0.56, 0.085), (0.37, 0.118), (0.19, 0.104), (0.065, 0.066), (0.0, 0.015)]
TAIL = [(0.725, -0.042), (0.86, -0.095), (1.0, -0.142), (0.935, -0.062), (0.885, -0.004), (0.935, 0.052), (1.0, 0.122),
        (0.86, 0.084), (0.725, 0.04)]
DORSAL = [(0.40, -0.124), (0.565, -0.198), (0.53, -0.106)]
PECT = [(0.20, 0.045), (0.385, 0.138), (0.30, 0.066)]
PELV = [(0.40, 0.114), (0.50, 0.175), (0.465, 0.108)]
ANAL = [(0.58, 0.082), (0.715, 0.122), (0.70, 0.05)]
CYAN = [(0.105, -0.072), (0.20, -0.098), (0.42, -0.104), (0.64, -0.068), (0.64, -0.046), (0.42, -0.073), (0.20, -0.064), (0.12, -0.05)]
RED = [(0.37, -0.012), (0.55, -0.046), (0.755, -0.04), (0.755, 0.03), (0.56, 0.018), (0.40, 0.006)]
GILL = [(0.165, -0.112), (0.205, 0.105)]           # head / body facet edge
LOWER = [(0.165, 0.035), (0.40, 0.035), (0.60, 0.03), (0.76, 0.04), (0.76, 0.2), (0.165, 0.2)]   # lower flank shadow facet
BELLY = [(0.22, 0.088), (0.36, 0.098), (0.52, 0.074), (0.52, 0.2), (0.22, 0.2)]                  # light belly strip
DORS_F = [(0.0, -0.3), (0.0, -0.035), (0.16, -0.07), (0.42, -0.088), (0.66, -0.056), (0.8, -0.04), (0.8, -0.3)]  # dorsal ridge facet (above the cyan line)
JAW = [(0.0, 0.02), (0.06, 0.012), (0.19, 0.03), (0.21, 0.2), (0.0, 0.2)]                         # lower head / jaw shadow
EYE = (0.088, -0.018)

def _P(pts, L): return Polygon([(x * L, y * L) for x, y in pts]).buffer(0)

def fish(x, y, L, ang, unit=None, mirror=None):
    """fish centred at (x, y) (mid point snout -> tail tip), head toward ang (deg, y down), length L mm"""
    ca = math.cos(math.radians(ang))
    if mirror is None: mirror = ca < 0                       # swimming leftward: flip so the belly stays down
    body = _P(TOP + BOT, L); tail = _P(TAIL, L).difference(body.buffer(0.1)).buffer(0)
    cyan = _P(CYAN, L).intersection(body.buffer(-0.35)).buffer(0)
    red = _P(RED, L).intersection(body.buffer(-0.3)).buffer(0)
    head = body.intersection(Polygon([(-1, -L), (GILL[0][0] * L, -L), (GILL[0][0] * L, GILL[0][1] * L), (GILL[1][0] * L, GILL[1][1] * L), (GILL[1][0] * L, L), (-1, L)])).buffer(0)
    lower = body.intersection(_P(LOWER, L)).difference(head).buffer(0)
    jaw = head.intersection(_P(JAW, L)).buffer(0)
    belly = body.intersection(_P(BELLY, L)).buffer(0)
    dors = body.intersection(_P(DORS_F, L)).buffer(0)
    lit = body.difference(unary_union([lower, head, dors])).buffer(0)
    head_lit = head.difference(jaw).buffer(0)
    eye_c = (EYE[0] * L, EYE[1] * L)
    er = max(0.82, 0.018 * L); eye = Point(eye_c).buffer(er); ring = Point(eye_c).buffer(er + 0.85)      # ring ≥ 0.85 wide (clean_vis min width 0.7)
    rp = lambda pts: (pts[0][0] * L, pts[0][1] * L)
    fins = [(_P(f, L), rp(f)) for f in (DORSAL, PECT, PELV, ANAL)]
    regs = []
    # sew order (sub): tail + outer fins -> body facets -> lines -> pectoral fin -> eye ring -> eye
    pedc = (0.73 * L, 0.0)
    up_l = tail.intersection(Polygon([(0, -L), (2 * L, -L), (2 * L, -0.004 * L), (0, -0.004 * L)])).buffer(0)
    regs.append(dict(col="kb_white", geom=up_l, st="satin", ang=("radial",) + pedc, grp="FI-tail", sub=1))
    regs.append(dict(col="kb_cream", geom=tail.difference(up_l).buffer(0), st="satin", ang=("radial",) + pedc, grp="FI-tail", sub=1))
    for (g, root), nm in zip(fins, ("dorsal", "pect", "pelv", "anal")):
        if nm == "pect": continue
        regs.append(dict(col="kb_ice", geom=g.difference(body.buffer(0.15)).buffer(0), st="satin", ang=("radial",) + root, grp="FI-fin", sub=1))
    regs.append(dict(col="kb_white", geom=lit, st="tatami", ang=25.0, grp="FI", sub=3, rel=True))
    regs.append(dict(col="kb_ice", geom=dors, st="satin", ang="auto", grp="FI-dorsal", sub=3))
    regs.append(dict(col="kb_white", geom=head_lit, st="tatami", ang=60.0, grp="FI", sub=3, rel=True))
    regs.append(dict(col="kb_cream", geom=unary_union([lower.difference(belly), jaw]).buffer(0), st="tatami", ang=-20.0, grp="FI-shade", sub=3.5, rel=True))
    regs.append(dict(col="kb_white", geom=belly.difference(head).buffer(0), st="satin", ang="auto", grp="FI-belly", sub=3.6))
    regs.append(dict(col="kb_cyan", geom=cyan, st="satin", ang="auto", grp="FI-line", sub=4))
    regs.append(dict(col="kb_red", geom=red, st="satin", ang="auto", grp="FI-red", sub=4))
    pg, proot = fins[1]
    regs.append(dict(col="kb_ice", geom=pg.difference(red.buffer(0.2)).buffer(0), st="satin", ang=("radial",) + proot, grp="FI-fin", sub=4.5))
    regs.append(dict(col="kb_white", geom=ring.intersection(body).buffer(0), st="satin", ang="auto", grp="FI-ring", sub=5))
    regs.append(dict(col="kb_ink", geom=eye, st="satin", ang="auto", grp="FI-eye", sub=6))
    # place: centre the fish at its midpoint, head (x = 0) toward ang
    out = []
    for r in regs:
        if r["geom"].is_empty: continue
        g = affinity.translate(r["geom"], -L / 2, 0)
        g = affinity.scale(g, -1, 1, origin=(0, 0))          # snout now at +L/2 (head along +x)
        if mirror: g = affinity.scale(g, 1, -1, origin=(0, 0))
        g = affinity.translate(affinity.rotate(g, ang, origin=(0, 0)), x, y).buffer(0)
        a = r["ang"]
        if isinstance(a, tuple):
            px, py = -(a[1] - L / 2), a[2] * (-1 if mirror else 1)
            q = affinity.translate(affinity.rotate(Point(px, py), ang, origin=(0, 0)), x, y); a = ("radial", q.x, q.y)
        elif r.get("rel"):
            a = ang + (-a if mirror else a)
        out.append(dict({k: v for k, v in r.items() if k != "rel"}, geom=g, ang=a, unit=unit))
    sil = unary_union([r["geom"] for r in out]).buffer(0.3)
    return out, sil
