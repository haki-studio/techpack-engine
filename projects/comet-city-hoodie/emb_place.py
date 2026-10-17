"""Embroidery placement per size on the pattern + keep-out clearances (read by pattern_out via pattern_cc.py).
The per-size art (art_<size>.pkl) is already in that size's pattern coordinates, so placement = the art itself."""
import cccore
import os, pickle
from shapely.ops import unary_union
import front as F

_C = {}
def outline(size, P):
    key = (size, P)
    if key not in _C:
        D = pickle.load(open(f"art_{size}.pkl", "rb"))
        _C[key] = unary_union([r["geom"].buffer(0.3) for r in D[P]]).buffer(-0.3).simplify(0.15)
    return _C[key]

def place(size, OL=None):
    g, mt = F.pieces(size)
    return {P: (cccore.PIECE_CODE[P], outline(size, P)) for P in cccore.PIECES}, g, mt

def clearances(size, OL=None):
    out = {P: F.clearances(outline(size, P), size, "R" if P == "FR" else "L") for P in cccore.FRONTS}
    out.update({P: F.sleeve_clearances(outline(size, P), size, "R" if P == "SR" else "L") for P in cccore.SLEEVES})
    return out

def mins(P): return F.MIN if P in cccore.FRONTS else F.SMIN
MIN = F.MIN

if __name__ == "__main__":
    allok = True
    for sz in cccore.SIZES:
        c = clearances(sz)
        bad = {P: {k: round(v, 1) for k, v in d.items() if v < mins(P)[k] - 0.3} for P, d in c.items()}
        allok &= not any(bad.values())
        print(sz, {P: {k: round(v, 1) for k, v in d.items()} for P, d in c.items()}, "FAIL" if any(bad.values()) else "all pass", bad if any(bad.values()) else "")
    print("ALL SIZES PASS" if allok else "KEEP-OUT FAILURES")
