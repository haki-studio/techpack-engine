"""Per-size production stitch files for the four pieces (FR, FL fronts; SR, SL sleeves): full file + hoop splits for the
factory frame (factory.json). usage: python3 build_size.py SIZE [FR FL SR SL] [nosplit] [splitsonly]
Stop order: all flat stops first, then (fronts) one machine PAUSE to lay 3 mm puff foam, then the puff stops (region codes
PF-*). merge_stops runs separately on the flat and the puff block so nothing puff is pulled in front of the foam.
Every number written to result_<piece>.json is read back from the DST (readback.dst, LESSONS B8/B20)."""
import kccore
import pickle, json, sys, time, os, math, inspect
from shapely.ops import unary_union
from shapely.geometry import Point
import tech, readback, factory
dst2 = kccore.patch_dst2()

size = sys.argv[1]
which = [a for a in sys.argv[2:] if a in kccore.PIECES] or list(kccore.PIECES)
D = pickle.load(open(f"art_{size}.pkl", "rb"))
FRAME = tuple(float(v) for v in factory.largest_frame(factory.load()))
PREFIX = f"HAKI_{kccore.SHORT}"
def out_dir(P): return f"out/stitch/{size}"

# split_clip with a wider split-line search (engine: 40-60 % of the extent; grand-line-jacket ENGINE_NOTES 8)
_src = inspect.getsource(dst2.split_clip)
_src = _src.replace("ys = np.linspace(b[1] + (b[3]-b[1])*0.40, b[1] + (b[3]-b[1])*0.60, 21) if ny == 2 else [None]",
                    "ys = np.linspace(b[1] + (b[3]-b[1])*0.15, b[1] + (b[3]-b[1])*0.85, 57) if ny == 2 else [None]")
_src = _src.replace("xs = np.linspace(b[0] + (b[2]-b[0])*0.40, b[0] + (b[2]-b[0])*0.60, 21) if nx == 2 else [None]",
                    "xs = np.linspace(b[0] + (b[2]-b[0])*0.25, b[0] + (b[2]-b[0])*0.75, 41) if nx == 2 else [None]")
assert "0.85, 57" in _src and "0.75, 41" in _src, "engine split_clip changed: update the search patch"
_ns = dict(vars(dst2)); exec(_src, _ns); split_clip_wide = _ns["split_clip"]

def is_puff(r): return tech.rule_for(r["grp"]).startswith("PF-") and kccore.PUFF

def stops_for(vis):
    flat = [r for r in vis if not is_puff(r)]; puff = [r for r in vis if is_puff(r)]
    st_f = tech.stops(flat) if flat else []; st_p = tech.stops(puff) if puff else []
    n0 = len(st_f) + len(st_p)
    st_f = dst2.merge_stops(st_f) if st_f else []; st_p = dst2.merge_stops(st_p) if st_p else []
    for s in st_p: s["puff"] = True
    return st_f + st_p, n0

def reg_in_first_colour(pat):
    """factory limit (12 colours incl. registration): the crosses sew at the start of stop 1 in stop 1's thread"""
    import pyembroidery as pe
    if len(pat.threadlist) < 2 or pat.threadlist[0].catalog_number != "WSB": return pat
    pat.threadlist.pop(0)
    for i, (x, y, c) in enumerate(pat.stitches):
        if (c & pe.COMMAND_MASK) == pe.COLOR_CHANGE: del pat.stitches[i]; break
    return pat

def sews(stops, basting=False):
    out = []
    for s in stops:
        out.append(dict(col=s["col"], codes=sorted({tech.rule_for(r["grp"]) for r in s["regions"]}),
                        types=sorted({r["st"] for r in s["regions"]}), objects=len(s["regions"]),
                        elements=sorted({r["el"] for r in s["regions"]}), puff=bool(s.get("puff"))))
    if basting and out: out[0]["codes"] = ["REG crosses"] + out[0]["codes"]
    return out

