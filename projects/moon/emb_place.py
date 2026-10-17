"""Moon jacket — embroidery placement on the pattern per size + keep-out clearance QA (LESSONS A3, C4, C5).
01 back + 03L/03R lower fronts are built per size directly on that size's pattern (art_<SIZE>.pkl).
02R/02L chest clouds and 04R/04L sleeve clouds are graded files (A/B/C), placed per size here, nudged by the
smallest move that restores every keep-out."""
import os, pickle, math, json
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity
import moonpattern, pattern as PT, drum
import front as FR
import scene

GRADE = {k: v for k, v in scene.GRADE.items()}
SCALE = scene.SCALE
OVERRIDE = {}
def grade_of(size, elem): return OVERRIDE.get((size, elem), GRADE[size][0])
PIECE = {"back": "B01", "box": "B01", "03L": "F01", "03R": "F02", "02L": "F01", "02R": "F02", "04R": "S01", "04L": "S02"}
NAME = {"back": "01 back scene", "box": "01 LICENSED FIGURE placeholder box (factory insert)", "03L": "03L pole + wires",
        "03R": "03R wires", "02L": "02L chest clouds", "02R": "02R chest clouds", "04R": "04R sleeve clouds", "04L": "04L sleeve clouds"}

class Outline:
    """art outline: exact distances from the regions themselves (STRtree-free vectorised shapely.distance), a rough
    union (0.3 mm close, 0.4 simplify) for drawing/bounds. A 1000-region exact union took minutes per size."""
    def __init__(self, geoms):
        import shapely
        self.g = np.array([g for g in geoms if not g.is_empty], dtype=object)
        self.rough = unary_union([g.simplify(0.2).buffer(0.3) for g in self.g]).buffer(-0.3).simplify(0.4) if len(self.g) else Polygon()
    def distance(self, other):
        import shapely
        return float(shapely.distance(self.g, other).min()) if len(self.g) else 1e9
    def __getattr__(self, k): return getattr(self.rough, k)

def outline(vis, lines=None):
    rs = [r for r in vis if (lines is None) or ((r["grp"] == "WR") == lines)]
    return Outline([r["geom"] for r in rs])

_G = None
def graded():
    global _G
    if _G is None: _G = pickle.load(open("art_graded.pkl", "rb"))
    return _G
_S = {}
def size_art(size):
    if size not in _S: _S[size] = pickle.load(open(f"art_{size}.pkl", "rb"))
    return _S[size]

def edge(g, pc, name): return LineString(next(e.pts for e in g[pc].edges if e.name == name))

def rules(g, k):
    """(min-distance rules, max rules) for element k on its piece."""
    pc = PIECE[k]; e = lambda n: edge(g, pc, n)
    if k in ("02R", "02L"):
        return [(e("CF / zip"), 15), (e("armhole"), 15), (e("shoulder"), 15), (e("side"), 15), (e("neck"), 6),
                (Polygon(g[pc].internal[0][1]), 6), ((FR.COLLAR_L if k == "02L" else FR.COLLAR_R), 6)]
    if k in ("04R", "04L"):
        return [(e("cap"), 15), (e("underarm front"), 15), (e("underarm back"), 15), (e("cuff"), 10)]
    return []

def place(size):
    g, mt = PT.draft(size); gM, mM = PT.draft("M"); res = {}; nudge = {}
    A = size_art(size)
    res["back"] = ("B01", outline(A["back"])); res["box"] = ("B01", box(*A["info"]["box"]))
    res["03L"] = ("F01", outline(A["F03L"])); res["03R"] = ("F02", outline(A["F03R"]))
    G = graded()
    for k in ("02R", "02L", "04R", "04L"):
        sc = SCALE[grade_of(size, k)]; a = outline(G[k]).rough; c = a.envelope.centroid
        s_ = affinity.scale(a, sc, sc, origin=(c.x, c.y)); bM = a.bounds; bs = s_.bounds
        if k in ("02R", "02L"):
            # inner edge keeps its M distance from CF; top keeps its M distance below the neck seam x scale
            tx = (bM[2] - bs[2]) if k == "02R" else (bM[0] - bs[0]); ty = bM[1] * sc - bs[1]
        else:
            kx = mt["W"] / mM["W"]; kl = (mt["cap_h"] + mt["Lu"]) / (mM["cap_h"] + mM["Lu"])
            tx = c.x * kx - c.x; ty = (-mt["cap_h"] + (c.y + mM["cap_h"]) * kl) - c.y
        geom = affinity.translate(s_, tx, ty)
        mins = rules(g, k)
        def ok(dx, dy): b_ = affinity.translate(geom, dx, dy); return all(b_.distance(L) >= v for L, v in mins)
        best = (0.0, 0.0)
        if not ok(0, 0):
            best = None
            for r in np.arange(0.5, 40.5, 0.5):
                for th in np.linspace(0, 2 * math.pi, 48, endpoint=False):
                    if ok(r * math.cos(th), r * math.sin(th)): best = (r * math.cos(th), r * math.sin(th)); break
                if best: break
            best = best or (0.0, 0.0)
        nudge[k] = best; res[k] = (PIECE[k], affinity.translate(geom, *best))
        res[k + "_tf"] = dict(scale=sc, dx=tx + best[0], dy=ty + best[1], centre=(c.x, c.y))
    res["_nudge"] = nudge
    return res, g, mt

