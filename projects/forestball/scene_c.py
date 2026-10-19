"""Rev C scene = TRACED art (trace_fb.py: close-up a for the back, close-up b + mockup x4 for 02R, mockup x4 for 02L)
+ the parts we add on purpose: licensed-placeholder outline, ripple rings round the placeholder pool, and the light rays
re-sewn as a broad sheer overlay traced from close-up a (rays_trace.py). Writes back_vis.pkl + front_vis.pkl.
usage: ./py.sh scene_c.py [back] [front]"""
import sys, json, math, pickle, random, time
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box, MultiLineString
from shapely.ops import unary_union
from shapely import affinity
import shapely
import fbcore, tech, dst2
from fmotifs import R, polys
import back as B, front as F

LAYER = {"TB": 5, "TBS": 5, "TT": 5.5, "TTS": 5.5, "TM": 6, "TMS": 6, "TL": 4.5, "TLS": 4.5, "TH": 8, "THS": 8, "WA": 2, "WAS": 2}

def norm(regs):
    out = []
    for r in regs:
        if r["st"] == "tatami":                        # tatami tracing slivers (< 0.8 mm mean width, < 20 mm²) are not stitchable: dropped
            g = r["geom"]; w_ = 2 * g.area / max(g.length, 1e-6)
            if w_ < 1.0 and g.area < 30: continue
        if r["st"] == "satin" and r["grp"].startswith("TT"):   # traced twigs thinner than the 0.8 mm satin minimum: thickened to ~1 mm
            g = r["geom"]; w_ = 2 * g.area / max(g.length, 1e-6)
            if w_ < 0.9: r = dict(r, geom=g.buffer(0.5 - w_ / 2, quad_segs=4))
        fam = r["grp"].split("-")[0]
        g = fam + ("S" if r["st"] == "satin" else "")
        out.append(dict(r, grp=g, layer=LAYER[g], col=fbcore.col(r["col"])))
    return out

def ray_overlay(clip, voids, sp=2.3, w=0.32, core=0.42, seed=3):
    """traced bands -> sheer overlay: rows ALONG the ray every `sp` mm (run 0.64 wide => ~28 % cover), cream core / sage edges,
    row ends ragged by 0-14 % of the band length at both ends (soft fade); one serpentine object per tone per band."""
    bands = json.load(open("rays_trace.json")); rng = random.Random(seed); regs = []; cov = []
    for bi, b in enumerate(bands):
        P = Polygon(b["pts"]).buffer(0).intersection(clip).difference(voids)
        if P.is_empty: continue
        th = math.radians(b["angle"]); d = np.array([-math.sin(th), math.cos(th)]); n = np.array([math.cos(th), math.sin(th)])
        c = np.array(P.centroid.coords[0]); span = max(P.bounds[2] - P.bounds[0], P.bounds[3] - P.bounds[1]) * 1.5
        us = [n @ np.array(q) for q in P.exterior.coords]; u0, u1 = min(us), max(us)
        rows = {"sage": [], "cream": []}
        for k, u in enumerate(np.arange(u0 + sp / 2, u1, sp)):
            f = (u - u0) / max(u1 - u0, 1e-6) - 0.5
            base = n * u; ln = LineString([tuple(base - d * span + d * (d @ c)), tuple(base + d * span + d * (d @ c))]).intersection(P)
            for seg in ([ln] if ln.geom_type == "LineString" else list(getattr(ln, "geoms", []))):
                if seg.geom_type != "LineString" or seg.length < 15: continue
                L = seg.length; a = rng.uniform(0, 0.14) * L * (0.6 + abs(f)); e = rng.uniform(0, 0.14) * L * (0.6 + abs(f))
                if L - a - e < 12: continue
                s_ = shapely.ops.substring(seg, a, L - e)
                rows["cream" if abs(f) < core / 2 else "sage"].append(list(s_.coords))
        for col, rr in rows.items():
            if not rr: continue
            rr.sort(key=lambda cs: n @ np.array(cs[0]))
            seq = []
            for i, cs in enumerate(rr): seq += cs if i % 2 == 0 else cs[::-1]
            g = LineString(seq).buffer(w, cap_style="round", join_style="round").intersection(P.buffer(0.5))
            regs.append(dict(col=col, geom=g, st="run", ang=None, grp="LR", layer=11, overlay=True))
        cov.append(sum(r["geom"].area for r in regs[-2:]) / P.area if P.area else 0)
    return regs, cov

def ripple_rings(box_, water, n=4, gap=4.5):
    c = box_.centroid; hw = (box_.bounds[2] - box_.bounds[0]) / 2; hh = (box_.bounds[3] - box_.bounds[1]) / 2
    out = []
    for i in range(1, n + 1):
        e = affinity.scale(Point(c.x, c.y).buffer(1.0, quad_segs=24), hw * 1.12 + i * gap, hh * 0.62 + i * gap * 0.55)
        ring = e.exterior.buffer(0.35).intersection(water).difference(box_.buffer(2.0))
        if not ring.is_empty: out.append(dict(col="cream" if i % 2 else "waterlt", geom=ring, st="run", ang=None, grp="RI", layer=8.5))
    return out

def knockout(items, clip):
    """later items (higher layer / later in list) knock out earlier ones; overlays (rays) and the placeholder knock out nothing"""
    vis = []; above = B.VOID if clip is B.CLIP else Polygon()
    for r in reversed(items):
        if r.get("overlay") or r["grp"] == "PH": vis.append(r); continue
        g = r["geom"].intersection(clip).difference(above)
        above = above.union(r["geom"]) if r["st"] not in ("run", "bean") else above
        vis.append(dict(r, geom=g))
    vis.reverse()
    return [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.05]

def build_back():
    t = time.time()
    tr = norm(pickle.load(open("trace_back.pkl", "rb")))
    water = unary_union([r["geom"] for r in tr if r["grp"].startswith("WA")]).buffer(1.0)
    rings = ripple_rings(B.PH_BOX, water.union(B.STREAM).intersection(B.PH_BOX.buffer(30)))
    ph = [dict(B.PH_OUT, col=fbcore.col("basting"), layer=0)]
    rays, cov = ray_overlay(B.CLIP, B.VOID)
    vis = ph + tr + knockout(rings, B.CLIP)               # traced regions are already disjoint (one tone per pixel)
    vis = dst2.clean_vis([v for v in vis if v["grp"] != "PH"]) + ph
    vis += rays
    print("back", len(vis), "regions; ray cover per band %", [round(100 * c) for c in cov], f"{time.time()-t:.0f}s", flush=True)
    return vis, cov

def build_front():
    tr = pickle.load(open("trace_front.pkl", "rb")); out = {}
    for p in ("02R", "02L"):
        out[p] = dst2.clean_vis(norm(tr[p])); print(p, len(out[p]), "regions", flush=True)
    return out

if __name__ == "__main__":
    what = sys.argv[1:] or ["back", "front"]
    if "back" in what:
        vb, cov = build_back(); pickle.dump({"back": vb}, open("back_vis.pkl", "wb"))
        json.dump(dict(ray_cover_pct=[round(100 * c, 1) for c in cov]), open("rays_cover.json", "w"))
    if "front" in what:
        pickle.dump(build_front(), open("front_vis.pkl", "wb"))
