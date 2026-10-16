"""Embroidery placement on the pattern, per size (art grade A/B/C), + clearance QA."""
import os, pickle, math, json
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity
import pattern as PT, drum

GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
SCALE = {"A": 0.92, "B": 1.0, "C": 1.08}
OVERRIDE = {("XXL", "04"): "B", ("3XL", "04"): "B"}   # 04 sits between the welt and the hem: stays at 100% on the largest sizes          # (size, elem) -> grade letter, filled below if an element can't hold its keep-outs at its size's grade
def grade_of(size, elem): return OVERRIDE.get((size, elem), GRADE[size][0])
ELEMS = ["back", "sleeve", "02R", "02L", "03", "04"]

def outlines():
    cp = "emb_outlines.pkl"
    if os.path.exists(cp): return pickle.load(open(cp, "rb"))
    out = {}
    for k in ELEMS:
        vis = pickle.load(open(f"clean_{k}.pkl", "rb"))
        u = unary_union([r["geom"].buffer(0.3) for r in vis]).buffer(-0.3).simplify(0.6)
        out[k] = u
    pickle.dump(out, open(cp, "wb")); return out

_M = None
def m_ref():
    global _M
    if _M is None: _M = PT.draft("M")
    return _M

_SZ = {}
def size_art(size):
    """per-size 01 back + sleeve outlines from back_<size>.pkl (built by back_size.py), or None"""
    if size in _SZ: return _SZ[size]
    p = f"back_{size}.pkl"
    if not os.path.exists(p): return None
    D = pickle.load(open(p, "rb"))
    ub = unary_union([r["geom"].buffer(0.3) for r in D["back"]]).buffer(-0.3).simplify(0.6)
    us = unary_union([r["geom"].buffer(0.3) for r in D["sleeve"]]).buffer(-0.3).simplify(0.6)
    _SZ[size] = (ub, us, D["info"]); return _SZ[size]

