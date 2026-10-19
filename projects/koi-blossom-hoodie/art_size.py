"""Per-size art for the four pieces (LESSONS A5): the size-M scene is graded (A 92 % / B 100 % / C 108 %) — fronts about
the CF neck point (both halves share the origin, so the zip line is the same on both), sleeves about the cuff-seam centre
(then moved onto that size's cuff seam) — and fitted inside THAT size's pattern keep-outs.
Fidelity first (A11): nothing is cut by a keep-out line. Whole motifs (fish, floating petals) and whole flower clusters
are nudged (<= 18 mm) and, only if that is not enough, shrunk (>= 85 %) until they sit inside the keep-outs; a leaf at the
edge of a cluster that still does not fit is moved inward along its own axis. Every move is recorded (art_<size>.pkl info).
usage: python3 art_size.py XS S M ...   -> art_<size>.pkl + out/art/<size>_flat.png"""
import kbcore
import pickle, sys, os, math, time
import numpy as np
from shapely.geometry import Point, box
from shapely.ops import unary_union
from shapely import affinity, prepared
import front as F, dst2, kbvis
kbcore.patch_dst2()

SC = pickle.load(open("scene.pkl", "rb")); ITEMS = SC["items"]; META = SC["meta"]
_, MT_M = F.pieces("M")

def xform(r, s, ox, oy, dx=0.0, dy=0.0):
    g = affinity.translate(affinity.scale(r["geom"], s, s, origin=(ox, oy)), dx, dy).buffer(0)
    a = r["ang"]
    if isinstance(a, tuple): a = (a[0], ox + (a[1] - ox)*s + dx, oy + (a[2] - oy)*s + dy)
    return dict(r, geom=g, ang=a)

def graded(P, size):
    grade, s = kbcore.GRADE[size]
    if P in ("FR", "FL"): return [xform(r, s, 0, 0) for r in ITEMS[P]]
    _, mt = F.pieces(size)
    return [xform(r, s, 0, MT_M["Lu"], 0, mt["Lu"] - MT_M["Lu"]) for r in ITEMS[P]]

def fit_group(regs, lim, maxd=18.0, scales=(1.0, 0.97, 0.94, 0.91, 0.88, 0.85)):
    """smallest move (then shrink) that puts the union of regs inside lim. returns (regs', move) or (None, None)"""
    u = unary_union([r["geom"] for r in regs])
    if lim.contains(u): return regs, (0.0, 0.0, 1.0)
    c = u.centroid
    for s in scales:
        us = affinity.scale(u, s, s, origin=c)
        for rr in np.arange(0.0 if s < 1 else 1.0, maxd + 0.1, 1.0):
            for th in np.linspace(0, 2*math.pi, max(8, int(rr*3)), endpoint=False):
                dx, dy = rr*math.cos(th), rr*math.sin(th)
                if lim.contains(affinity.translate(us, dx, dy)):
                    return [xform(r, s, c.x, c.y, dx, dy) for r in regs], (dx, dy, s)
    return None, None

def build(size):
    t0 = time.time(); grade, s = kbcore.GRADE[size]
    res = {"info": dict(size=size, grade=grade, scale=s, variant=F.VARIANT)}
    for P in kbcore.PIECES:
        clip = F.clip_for(size, P).buffer(-0.4)       # 0.4 inside the keep-out: cleaning + simplification never cross it
        lim = prepared.prep(clip)
        its = graded(P, size)
        groups = {}
        for r in its: groups.setdefault(r["cluster"] or r["unit"], []).append(r)
        out, moves, leafmoves, dropped = [], {}, {}, []
        for gk, regs in groups.items():
            is_cl = regs[0]["cluster"] is not None
            if size == "M" and gk.startswith(("fill_", "petal_")):   # traced from the mockup inside size M's keep-outs: placed as traced (A14); graded sizes are fitted
                out += regs; continue
            fitted, mv = (None, None) if is_cl else fit_group(regs, lim)
            if fitted is None and not is_cl: fitted, mv = fit_group(regs, lim, 32.0)      # Rev B: wider search before giving up (no motif dropped)
            if fitted is not None:
                out += fitted
                if mv != (0.0, 0.0, 1.0): moves[gk] = tuple(round(v, 2) for v in mv)
                continue
            if not is_cl: dropped.append(gk); continue
            # flower cluster: fit its core (flowers + stems) as one, then each leaf on its own (nudged / shrunk, never cut)
            core = [r for r in regs if r["unit"].split("_")[-1].startswith(("flower", "stem"))]
            if not core:                     # a traced cluster of leaves only (no lily / stem): every leaf fitted on its own
                core = []; cf, mv = [], (0.0, 0.0, 1.0)
            else:
                cf, mv = fit_group(core, lim, 24.0)
            if cf is None and core: cf, mv = fit_group(core, lim, 36.0, (1.0, 0.95, 0.9, 0.85, 0.8, 0.76))     # Rev B: wider search, never cut a cluster
            if cf is None:
                cf, mv = core, (0.0, 0.0, 1.0); dropped.append(gk + " core (does not fit)")
            out += cf
            if mv != (0.0, 0.0, 1.0): moves[gk] = tuple(round(v, 2) for v in mv)
            leaves = {}
            for r in regs:
                if r not in core: leaves.setdefault(r["unit"], []).append(r)
            c0 = unary_union([r["geom"] for r in (core or regs)]).centroid
            for lu, lr in leaves.items():
                # apply the core move first (leaves stay with their stems), then fit the leaf alone
                lr = [xform(r, mv[2], c0.x, c0.y, mv[0], mv[1]) for r in lr]
                lf, lmv = fit_group(lr, lim, 14.0)
                if lf is None: dropped.append(lu)
                else:
                    out += lf
                    if lmv != (0.0, 0.0, 1.0): leafmoves[lu] = tuple(round(v, 2) for v in lmv)
        vis = kbvis.visible(out, clip)
        vis = dst2.clean_vis(vis)
        vis = [dict(r, geom=r["geom"].intersection(clip).buffer(0)) for r in vis]
        vis = [r for r in vis if not r["geom"].is_empty and r["geom"].area > 0.3]
        res[P] = vis
        u = unary_union([r["geom"] for r in vis])
        res["info"][P] = dict(objects=len(vis), area=u.area, bbox=u.bounds, moves=moves, leaf_moves=leafmoves, dropped=dropped,
                              units=len({r["unit"] for r in vis}))
    pickle.dump(res, open(f"art_{size}.pkl", "wb"))
    print(size, grade, s, {P: (res["info"][P]["objects"], [round(v) for v in res["info"][P]["bbox"]], len(res["info"][P]["moves"]),
                               len(res["info"][P]["leaf_moves"]), res["info"][P]["dropped"]) for P in kbcore.PIECES}, f"{time.time()-t0:.0f}s", flush=True)
    return res

if __name__ == "__main__":
    os.makedirs("out/art", exist_ok=True)
    for sz in sys.argv[1:] or kbcore.SIZES: build(sz)
