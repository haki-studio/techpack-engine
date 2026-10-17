"""Per-size production stitch files: one full file per piece + hoop splits for the factory frame (factory.json).
usage: python3 build_size.py SIZE [BK FR FL SR SL] [nosplit] [splitsonly]
Every number written to result_<piece>.json is read back from the DST (readback.dst, LESSONS B8/B20).
Colours: the jacket board has 18 threads; each piece sews <= 12 (factory limit incl. registration): merge_plan.json
(built once from the size-M art, used for every size so all sizes of a piece look the same) maps a piece's least-used tones
to their closest thread (ΔE2000 x area cost)."""
import cfcore
import pickle, json, sys, time, os, math, inspect
import numpy as np
from shapely.ops import unary_union
from shapely.geometry import Point
import tech, readback, factory
from motifs2 import HEX
dst2 = cfcore.patch_dst2()

PROF = factory.load(); LIMIT = factory.max_threads(PROF)
FRAME = tuple(float(v) for v in factory.largest_frame(PROF))

# split_clip with a wider split-line search (engine searches 40-60 % only): every frame-legal line 15-85 % (Grand Line ENGINE_NOTES 8)
_src = inspect.getsource(dst2.split_clip)
_src = _src.replace("xs = np.linspace(b[0] + (b[2]-b[0])*0.40, b[0] + (b[2]-b[0])*0.60, 21) if nx == 2 else [None]",
                    "xs = np.linspace(b[0] + (b[2]-b[0])*0.30, b[0] + (b[2]-b[0])*0.70, 41) if nx == 2 else [None]")
_src = _src.replace("ys = np.linspace(b[1] + (b[3]-b[1])*0.40, b[1] + (b[3]-b[1])*0.60, 21) if ny == 2 else [None]",
                    "ys = np.linspace(b[1] + (b[3]-b[1])*0.15, b[1] + (b[3]-b[1])*0.85, 57) if ny == 2 else [None]")
assert "0.85, 57" in _src and "0.70, 41" in _src, "engine split_clip changed: update the search patch"
_ns = dict(vars(dst2)); exec(_src, _ns); split_clip_wide = _ns["split_clip"]

def merge_plan():
    """{piece: {tone: thread}} so each piece uses <= LIMIT colours; cost = ΔE2000 x sqrt(area of the merged tone)"""
    p = "merge_plan.json"
    if os.path.exists(p): return json.load(open(p))
    D = pickle.load(open("art_M.pkl", "rb")); plan = {}
    for P in cfcore.PIECES:
        area = {}
        for r in D[P]: area[r["col"]] = area.get(r["col"], 0) + r["geom"].area
        m = {}; cols = set(area)
        while len(cols) > LIMIT:
            best = None
            for a in cols:
                for b in cols:
                    if a == b: continue
                    de = tech.de2000(tech._lab(tuple(int(HEX[a][i:i+2], 16) for i in (1, 3, 5))), tech._lab(tuple(int(HEX[b][i:i+2], 16) for i in (1, 3, 5))))
                    c = de * math.sqrt(area[a])
                    if best is None or c < best[0]: best = (c, a, b, de)
            _, a, b, de = best
            for k, v in list(m.items()):
                if v == a: m[k] = b
            m[a] = b; area[b] += area.pop(a); cols.discard(a)
        plan[P] = m
    json.dump(plan, open(p, "w"), indent=1); return plan

def cap_stitches(pat, mx=7.4):
    """belt + braces for LESSONS B17 (the engine splits at 7.4 too)"""
    import pyembroidery as pe
    out = []; prev = None
    for x, y, c in pat.stitches:
        if (c & pe.COMMAND_MASK) == pe.STITCH and prev is not None:
            d = math.hypot(x - prev[0], y - prev[1]) / 10.0
            if d > mx:
                n = int(math.ceil(d / 6.0))
                for k in range(1, n): out.append([prev[0] + (x - prev[0])*k/n, prev[1] + (y - prev[1])*k/n, pe.STITCH])
        out.append([x, y, c])
        prev = (x, y) if (c & pe.COMMAND_MASK) in (pe.STITCH, pe.JUMP) else prev
    pat.stitches = out
    return pat

def reg_in_first_colour(pat):
    """factory limit (12 colours incl. registration): the crosses sew at the start of stop 1 in stop 1's thread"""
    import pyembroidery as pe
    if len(pat.threadlist) < 2 or pat.threadlist[0].catalog_number != "WSB": return pat
    pat.threadlist.pop(0)
    for i, (x, y, c) in enumerate(pat.stitches):
        if (c & pe.COMMAND_MASK) == pe.COLOR_CHANGE: del pat.stitches[i]; break
    return pat

def stops_for(vis):
    st = tech.stops(vis); n0 = len(st); return dst2.merge_stops(st), n0

def sews(stops, basting=False):
    out = []
    for s in stops:
        out.append(dict(col=s["col"], codes=sorted({tech.rule_for(r["grp"]) for r in s["regions"]}),
                        types=sorted({r["st"] for r in s["regions"]}), objects=len(s["regions"])))
    if basting and out: out[0]["codes"] = ["REG crosses"] + out[0]["codes"]
    return out

def record(base, stops, extra, basting=False):
    rb = readback.dst(base + ".dst"); rb["threads"] = factory.check_threads(base + ".pes", PROF)
    info = sews(stops, basting)
    assert len(info) == rb["stops"], f"{base}: {len(info)} stops built vs {rb['stops']} in the DST"
    for ps, si in zip(rb["per_stop"], info): ps.update(si)
    rb.update(extra, file=base); return rb