def place(size, OL=None):
    """returns {elem: geometry in that piece's pattern coords}, plus the pieces + meta for the size."""
    OL = OL or outlines(); g, mt = PT.draft(size); gM, mM = m_ref()
    res = {}
    def S(geom, elem):
        sc_ = SCALE[grade_of(size, elem)]; c = geom.envelope.centroid; return affinity.scale(geom, sc_, sc_, origin=(c.x, c.y))
    # 01 back: centre x keeps its CB offset × scale; bottom stays 10 above the hem-rib seam
    sc = SCALE[grade_of(size, "back")]
    a = OL["back"]; bM = a.bounds; s_ = S(a, "back"); bs = s_.bounds
    tx = ((bM[0] + bM[2]) / 2) * sc - (bs[0] + bs[2]) / 2; ty = (mt["hem_b"] - (mM["hem_b"] - bM[3])) - bs[3]
    res["back"] = ("B01", affinity.translate(s_, tx, ty))
    # 02R / 02L: zip edge 15 from CF; top below neck seam × scale
    for k, side in (("02R", -1), ("02L", 1)):
        sc = SCALE[grade_of(size, k)]
        a = OL[k]; bM = a.bounds; s_ = S(a, k); bs = s_.bounds
        tx = (-15 - bs[2]) if side < 0 else (15 - bs[0]); ty = bM[1] * sc - bs[1]
        res[k] = ("F02" if side < 0 else "F01", affinity.translate(s_, tx, ty))
    # 03: offset from the wearer's-left welt centre × scale
    sc = SCALE[grade_of(size, "03")]
    a = OL["03"]; c = a.envelope.centroid; wM = mM["welt_c"]; w = mt["welt_c"]
    s_ = S(a, "03"); cs = s_.envelope.centroid
    res["03"] = ("F01", affinity.translate(s_, w[0] + (c.x - wM[0]) * sc - cs.x, w[1] + (c.y - wM[1]) * sc - cs.y))
    # 04: wearer's right, bottom fixed above the hem seam, x centre × scale
    sc = SCALE[grade_of(size, "04")]
    a = OL["04"]; bM = a.bounds; s_ = S(a, "04"); bs = s_.bounds
    tx = ((bM[0] + bM[2]) / 2) * sc - (bs[0] + bs[2]) / 2; ty = (mt["hem_f"] - (mM["hem_f"] - bM[3])) - bs[3]
    res["04"] = ("F02", affinity.translate(s_, tx, ty))
    # ---- per-size nudge: smallest move that restores every keep-out (the art never resizes beyond its grade)
    def need(k, geom):
        pc = res[k][0] if k in res else None
        e = lambda nm: LineString(next(x.pts for x in g[pc].edges if x.name == nm))
        wl = lambda: Polygon(g[pc].internal[0][1])
        if k == "back": return [(e("side L"), 15), (e("armhole R"), 3), (e("hem"), 9.5), (e("shoulder R"), 6)], [(e("armhole R"), 6)]
        if k in ("02R", "02L"): return [(e("CF / zip"), 14.9), (e("armhole"), 15), (e("shoulder"), 15), (wl(), 6)], []
        if k == "03": return [(wl(), 6), (e("side"), 15), (e("CF / zip"), 15)], []
        if k == "04": return [(wl(), 6), (e("side"), 15), (e("CF / zip"), 15), (e("hem"), 9.5)], []
    NUDGE = {}
    for k in ("back", "02R", "02L", "03", "04"):
        pc, a = res[k]; mins, maxs = need(k, a)
        def ok(dx, dy):
            b_ = affinity.translate(a, dx, dy)
            return all(b_.distance(L_) >= v for L_, v in mins) and all(b_.distance(L_) <= v for L_, v in maxs)
        if ok(0, 0): NUDGE[k] = (0.0, 0.0); continue
        best = None
        for r in np.arange(0.5, 45.5, 0.5):
            for th in np.linspace(0, 2*math.pi, 48, endpoint=False):
                dx, dy = r*math.cos(th), r*math.sin(th)
                if k in ("02R", "02L"): dx = 0.0          # zip edge stays 15 from CF
                if ok(dx, dy): best = (dx, dy); break
            if best: break
        if best is None and maxs:                         # can't hold the wrap gap: drop the max rule
            for r in np.arange(0.5, 30.5, 0.5):
                for th in np.linspace(0, 2*math.pi, 32, endpoint=False):
                    dx, dy = r*math.cos(th), r*math.sin(th)
                    b_ = affinity.translate(a, dx, dy)
                    if all(b_.distance(L_) >= v for L_, v in mins): best = (dx, dy); break
                if best: break
        best = best or (0.0, 0.0); NUDGE[k] = best
        res[k] = (pc, affinity.translate(a, *best))
    res["_nudge"] = NUDGE
    SA_ = size_art(size)
    if SA_ is not None:
        res["back"] = ("B01", SA_[0]); NUDGE["back"] = ("per-size art", SA_[2]["dx"], SA_[2]["dy"])
    # sleeve wrap: seam coords (s from the old shoulder point, d into the sleeve) -> right sleeve cap
    sc = SCALE[grade_of(size, "sleeve")]
    cap = g["S01"].edges[0].pts; k = mt["cap"] / mt["AH"]; st = mt["cap_top"]; sp = g["S01"].sew_poly()
    # wrap check: each limb crossing found on the M sleeve art (wrap_marks.json, arc mm from the old shoulder point) must meet
    # back art within 6 mm of the armhole at the scaled position (±6 mm). Sleeve art is placed by the same scaled marks.
    armR = next(e.pts for e in g["B01"].edges if e.name == "armhole R")[::-1]       # shoulder seam -> underarm
    ab = res["back"][1]; marks = json.load(open("wrap_marks.json")); hits = []
    if SA_ is not None: marks = [tuple(m_) for m_ in SA_[2]["marks"]]
    for a0, a1 in marks:
        c_ = (a0 + a1) / 2 if SA_ is not None else (a0 + a1) / 2 * sc + PT.FWD
        hits.append(any(ab.distance(Point(PT.at(armR, c_ + d)[0])) < 6.0 for d in np.arange(-6, 6.5, 1.0)))
    res["_wrap"] = dict(aligned=sum(hits), total=len(hits))
    shift = 0.0
    def to_sleeve(x, y):
        pos = st - (x * sc + PT.FWD + shift) * k
        p, tg = PT.at(cap, max(0.0, pos)); n = (-tg[1], tg[0])
        if not sp.contains(Point(p[0] + n[0]*2, p[1] + n[1]*2)): n = (-n[0], -n[1])
        return (p[0] + n[0] * y * sc, p[1] + n[1] * y * sc)
    if SA_ is not None:       # per-size sleeve art is already in this size's seam coords (s from the shoulder seam)
        a = SA_[1]
        def to_sleeve(x, y):
            p, tg = PT.at(cap, max(0.0, st - x * k)); n = (-tg[1], tg[0])
            if not sp.contains(Point(p[0] + n[0]*2, p[1] + n[1]*2)): n = (-n[0], -n[1])
            return (p[0] + n[0] * y, p[1] + n[1] * y)
    else:
        a = OL["sleeve"]
    polys = [a] if a.geom_type == "Polygon" else list(a.geoms)
    mapped = [Polygon([to_sleeve(x, y) for x, y in PT.resample(list(p.exterior.coords), 1.5)]).buffer(0) for p in polys if p.area > 1]
    res["sleeve"] = ("S01", unary_union(mapped))
    return res, g, mt

