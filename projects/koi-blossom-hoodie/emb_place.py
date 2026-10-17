"""Embroidery placement per size on the pattern + keep-out clearances. The per-size art (art_<size>.pkl) is already in
that size's pattern coordinates (fronts: garment coords = F01/F02 coords; sleeves: S01/S02 coords), so placement = the art."""
import kbcore
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
    return {P: (F.CODE[P], outline(size, P)) for P in kbcore.PIECES}, g, mt

def clearances(size, OL=None):
    return {P: F.clearances(outline(size, P), size, P) for P in kbcore.PIECES}

def MIN(P): return F.MIN(P)

if __name__ == "__main__":
    allok = True
    for sz in kbcore.SIZES:
        c = clearances(sz)
        bad = {P: {k: round(v, 1) for k, v in d.items() if v < F.MIN(P)[k] - 0.3} for P, d in c.items()}
        allok &= not any(bad.values())
        print(sz, {P: {k: round(v, 1) for k, v in d.items()} for P, d in c.items()}, "FAIL" if any(bad.values()) else "all pass", bad if any(bad.values()) else "")
    print("KEEP-OUTS:", "all pass" if allok else "FAIL")
