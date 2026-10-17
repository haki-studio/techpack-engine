"""Embroidery placement per size on the pattern + keep-out clearances (read by pattern_out via pattern_wave.py).
The per-size art (art_<size>.pkl, waveart.py) is already in that size's pattern-piece coordinates: placement = the art."""
import wavecore as WC
import os, pickle
from shapely.ops import unary_union
import pieces as PC

_C = {}
def outline(size, P):
    key = (size, P)
    if key not in _C:
        D = pickle.load(open(f"art_{size}.pkl", "rb"))
        _C[key] = unary_union([r["geom"].buffer(0.3) for r in D[P]]).buffer(-0.3).simplify(0.15)
    return _C[key]

def place(size, OL=None):
    g, mt = PC.draft(size)
    return {P: (PC.CODE[P], outline(size, P)) for P in PC.PIECES}, g, mt

def clearances(size, OL=None):
    return {P: PC.clearances(outline(size, P), size, P) for P in PC.PIECES}

MIN = PC.MIN

if __name__ == "__main__":
    allok = True
    for sz in WC.SIZES:
        c = clearances(sz)
        bad = {P: {k: round(v, 1) for k, v in d.items() if v < MIN[P][k] - 0.3} for P, d in c.items()}
        allok &= not any(bad.values())
        print(sz, {P: {k: round(v, 1) for k, v in d.items()} for P, d in c.items()}, "FAIL" if any(bad.values()) else "all pass", bad if any(bad.values()) else "")
    print("ALL SIZES PASS" if allok else "KEEP-OUT FAILURES")
