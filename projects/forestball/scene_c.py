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

def split_wide_satin(regs):
    """Rev C final (found by the A15 uncovered gate): the trace sent a region to satin when its MEAN width (2A/P) was < 3.2,
    so big convoluted regions with holes (a 1,380 mm² stream area, moss mats) became one 'satin' whose centreline is garbage —
    the engine left most of them unsewn. Now: the parts wider than 3.2 mm (an opening by 1.6 mm) sew as tatami (stream
    horizontal, others along the region's own axis), the thin remainder stays satin strands."""
    out = []; moved = 0.0
    for r in regs:
        if r["st"] != "satin" or r["geom"].buffer(-1.6).is_empty: out.append(r); continue
        g = r["geom"]; wide = g.buffer(-1.6).buffer(1.6, join_style="round").intersection(g)
        thin = g.difference(wide.buffer(0.05))
        fam = r["grp"].split("-")[0]; moved += wide.area
        if not wide.is_empty and wide.area > 1.0:
            out.append(dict(r, geom=wide, st="tatami", grp=fam, ang=0.0 if fam == "WA" else "auto"))
        for q in polys(thin):
            if q.area > 1.0: out.append(dict(r, geom=q))
    print("   wide satin -> tatami:", round(moved), "mm²", flush=True)
    return out

def norm(regs):
    out = []
    regs = split_wide_satin(regs)
    for r in regs:
        if r["st"] == "tatami":                        # tatami tracing slivers (< 0.8 mm mean width, < 20 mm²) are not stitchable: dropped
            g = r["geom"]; w_ = 2 * g.area / max(g.length, 1e-6)
            if w_ < 1.0 and g.area < 30: continue
        if r["st"] == "satin":   # Rev C final: ANY traced satin strand thinner than the 0.8 mm minimum (twigs, moss strands,
            # bark slivers) is thickened to ~1 mm (it overlaps its neighbour by <= 0.15 mm), so the width check passes without
            # dropping the strand
            g = r["geom"]; w_ = 2 * g.area / max(g.length, 1e-6)
            if w_ < 0.9: r = dict(r, geom=g.buffer(0.5 - w_ / 2, quad_segs=4))
        fam = r["grp"].split("-")[0]
        g = fam + ("S" if r["st"] == "satin" else "")
        out.append(dict(r, grp=g, layer=LAYER[g], col=fbcore.col(r["col"])))
    return out

def ray_overlay(clip, voids, sp=2.3, w=0.32, core=0.42, seed=3, under=None, sp_core=1.8, sp_edge=2.8, ymax=470.0):
    """Rev C (review item 5): rays sew FIRST and are knocked out by every later art object (`under` = art silhouette), so
    they read as light falling BEHIND the limb, leaves and bank as in close-up a; row spacing 1.8 mm in the cream core,
    2.8 mm in the sage edges (soft edges), cut at y = ymax (they fade into the grass / stream in the close-up)."""
    """traced bands -> sheer overlay: rows ALONG the ray every `sp` mm (run 0.64 wide => ~28 % cover), cream core / sage edges,
    row ends ragged by 0-14 % of the band length at both ends (soft fade); one serpentine object per tone per band."""
    bands = json.load(open("rays_trace.json")); rng = random.Random(seed); regs = []; cov = []
    for bi, b in enumerate(bands):
        P = Polygon(b["pts"]).buffer(0).intersection(clip).difference(voids).intersection(box(-400, -100, 400, ymax))
        if P.is_empty: continue
        th = math.radians(b["angle"]); d = np.array([-math.sin(th), math.cos(th)]); n = np.array([math.cos(th), math.sin(th)])
        c = np.array(P.centroid.coords[0]); span = max(P.bounds[2] - P.bounds[0], P.bounds[3] - P.bounds[1]) * 1.5
        us = [n @ np.array(q) for q in P.exterior.coords]; u0, u1 = min(us), max(us)
        rows = {"sage": [], "cream": [], "sage2": []}; ph1, ph2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
        us_ = []; u = u0 + sp_edge / 2
        while u < u1:
            f = (u - u0) / max(u1 - u0, 1e-6) - 0.5; us_.append(u); u += sp_core if abs(f) < core / 2 else sp_edge
        for k, u in enumerate(us_):
            f = (u - u0) / max(u1 - u0, 1e-6) - 0.5
            base = n * u; ln = LineString([tuple(base - d * span + d * (d @ c)), tuple(base + d * span + d * (d @ c))]).intersection(P)
            for seg in ([ln] if ln.geom_type == "LineString" else list(getattr(ln, "geoms", []))):
                if seg.geom_type != "LineString" or seg.length < 15: continue
                # soft ends: the trim-back varies SMOOTHLY row to row (≤ ~2 mm between neighbours), so the serpentine
                # connectors stay short and the band ends fade along a soft wavy edge (no zig-zag spikes)
                L = seg.length
                a = (3.0 + 10.0 * (0.5 + 0.5 * math.sin(0.42 * k + ph1)) + 18.0 * abs(f)) * min(1.0, L / 120.0)
                e = (3.0 + 10.0 * (0.5 + 0.5 * math.sin(0.37 * k + ph2)) + 18.0 * abs(f)) * min(1.0, L / 120.0)
                if L - a - e < 12: continue
                s_ = shapely.ops.substring(seg, a, L - e)
                rows["cream" if abs(f) < core / 2 else ("sage" if f < 0 else "sage2")].append(list(s_.coords))   # each edge its own object: no connector over the core
        for col, rr in rows.items():
            if not rr: continue
            rr.sort(key=lambda cs: n @ np.array(cs[0]))
            seq = []
            for i, cs in enumerate(rr): seq += cs if i % 2 == 0 else cs[::-1]
            g = LineString(seq).buffer(w, cap_style="round", join_style="round").intersection(P.buffer(0.5))
            band_cov = g.area / P.area if P.area else 0
            if under is not None: g = g.difference(under)
            parts = [q for q in (list(g.geoms) if hasattr(g, "geoms") else [g]) if q.geom_type == "Polygon" and q.area > 3.0]
            if not parts: continue
            regs.append(dict(col=col.rstrip("2"), geom=unary_union(parts), st="run", ang=None, grp="LR", layer=1, cov=band_cov, band=bi))
        cov.append(sum(r["cov"] for r in regs if r.get("band") == bi))
    return regs, cov

