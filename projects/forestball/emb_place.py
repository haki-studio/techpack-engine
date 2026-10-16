"""Embroidery placement on the Drum Island pattern, per size (art grade A/B/C) + clearance QA (LESSONS A3, C4, C5).
Elements: back (01, on B01), 02R (wearer's right front, F02), 02L (wearer's left front, F01). Nothing wraps."""
import os, pickle, math
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity
import fbcore
import pattern as PT, drum

GRADE = {"XS": ("A", 0.90), "S": ("A", 0.90), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
SCALE = {"A": 0.90, "B": 1.0, "C": 1.08}
OVERRIDE = {}            # (size, elem) -> grade letter, if an element can't hold its keep-outs at its size's grade
def grade_of(size, elem): return OVERRIDE.get((size, elem), GRADE[size][0])
ELEMS = ["back", "02R", "02L"]
PIECE = {"back": "B01", "02R": "F02", "02L": "F01"}
COLLAR_FALL = 45.0       # PROPOSED (back.py)

def outlines():
    cp = "emb_outlines.pkl"
    srcs = ["back_vis.pkl", "front_vis.pkl"]
    if os.path.exists(cp) and all(os.path.getmtime(cp) > os.path.getmtime(s) for s in srcs): return pickle.load(open(cp, "rb"))
    D = pickle.load(open("back_vis.pkl", "rb")); F = pickle.load(open("front_vis.pkl", "rb"))
    out = {}
    for k, vis in (("back", D["back"]), ("02R", F["02R"]), ("02L", F["02L"])):
        out[k] = unary_union([r["geom"].buffer(0.3) for r in vis if r["grp"] != "PH"]).buffer(-0.3).simplify(0.1)
        if k in ("02R", "02L"):     # main-limb bark at the zip, for the per-size zip match marks
            out["_bark_" + k] = unary_union([r["geom"] for r in vis if r["grp"].split("-")[0] == "TR"]).buffer(0.2).buffer(-0.2)
    import back as B
    out["_ph"] = B.PH_BOX
    pickle.dump(out, open(cp, "wb")); return out

_M = None
def m_ref():
    global _M
    if _M is None: _M = PT.draft("M")
    return _M

def collar_zone_back(g):
    neck = next(e.pts for e in g["B01"].edges if e.name == "neck")
    n2 = max(abs(x) for x, y in neck)
    return Polygon(list(neck) + [(x, y + COLLAR_FALL * (1 - 0.35 * abs(x) / n2)) for x, y in neck[::-1]]).buffer(0)

def need(k, g):
    pc = PIECE[k]
    e = lambda nm: LineString(next(x.pts for x in g[pc].edges if x.name == nm))
    if k == "back":
        return [(e("side L"), 15), (e("side R"), 15), (e("armhole L"), 15), (e("armhole R"), 15), (e("shoulder L"), 15),
                (e("shoulder R"), 15), (e("hem"), 9.5), (collar_zone_back(g), 6)]
    wl = Polygon(g[pc].internal[0][1])
    return [(e("CF / zip"), 15.0), (e("armhole"), 15), (e("shoulder"), 15), (e("side"), 15), (wl, 6), (e("hem"), 10)]

def place(size, OL=None):
    """{elem: (piece code, geometry in pattern coords)}, '_tf': {elem: (scale, origin, dx, dy)}, '_ph': placeholder box."""
    OL = OL or outlines(); g, mt = PT.draft(size); gM, mM = m_ref()
    res = {}; TF = {}
    for k in ELEMS:
        sc = SCALE[grade_of(size, k)]; a = OL[k]; bM = a.bounds; c = ((bM[0]+bM[2])/2, (bM[1]+bM[3])/2)
        s_ = affinity.scale(a, sc, sc, origin=c); bs = s_.bounds
        if k == "back":       # x centre keeps its CB offset × scale; bottom keeps its distance above the hem seam
            dx = c[0] * sc - c[0]; dy = (mt["hem_b"] - (mM["hem_b"] - bM[3])) - bs[3]
        else:                 # zip edge 15 from CF; top = M distance below the neck seam × scale
            side = -1 if k == "02R" else 1
            dx = (-15.3 - bs[2]) if side < 0 else (15.3 - bs[0]); dy = bM[1] * sc - bs[1]
        TF[k] = [sc, c, dx, dy]; res[k] = (PIECE[k], affinity.translate(s_, dx, dy))
    NUDGE = {}
    def ok_for(k, dx, dy):
        a = res[k][1]; return all(affinity.translate(a, dx, dy).distance(L_) >= v for L_, v in need(k, g))
    # back: free nudge
    if ok_for("back", 0, 0): NUDGE["back"] = (0.0, 0.0)
    else:
        best = None
        for r in np.arange(0.25, 40.25, 0.25):
            for th in np.linspace(0, 2*math.pi, 64, endpoint=False):
                if ok_for("back", r*math.cos(th), r*math.sin(th)): best = (r*math.cos(th), r*math.sin(th)); break
            if best: break
        NUDGE["back"] = best or (0.0, 0.0)
    # fronts: ONE vertical nudge for both pieces so the limb stays continuous across the zip (Rev B)
    dyf = 0.0
    if not (ok_for("02R", 0, 0) and ok_for("02L", 0, 0)):
        for d in sorted(np.arange(-30, 30.25, 0.25), key=abs):
            if ok_for("02R", 0, d) and ok_for("02L", 0, d): dyf = float(d); break
    NUDGE["02R"] = NUDGE["02L"] = (0.0, dyf)
    for k in ELEMS:
        if any(NUDGE[k]):
            res[k] = (res[k][0], affinity.translate(res[k][1], *NUDGE[k])); TF[k][2] += NUDGE[k][0]; TF[k][3] += NUDGE[k][1]
    sc, c, dx, dy = TF["back"]
    res["_ph"] = affinity.translate(affinity.scale(OL["_ph"], sc, sc, origin=c), dx, dy)
    res["_nudge"] = NUDGE; res["_tf"] = TF
    marks = {}
    for k, xx in (("02R", -15.0), ("02L", 15.0)):
        sc, c, dx, dy = TF[k]
        bk = affinity.translate(affinity.scale(OL["_bark_" + k], sc, sc, origin=c), dx, dy)
        seg = bk.intersection(LineString([(xx + (0.6 if xx > 0 else -0.6), -200), (xx + (0.6 if xx > 0 else -0.6), 900)]))
        ys = [q for gg in (getattr(seg, "geoms", None) or [seg]) if not gg.is_empty for q in [c_[1] for c_ in gg.coords]]
        marks[k] = (min(ys), max(ys)) if ys else None
    res["_zip"] = marks
    return res, g, mt

def clearances(size, OL=None):
    res, g, mt = place(size, OL); out = {"nudge": res["_nudge"]}
    def edge(pc, name): return LineString(next(e.pts for e in g[pc].edges if e.name == name))
    _, a = res["back"]
    out["01"] = dict(side_L=a.distance(edge("B01", "side L")), side_R=a.distance(edge("B01", "side R")),
                     armhole_L=a.distance(edge("B01", "armhole L")), armhole_R=a.distance(edge("B01", "armhole R")),
                     shoulder=min(a.distance(edge("B01", "shoulder L")), a.distance(edge("B01", "shoulder R"))),
                     hem=a.distance(edge("B01", "hem")), collar=a.distance(collar_zone_back(g)))
    for k, pc in (("02R", "F02"), ("02L", "F01")):
        _, a = res[k]
        out[k] = dict(CF=a.distance(edge(pc, "CF / zip")) + 0.0, armhole=a.distance(edge(pc, "armhole")), shoulder=a.distance(edge(pc, "shoulder")),
                      side=a.distance(edge(pc, "side")), welt=a.distance(Polygon(g[pc].internal[0][1])), hem=a.distance(edge(pc, "hem")))
    return out

MIN = {"01": dict(side_L=15, side_R=15, armhole_L=15, armhole_R=15, shoulder=15, hem=10, collar=6),
       "02R": dict(CF=15, armhole=15, shoulder=15, side=15, welt=6, hem=10),
       "02L": dict(CF=15, armhole=15, shoulder=15, side=15, welt=6, hem=10)}

def failures(c):          # exact: no tolerance below the documented minimum (Rev B, reviewer)
    return {e: {k: round(v, 2) for k, v in d.items() if k in MIN.get(e, {}) and v < MIN[e][k] - 1e-6} for e, d in c.items() if e in MIN}

def zip_check(size, OL=None):
    """main-limb band at x = ±15 per size: (centre, width) on 02R and 02L, centre step + width difference"""
    res, g, mt = place(size, OL); z = res["_zip"]
    if not z["02R"] or not z["02L"]: return None
    cR, wR = sum(z["02R"])/2, z["02R"][1] - z["02R"][0]; cL, wL = sum(z["02L"])/2, z["02L"][1] - z["02L"][0]
    return dict(R=z["02R"], L=z["02L"], cR=cR, cL=cL, wR=wR, wL=wL, step=abs(cR - cL), dw=abs(wR - wL))

if __name__ == "__main__":
    OL = outlines(); allok = True
    for sz in drum.SIZES:
        c = clearances(sz, OL); nd = c.pop("nudge"); bad = {e: v for e, v in failures(c).items() if v}
        allok &= not bad
        print(sz, GRADE[sz][0], "nudge", {k: tuple(round(v, 1) for v in d) for k, d in nd.items() if any(d)},
              {e: {k: round(v, 1) for k, v in d.items()} for e, d in c.items()}, "FAIL:" if bad else "ok", bad or "")
        z = zip_check(sz, OL); print("   zip", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in z.items()} if z else None)
        allok &= bool(z) and z["step"] <= 3.0 and z["dw"] <= 3.0
    print("ALL PASS" if allok else "FAILURES")