NAMES = {(0, 0): "S1_top-left", (1, 0): "S2_top-right", (0, 1): "S3_bottom-left", (1, 1): "S4_bottom-right"}
def sec_name(key, sp):
    if sp["sx"] is None: return {0: "S1_top", 1: "S2_bottom"}[key[1]]
    if sp["sy"] is None: return {0: "S1_left", 1: "S2_right"}[key[0]]
    return NAMES[key]

if __name__ == "__main__":
    size = sys.argv[1]
    which = [a for a in sys.argv[2:] if a in cfcore.PIECES] or list(cfcore.PIECES)
    D = pickle.load(open(f"art_{size}.pkl", "rb")); PLAN = merge_plan()
    for P in which:
        e = cfcore.PIECE_ELEM[P]; OUT = f"out/{e}_{cfcore.ELEMS[e][0]}/{size}"; os.makedirs(OUT, exist_ok=True)
        rp = f"{OUT}/result_{P}.json"
        res = json.load(open(rp)) if os.path.exists(rp) else {}
        vis = dst2.merge_colours(D[P], PLAN[P])
        assert len({r["col"] for r in vis}) <= LIMIT, f"{P}: {len({r['col'] for r in vis})} colours > {LIMIT}"
        tag = f"HAKI_{cfcore.SHORT}_{e}_{cfcore.ELEMS[e][0]}_{P}_{size}"
        if "splitsonly" not in sys.argv:
            t = time.time()
            ub = dst2.bounds_of([r["geom"] for r in vis]); c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
            stops, n0 = stops_for(vis); pat, st = dst2.make_pattern(vis, stops, c)
            base = f"{OUT}/{tag}"
            dst2.write(cap_stitches(pat), base); dst2.render(base, base + "_preview.png", bg=(46, 56, 71), s=0.5)
            ex = dst2.exposed_travel(stops, st.get("runs", []))
            res["full"] = record(base, stops, dict(origin=c, art_box=ub, stops_before_merge=n0, secs=round(time.time()-t), merged_tones=PLAN[P],
                                 exposed_travel=dict(runs_over_1mm=sum(1 for x in ex if x > 1.0), runs_over_2mm=sum(1 for x in ex if x > 2.0), max_mm=round(max(ex), 1) if ex else 0.0),
                                 build_trims_by_code=sorted(st.get("by", {}).items(), key=lambda kv: -kv[1])[:10], trims_why=st.get("why", {})))
            f_ = res["full"]
            print(size, P, {k: f_[k] for k in ("stitches", "trims", "jumps", "stops", "size_mm", "max_stitch", "threads")}, f"{f_['secs']}s", flush=True)
            json.dump(res, open(rp, "w"), default=float, indent=1)
        if "nosplit" not in sys.argv:
            for wm in (70.0, 55.0, 40.0):
                sp = split_clip_wide(vis, FRAME, whole_max=wm)
                if all(sp["fits"].values()): break
            jobs = []
            if all(sp["fits"].values()):
                marks = dst2.split_marks(sp, ext=4.0)
                spl = dict(frame=FRAME, sx=sp["sx"], sy=sp["sy"], xs=[sp["sx"]] if sp["sx"] is not None else [], ys=[sp["sy"]] if sp["sy"] is not None else [],
                           grid=[2 if sp["sx"] is not None else 1, 2 if sp["sy"] is not None else 1], cut_mm=sp["cut"], whole_max=wm, method="split_clip", sections={})
                for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])): jobs.append((sec_name(key, sp), sp["secs"][key], marks[key]))
            else:          # wider than two hoopings (XXL/3XL back): any-grid split (moon gridsplit), crosses on the split lines
                import gridsplit
                gp = gridsplit.grid_split(vis, FRAME)
                spl = dict(frame=FRAME, sx=None, sy=None, xs=gp["xs"], ys=gp["ys"], grid=[gp["nx"], gp["ny"]], cut_mm=gp["cut"], whole_max=70.0, method="grid_split", sections={})
                for key in sorted(gp["secs"], key=lambda k: (k[1], k[0])): jobs.append((gp["names"][key], gp["secs"][key], gp["marks"][key]))
            for nm, sv, mk in jobs:
                t = time.time(); stops, n0 = stops_for(sv)
                bb = dst2.bounds_of([r["geom"] for r in sv] + [Point(m).buffer(6) for m in mk])
                cc = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
                pat, st = dst2.make_pattern(sv, stops, cc, reg_marks=mk)
                base = f"{OUT}/splits/{tag}_{nm}"; os.makedirs(os.path.dirname(base), exist_ok=True)
                dst2.write(cap_stitches(reg_in_first_colour(pat)), base); dst2.render(base, base + "_preview.png", bg=(46, 56, 71), s=0.5)
                r = record(base, stops, dict(bbox=bb, origin=cc, marks=mk, secs=round(time.time()-t)), basting=True)
                r["fits"] = r["size_mm"][0] <= FRAME[0] - 16 and r["size_mm"][1] <= FRAME[1] - 16
                spl["sections"][nm] = r
                print(size, P, nm, {k: r[k] for k in ("stitches", "trims", "stops", "size_mm", "fits", "threads")}, flush=True)
            if "splitsonly" in sys.argv and os.path.isdir(f"{OUT}/splits"):
                for fn in os.listdir(f"{OUT}/splits"):          # drop section files of an older split layout
                    if fn.startswith(tag + "_") and not any(fn.startswith(f"{tag}_{nm}.") or fn.startswith(f"{tag}_{nm}_") for nm in spl["sections"]):
                        os.remove(f"{OUT}/splits/{fn}")
            res["splits"] = spl; json.dump(res, open(rp, "w"), default=float, indent=1)
    print("DONE", size, which, flush=True)
