"""Embroidery placement per size on the pattern + keep-out clearances (LESSONS A3, C4, C8).
The per-size art (art_<size>.pkl) is already in that size's pattern coordinates, so placement = the art itself.
usage: python3 emb_place.py   -> table + place_check.json"""
import rbcore
import os, pickle, json
from shapely.ops import unary_union
import front as F

_C = {}
def outline(size, P):
    key = (size, P)
    if key not in _C:
        D = pickle.load(open(f"art_{size}.pkl", "rb"))
        _C[key] = unary_union([r["geom"] for r in D[P]]).buffer(0)
    return _C[key]

def place(size):
    g, mt = F.pieces(size)
    return {P: (rbcore.PIECE_CODE[P], outline(size, P)) for P in rbcore.PIECES}, g, mt

def clearances(size):
    return {P: F.piece_clear(outline(size, P), size, P) for P in rbcore.PIECES}

if __name__ == "__main__":
    out = {}; allok = True
    for sz in rbcore.SIZES:
        c = clearances(sz); row = {}
        for P, d in c.items():
            mn = F.piece_min(P)
            bad = {k: round(v, 2) for k, v in d.items() if v < mn[k] - 0.05}
            row[P] = dict(clear={k: round(v, 1) for k, v in d.items()}, fail=bad); allok &= not bad
        out[sz] = row
        print(sz, {P: (min(row[P]["clear"].items(), key=lambda kv: kv[1] - F.piece_min(P)[kv[0]]), "FAIL " + str(row[P]["fail"]) if row[P]["fail"] else "ok") for P in row})
    json.dump(dict(sizes=out, all_pass=allok), open("place_check.json", "w"), indent=1)
    print("ALL PASS" if allok else "FAILURES")