MIN = {"01": dict(side_L=15, side_R=15, armhole_L=15, armhole_R=15, hem=10, neck=6, wire_side_L=3, wire_side_R=3),
       "03L": dict(side=15, wire_side=3, CF=15, hem=10, welt=6, wire_welt=6), "03R": dict(wire_side=3, CF=15, hem=10, welt=6, wire_welt=6),
       "02R": dict(CF=15, armhole=15, shoulder=15, side=15, welt=6, collar=6), "02L": dict(CF=15, armhole=15, shoulder=15, side=15, welt=6, collar=6),
       "04R": dict(cap=15, underarm=15, cuff=10), "04L": dict(cap=15, underarm=15, cuff=10)}
MAX = {"01": dict(wire_side_L=3.6, wire_side_R=3.6), "03L": dict(wire_side=3.6), "03R": dict(wire_side=3.6)}

def clearances(size):
    res, g, mt = place(size); A = size_art(size); out = {"nudge": res["_nudge"]}
    e = lambda pc, n: edge(g, pc, n)
    art = outline(A["back"], False); wl = outline(A["back"], True)
    out["01"] = dict(side_L=art.distance(e("B01", "side L")), side_R=art.distance(e("B01", "side R")),
                     armhole_L=art.distance(e("B01", "armhole L")), armhole_R=art.distance(e("B01", "armhole R")),
                     hem=res["back"][1].distance(e("B01", "hem")), neck=res["back"][1].distance(e("B01", "neck")),
                     wire_side_L=wl.distance(e("B01", "side L")), wire_side_R=wl.distance(e("B01", "side R")))
    for k, pc in (("03L", "F01"), ("03R", "F02")):
        art = outline(A["F" + k], False); wl = outline(A["F" + k], True); w = Polygon(g[pc].internal[0][1])
        d = dict(wire_side=wl.distance(e(pc, "side")), CF=res[k][1].distance(e(pc, "CF / zip")), hem=res[k][1].distance(e(pc, "hem")),
                 wire_welt=wl.distance(w))
        if not art.is_empty: d.update(side=art.distance(e(pc, "side")), welt=art.distance(w))
        else: d.update(welt=wl.distance(w))
        out[k] = d
    for k in ("02R", "02L"):
        pc = PIECE[k]; a = res[k][1]
        out[k] = dict(CF=a.distance(e(pc, "CF / zip")), armhole=a.distance(e(pc, "armhole")), shoulder=a.distance(e(pc, "shoulder")),
                      side=a.distance(e(pc, "side")), welt=a.distance(Polygon(g[pc].internal[0][1])),
                      collar=a.distance(FR.COLLAR_L if k == "02L" else FR.COLLAR_R))
    for k in ("04R", "04L"):
        pc = PIECE[k]; a = res[k][1]
        out[k] = dict(cap=a.distance(e(pc, "cap")), underarm=min(a.distance(e(pc, "underarm front")), a.distance(e(pc, "underarm back"))),
                      cuff=a.distance(e(pc, "cuff")), inside=float(g[pc].sew_poly().contains(a)))
    # wrap: every side-seam wire end on the back has its partner on the front at the same height (per size)
    m = A["info"]["marks"]
    bk = sorted((s, h) for s, h, d in m["back"] if d is not None and abs(d - 3) <= 0.6)
    fr = sorted((s, h) for s, h, d in m["front_L"] + m["front_R"] if d is not None and abs(d - 3) <= 0.6)
    out["wrap"] = dict(aligned=len(set(bk) & set(fr)), total=len(set(bk) | set(fr)))
    return out

def failures(c):
    bad = []
    for el, d in c.items():
        if el in ("nudge", "wrap"): continue
        for k, v in d.items():
            if k in MIN.get(el, {}) and v < MIN[el][k] - 0.05: bad.append(f"{el} {k} {v:.1f}<{MIN[el][k]}")
            if k in MAX.get(el, {}) and v > MAX[el][k]: bad.append(f"{el} {k} {v:.1f}>{MAX[el][k]}")
    if c["wrap"]["aligned"] != c["wrap"]["total"]: bad.append(f"wrap {c['wrap']}")
    return bad

if __name__ == "__main__":
    allc = {}
    for sz in drum.SIZES:
        c = clearances(sz); allc[sz] = c
        print(sz, "wrap", c["wrap"], "nudge", {k: tuple(round(v, 1) for v in d) for k, d in c["nudge"].items() if any(d)})
        print("   ", {e: {k: round(v, 1) for k, v in d.items()} for e, d in c.items() if e not in ("nudge", "wrap")})
        print("    FAIL:", failures(c) or "none")
    json.dump(allc, open("out/results/clearances.json", "w"), default=float, indent=1)
