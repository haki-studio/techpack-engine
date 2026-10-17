"""Keep-outs per size and piece, measured on that size's drafted pattern piece (LESSONS A3, C8).
Coords = the pattern piece's own coords (back: x from CB, + = wearer's right; fronts: x from CF, + = wearer's left;
sleeves: x across the sleeve from the centre line, + = front half on S01, y down from the underarm line, cap top at -h).

Keep-outs (mm from the sew line):
  CF / zip 15 · side seams 15 · shoulder 15 · hem-rib seam 10 · welt box 6 · collar lying flat 6 ·
  armhole / sleeve cap 3 = WRAP seam (LESSONS A4: the mockup art runs across the armhole; art stops 3 mm short on both
  sides, armhole sewn without topstitch) · sleeve underarm seams 15 · cuff seam 10.  [armhole wrap rule PROPOSED]"""
import cfcore
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union
import numpy as np
import pattern as PT, drum
import front as F

K = {"CF / zip": 15.0, "side": 15.0, "shoulder": 15.0, "hem": 10.0, "welt": 6.0, "collar": 6.0, "armhole": 3.0,
     "cap": 3.0, "underarm": 15.0, "cuff": 10.0, "neck": 6.0}
COLLAR_FALL = 70.0           # collar lying flat on the back: 70 below the back neck seam at CB (collar 100 high, ~30 stand) [PROPOSED]

_PC = {}
def pieces(size):
    if size not in _PC: _PC[size] = PT.draft(size)
    return _PC[size]

def edge(pc, name): return LineString(next(e.pts for e in pc.edges if e.name == name))

def back_collar(size):
    g, mt = pieces(size); neck = next(e.pts for e in g["B01"].edges if e.name == "neck")
    lo = [(x, y + COLLAR_FALL * (1 - 0.25 * (abs(x) / max(1, mt["hps_b"][0])) ** 2)) for x, y in neck]
    return Polygon(list(neck) + lo[::-1]).buffer(0)

def lines(size, P):
    """named keep-out references {name: (geometry, min mm)} for piece P of one size"""
    g, mt = pieces(size)
    if P == "BK":
        pc = g["B01"]
        return {"side L": (edge(pc, "side L"), K["side"]), "side R": (edge(pc, "side R"), K["side"]),
                "armhole L": (edge(pc, "armhole L"), K["armhole"]), "armhole R": (edge(pc, "armhole R"), K["armhole"]),
                "shoulder L": (edge(pc, "shoulder L"), K["shoulder"]), "shoulder R": (edge(pc, "shoulder R"), K["shoulder"]),
                "hem": (edge(pc, "hem"), K["hem"]), "collar": (back_collar(size), K["collar"])}
    if P in ("FR", "FL"):
        pc = g["F02" if P == "FR" else "F01"]
        return {"CF / zip": (edge(pc, "CF / zip"), K["CF / zip"]), "side": (edge(pc, "side"), K["side"]),
                "armhole": (edge(pc, "armhole"), K["armhole"]), "shoulder": (edge(pc, "shoulder"), K["shoulder"]),
                "hem": (edge(pc, "hem"), K["hem"]), "welt": (Polygon(pc.internal[0][1]).buffer(0), K["welt"]),
                "collar": (F.COLLAR_R if P == "FR" else F.COLLAR_L, K["collar"]), "neck": (edge(pc, "neck"), K["neck"])}
    pc = g["S01" if P == "SR" else "S02"]
    return {"cap": (edge(pc, "cap"), K["cap"]), "underarm front": (edge(pc, "underarm front"), K["underarm"]),
            "underarm back": (edge(pc, "underarm back"), K["underarm"]), "cuff": (edge(pc, "cuff"), K["cuff"])}

def panel(size, P):
    g, mt = pieces(size)
    return g[cfcore.PIECE_CODE[P]].sew_poly()

_CL = {}
def clip(size, P):
    """area the art may occupy on piece P of this size (all keep-outs removed)"""
    if (size, P) not in _CL:
        a = panel(size, P)
        for nm, (geo, d) in lines(size, P).items():
            a = a.difference(geo.buffer(d))
        if a.geom_type != "Polygon":
            a = max(getattr(a, "geoms", [a]), key=lambda q: q.area)
        _CL[(size, P)] = a.buffer(0)
    return _CL[(size, P)]

def clearances(geom, size, P):
    return {nm: geom.distance(geo) for nm, (geo, d) in lines(size, P).items()}

def minimums(size, P): return {nm: d for nm, (geo, d) in lines(size, P).items()}
