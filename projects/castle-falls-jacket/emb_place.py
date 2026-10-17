"""Embroidery placement per size on the pattern + keep-out clearances (read by pattern_out via pattern_cf.py).
The per-size art (art_<size>.pkl, built by art_size.py) is already in that size's pattern-piece coordinates, so the
placement IS the art outline. usage: python3 emb_place.py  -> clearance table for every size + piece."""
import cfcore
import os, pickle
from shapely.geometry import Polygon
from shapely.ops import unary_union
import keepout as KO

_C = {}
def outline(size, P):
    key = (size, P)
    if key not in _C:
        p = f"art_{size}.pkl"
        if not os.path.exists(p): return Polygon()
        D = pickle.load(open(p, "rb"))
        _C[key] = unary_union([r["geom"].buffer(0.3) for r in D[P]]).buffer(-0.3).simplify(0.2)
    return _C[key]

def place(size, OL=None):
    g, mt = KO.pieces(size)
    return {P: (cfcore.PIECE_CODE[P], outline(size, P)) for P in cfcore.PIECES}, g, mt

def clearances(size, OL=None):
    return {P: KO.clearances(outline(size, P), size, P) for P in cfcore.PIECES if not outline(size, P).is_empty}

def check(size):
    """{piece: {name: (measured, min, ok)}}"""
    out = {}
    for P, d in clearances(size).items():
        mn = KO.minimums(size, P)
        out[P] = {k: (round(v, 1), mn[k], v >= mn[k] - 0.3) for k, v in d.items()}
    return out

if __name__ == "__main__":
    allok = True
    for sz in cfcore.SIZES:
        if not os.path.exists(f"art_{sz}.pkl"): print(sz, "no art yet"); continue
        c = check(sz); bad = {P: {k: v for k, v in d.items() if not v[2]} for P, d in c.items()}
        bad = {P: v for P, v in bad.items() if v}; allok &= not bad
        print(sz, "FAIL" if bad else "all pass", bad if bad else "", {P: min(v[0] - v[1] for v in d.values()) for P, d in c.items()})
    print("ALL SIZES PASS" if allok else "FAILURES")