def record(base, stops, extra, basting=False):
    rb = readback.dst(base + ".dst"); rb["threads"] = factory.check_threads(base + ".pes")
    info = sews(stops, basting)
    assert len(info) == rb["stops"], f"{base}: {len(info)} stops built vs {rb['stops']} in the DST"
    for ps, si in zip(rb["per_stop"], info): ps.update(si)
    fp = [ps["stop"] for ps in rb["per_stop"] if ps.get("puff")]
    rb["foam_pause_before_stop"] = fp[0] if fp else None
    rb.update(extra, file=base); return rb

def runs_exposed(stops, st):
    ex = dst2.exposed_travel(stops, st.get("runs", []))
    return dict(runs_exposed_gt1mm=sum(1 for v in ex if v > 1.0), max_exposed_mm=round(max(ex), 2) if ex else 0.0)

for P in which:
    OUT = out_dir(P); os.makedirs(OUT, exist_ok=True)
    rp = f"{OUT}/result_{P}.json"
    res = json.load(open(rp)) if os.path.exists(rp) else {}
    vis = dst2.merge_colours(D[P])
    if "splitsonly" not in sys.argv:
        t = time.time()
        ub = dst2.bounds_of([r["geom"] for r in vis]); c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
        stops, n0 = stops_for(vis); pat, st = dst2.make_pattern(vis, stops, c)
        base = f"{OUT}/{PREFIX}_{P}_{size}"
        dst2.write(pat, base); dst2.render(base, base + "_preview.png", bg=(25, 28, 36), s=0.5)
        res["full"] = record(base, stops, dict(origin=c, art_box=ub, stops_before_merge=n0, secs=round(time.time()-t),
                                               build_trims_by_code=sorted(st.get("by", {}).items(), key=lambda kv: -kv[1])[:10],
                                               trims_why=st.get("why", {}), **runs_exposed(stops, st)))
        f_ = res["full"]
        print(size, P, {k: f_[k] for k in ("stitches", "trims", "jumps", "stops", "size_mm", "max_stitch", "foam_pause_before_stop")}, f"{f_['secs']}s", flush=True)
        json.dump(res, open(rp, "w"), default=float, indent=1)
    if "nosplit" not in sys.argv:
        for wm in (70.0, 55.0, 40.0):
            sp = split_clip_wide(vis, FRAME, whole_max=wm)
            if all(sp["fits"].values()): break
        marks = dst2.split_marks(sp, ext=12.0)
        names = {(0, 0): "S1", (0, 1): "S2", (1, 0): "S1b", (1, 1): "S2b"}
        if sp["sx"] is not None:
            names = {(0, 0): "S1_top-left", (1, 0): "S2_top-right", (0, 1): "S3_bottom-left", (1, 1): "S4_bottom-right"}
        elif sp["sy"] is not None: names = {(0, 0): "S1_top", (0, 1): "S2_bottom"}
        else: names = {(0, 0): "S1_single"}
        spl = dict(frame=FRAME, sx=sp["sx"], sy=sp["sy"], cut_mm=sp["cut"], whole_max=wm, sections={})
        if len(sp["secs"]) > 1:
            for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])):
                sv = sp["secs"][key]
                if not sv: continue
                t = time.time(); stops, n0 = stops_for(sv)
                bb = dst2.bounds_of([r["geom"] for r in sv] + [Point(m).buffer(6) for m in marks[key]])
                cc = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
                pat, st = dst2.make_pattern(sv, stops, cc, reg_marks=marks[key])
                base = f"{OUT}/splits/{PREFIX}_{P}_{size}_{names[key]}"; os.makedirs(os.path.dirname(base), exist_ok=True)
                dst2.write(reg_in_first_colour(pat), base); dst2.render(base, base + "_preview.png", bg=(25, 28, 36), s=0.5)
                r = record(base, stops, dict(bbox=bb, origin=cc, marks=marks[key], secs=round(time.time()-t)), basting=True)
                r["fits"] = r["size_mm"][0] <= FRAME[0] - 16 and r["size_mm"][1] <= FRAME[1] - 16
                spl["sections"][names[key]] = r
                print(size, P, names[key], {k: r[k] for k in ("stitches", "trims", "stops", "size_mm", "fits")}, flush=True)
        res["splits"] = spl; json.dump(res, open(rp, "w"), default=float, indent=1)
print("DONE", size, which, flush=True)