def clearances(size, OL=None):
    res, g, mt = place(size, OL); out = {"nudge": res["_nudge"], "wrap": res["_wrap"]}
    def edge(pc, name): return LineString(next(e.pts for e in g[pc].edges if e.name == name))
    def welt(pc): return Polygon(g[pc].internal[0][1])
    _, a = res["back"]
    out["01"] = dict(side_L=a.distance(edge("B01", "side L")), armhole_R=a.distance(edge("B01", "armhole R")),
                     hem=a.distance(edge("B01", "hem")), neck=a.distance(edge("B01", "neck")), shoulder_R=a.distance(edge("B01", "shoulder R")))
    for k, pc in (("02R", "F02"), ("02L", "F01")):
        _, a = res[k]
        out[k] = dict(CF=a.distance(edge(pc, "CF / zip")), armhole=a.distance(edge(pc, "armhole")), shoulder=a.distance(edge(pc, "shoulder")),
                      welt=a.distance(welt(pc)), neck=a.distance(edge(pc, "neck")))
    _, a = res["03"]; out["03"] = dict(welt=a.distance(welt("F01")), side=a.distance(edge("F01", "side")), CF=a.distance(edge("F01", "CF / zip")), hem=a.distance(edge("F01", "hem")))
    _, a = res["04"]; out["04"] = dict(welt=a.distance(welt("F02")), side=a.distance(edge("F02", "side")), CF=a.distance(edge("F02", "CF / zip")), hem=a.distance(edge("F02", "hem")))
    _, a = res["sleeve"]; out["sleeve"] = dict(cap=a.distance(LineString(g["S01"].edges[0].pts)), inside=float(g["S01"].sew_poly().contains(a)))
    return out

MIN = {"01": dict(side_L=15, armhole_R=3, hem=10, neck=6, shoulder_R=6), "02R": dict(CF=15, armhole=15, shoulder=15, welt=6, neck=6),
       "02L": dict(CF=15, armhole=15, shoulder=15, welt=6, neck=6), "03": dict(welt=6, side=15, CF=15, hem=10),
       "04": dict(welt=6, side=15, CF=15, hem=10), "sleeve": dict(cap=3)}

if __name__ == "__main__":
    OL = outlines()
    for sz in drum.SIZES:
        c = clearances(sz, OL)
        nd = c.pop("nudge"); wr = c.pop("wrap"); print(sz, "wrap", wr)
        bad = {e: {k: round(v, 1) for k, v in d.items() if k in MIN.get(e, {}) and v < MIN[e][k] - 0.6} for e, d in c.items()}
        print(sz, "nudge", {k: tuple(round(v, 1) for v in d) for k, d in nd.items() if any(d)}, {e: {k: round(v, 1) for k, v in d.items()} for e, d in c.items()})
        print("   FAIL:", {e: v for e, v in bad.items() if v})