def ray_stripes(clip, voids, under, sp_cream=1.3, sp_sage=1.6, w=0.32, cream_ex=11.0):
    """Rev C final (founder 19 Oct + LESSONS A14): the rays are the mockup's own light stripes, each traced with its own
    silhouette and axis (rays_trace2.py) — they fan, end and fade where the mockup's do. Each stripe is filled with run rows
    ALONG its own axis (1.3 mm apart in bright cream stripes, 1.6 mm in the dimmer sage ones: a sheer veil, ~40-50 % inside
    a stripe, ~20-30 % over a ray band), one serpentine object per stripe; sewn FIRST, every later object covers it."""
    R = json.load(open("rays_trace2.json")); regs = []; A_st = 0.0; A_run = 0.0
    for k, st in enumerate(R["stripes"]):
        P = Polygon(st["pts"]).buffer(0).intersection(clip).difference(voids)
        if P.is_empty or P.area < 3: continue
        d = np.array(st["dir"]); d = d / np.linalg.norm(d); n = np.array([-d[1], d[0]])
        col = "cream" if st["excess"] >= cream_ex else "sage"; sp = sp_cream if col == "cream" else sp_sage
        sp = min(sp, max(0.7, st["width"] / 2.2))       # narrow stripes keep >= 2 rows (they read as a stripe, not a hairline)
        us = [n @ np.array(q) for q in P.exterior.coords]; u0, u1 = min(us), max(us); c = np.array(P.centroid.coords[0])
        span = max(P.bounds[2] - P.bounds[0], P.bounds[3] - P.bounds[1]) * 1.5 + 10
        rows = []
        for u in np.arange(u0 + min(sp, (u1 - u0)) / 2, u1, sp):
            base = n * u + d * (d @ c)
            ln = LineString([tuple(base - d * span), tuple(base + d * span)]).intersection(P.buffer(-0.2))
            for seg in ([ln] if ln.geom_type == "LineString" else list(getattr(ln, "geoms", []))):
                if seg.geom_type == "LineString" and seg.length >= 2.5: rows.append(list(seg.coords))
        if not rows: continue
        rows.sort(key=lambda cs: n @ np.array(cs[0])); seq = []
        for i, cs in enumerate(rows): seq += cs if i % 2 == 0 else cs[::-1]
        g = LineString(seq).buffer(w, cap_style="round", join_style="round").intersection(P.buffer(0.3))
        A_st += P.area; A_run += g.area
        g = g.difference(under)
        parts = [q for q in (list(g.geoms) if hasattr(g, "geoms") else [g]) if q.geom_type == "Polygon" and q.area > 1.5]
        if parts: regs.append(dict(col=col, geom=unary_union(parts), st="run", ang=None, grp="LR", layer=1, stripe=k))
    return regs, (A_run / A_st if A_st else 0.0)

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
    art = unary_union([r["geom"] for r in tr]).buffer(0.6)
    rays, cov = ray_stripes(B.CLIP, B.VOID, under=art)
    # LESSONS A14: no generated stand-ins — the pool's ripple rings are the ones TRACED from close-up a (no generated rings)
    vis = ph + tr                                          # traced regions are already disjoint (one tone per pixel)
    vis = dst2.clean_vis([v for v in vis if v["grp"] != "PH"]) + ph
    vis = rays + vis                                       # rays first (layer 1): every later object covers them
    print("back", len(vis), "regions;", len(rays), "ray stripes, cover inside the stripes", round(100 * cov), "%", f"{time.time()-t:.0f}s", flush=True)
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
        R = json.load(open("rays_trace2.json")); ax = [st["axis_deg"] for st in R["stripes"]]
        json.dump(dict(stripes=len(R["stripes"]), sewn=len({r["stripe"] for r in vb if r.get("stripe") is not None}),
                       axis_deg_min=min(ax), axis_deg_max=max(ax), vp=R["vp"], cover_in_stripes_pct=round(100 * cov, 1)), open("rays_cover.json", "w"))
    if "front" in what:
        pickle.dump(build_front(), open("front_vis.pkl", "wb"))
