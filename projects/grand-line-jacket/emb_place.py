"""Embroidery placement per size on the pattern + keep-out clearances (read by pattern_out via pattern_gl.py).
The per-size art (front_<size>.pkl) is already in that size's pattern coordinates, so placement = the art itself."""
import glcore
import os, pickle
from shapely.ops import unary_union
import front as F

_C = {}
def outline(size, P):
    key = (size, P)
    if key not in _C:
        D = pickle.load(open(f"front_{size}.pkl", "rb"))
        _C[key] = unary_union([r["geom"].buffer(0.3) for r in D[P]]).buffer(-0.3).simplify(0.15)
    return _C[key]

def place(size, OL=None):
    g, mt = F.pieces(size)
    return {"FR": ("F02", outline(size, "FR")), "FL": ("F01", outline(size, "FL"))}, g, mt

def clearances(size, OL=None):
    return {P: F.clearances(outline(size, P), size, "R" if P == "FR" else "L") for P in ("FR", "FL")}

MIN = F.MIN

if __name__ == "__main__":
    for sz in glcore.SIZES:
        c = clearances(sz)
        bad = {P: {k: round(v, 1) for k, v in d.items() if v < MIN[k] - 0.3} for P, d in c.items()}
        print(sz, {P: {k: round(v, 1) for k, v in d.items()} for P, d in c.items()}, "FAIL" if any(bad.values()) else "all pass", bad if any(bad.values()) else "")
