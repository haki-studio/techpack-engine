"""Embroidery placement per size on the pattern + keep-out clearances (LESSONS A3, C8). The per-size art (art_<size>.pkl)
is already in that size's pattern coordinates, so placement = the art itself. usage: python3 emb_place.py"""
import kccore
import pickle
from shapely.ops import unary_union
import front as F, sleeve as SV

_C = {}
def outline(size, P):
    key = (size, P)
    if key not in _C:
        D = pickle.load(open(f"art_{size}.pkl", "rb"))
        _C[key] = unary_union([r["geom"] for r in D[P]])
    return _C[key]

def place(size, OL=None):
    g, mt = F.pieces(size)
    return {P: (kccore.PIECE_CODE[P], outline(size, P)) for P in kccore.PIECES}, g, mt

def clearances(size, OL=None):
    out = {}
    for P in kccore.PIECES:
        if P in ("FR", "FL"): out[P] = F.clearances(outline(size, P), size, "R" if P == "FR" else "L")
        else: out[P] = SV.clearances(outline(size, P), size, P)
    return out

def mins(P): return F.MIN if P in ("FR", "FL") else SV.MIN

def worst():
    """[(label, min distance over all sizes, required, ok)] per keep-out kind"""
    agg = {}
    for sz in kccore.SIZES:
        for P, d in clearances(sz).items():
            for k, v in d.items():
                lab = f"{'fronts' if P in ('FR', 'FL') else 'sleeves'}: {k}"
                if lab not in agg or v < agg[lab][0]: agg[lab] = (v, mins(P)[k])
    return [(k, v, m, v >= m - 0.5) for k, (v, m) in agg.items()]

if __name__ == "__main__":
    for sz in kccore.SIZES:
        c = clearances(sz)
        bad = {P: {k: round(v, 1) for k, v in d.items() if v < mins(P)[k] - 0.5} for P, d in c.items()}
        print(sz, {P: {k: round(v, 1) for k, v in d.items()} for P, d in c.items()}, "FAIL" if any(bad.values()) else "all pass", bad if any(bad.values()) else "")
