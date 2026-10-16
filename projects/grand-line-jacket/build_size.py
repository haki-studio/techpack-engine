"""Per-size production stitch files for the two front pieces (FR, FL): full file + hoop splits for the factory frame.
usage: python3 build_size.py SIZE [FR|FL ...] [nosplit] [splitsonly]
Every number written to result_<piece>.json is read back from the DST (readback.dst, LESSONS B8/B20):
stitches, trims, jumps, stops, per-stop counts, max stitch, size. 'sews' per stop = the region codes the build put in it."""
import glcore
import pickle, json, sys, time, os, math, inspect
import numpy as np
from shapely.ops import unary_union
from shapely.geometry import Point
import tech, readback, factory
dst2 = glcore.patch_dst2()

size = sys.argv[1]
which = [a for a in sys.argv[2:] if a in glcore.PIECES] or list(glcore.PIECES)
D = pickle.load(open(f"front_{size}.pkl", "rb"))
OUT = f"out/01_front-scene/{size}"; os.makedirs(OUT, exist_ok=True)
FRAME = tuple(float(v) for v in factory.largest_frame(factory.load()))

# split_clip with a wider split-line search (engine searches 40-60 % of the height only): every frame-legal y is tried
_src = inspect.getsource(dst2.split_clip).replace(
    "ys = np.linspace(b[1] + (b[3]-b[1])*0.40, b[1] + (b[3]-b[1])*0.60, 21) if ny == 2 else [None]",
    "ys = np.linspace(b[1] + (b[3]-b[1])*0.12, b[1] + (b[3]-b[1])*0.88, 77) if ny == 2 else [None]")
assert "0.88, 77" in _src, "engine split_clip changed: update the y-search patch"
_ns = dict(vars(dst2)); exec(_src, _ns); split_clip_wide = _ns["split_clip"]

def cap_stitches(pat, mx=7.4):
    """belt + braces for LESSONS B17 (the engine now splits at 7.4 too)"""
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

def stops_for(vis):
    st = tech.stops(vis); n0 = len(st); return dst2.merge_stops(st), n0

def sews(stops, basting=False):
    """what each colour stop sews: region codes + stitch types (underlay/edge runs are part of every fill object)"""
    out = [dict(col="#00A3FF", codes=["REG"], types=["basting crosses"])] if basting else []
    for s in stops:
        codes = sorted({tech.rule_for(r["grp"]) for r in s["regions"]})
        types = sorted({r["st"] for r in s["regions"]})
        out.append(dict(col=s["col"], codes=codes, types=types, objects=len(s["regions"])))
    return out

def record(base, stops, extra, basting=False):
    rb = readback.dst(base + ".dst")
    info = sews(stops, basting)
    assert len(info) == rb["stops"], f"{base}: {len(info)} stops built vs {rb['stops']} in the DST"
    for ps, si in zip(rb["per_stop"], info): ps.update(si)
    rb.update(extra, file=base); return rb

for P in which:
    rp = f"{OUT}/result_{P}.json"
    res = json.load(open(rp)) if os.path.exists(rp) else {}
    vis = dst2.merge_colours(D[P])
    if "splitsonly" not in sys.argv:
        t = time.time()
        ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
        stops, n0 = stops_for(vis); pat, st = dst2.make_pattern(vis, stops, c)
        base = f"{OUT}/HAKI_GRLN_01_front-scene_{P}_{size}"
        dst2.write(cap_stitches(pat), base); dst2.render(base, base + "_preview.png", s=0.5)
        res["full"] = record(base, stops, dict(origin=c, art_box=ub, stops_before_merge=n0, secs=round(time.time()-t),
                                               build_trims_by_code=sorted(st.get("by", {}).items(), key=lambda kv: -kv[1])[:10]))
        f_ = res["full"]
        print(size, P, {k: f_[k] for k in ("stitches", "trims", "jumps", "stops", "size_mm", "max_stitch")}, f"{f_['secs']}s", flush=True)
        json.dump(res, open(rp, "w"), default=float, indent=1)
    if "nosplit" not in sys.argv:
        for wm in (70.0, 55.0, 40.0):
            sp = split_clip_wide(vis, FRAME, whole_max=wm)
            if all(sp["fits"].values()): break
        marks = dst2.split_marks(sp, ext=4.0)
        names = {(0, 0): "S1_top", (0, 1): "S2_bottom", (1, 0): "S1b_right", (1, 1): "S2b_right"}
        spl = dict(frame=FRAME, sx=sp["sx"], sy=sp["sy"], cut_mm=sp["cut"], whole_max=wm, sections={})
        for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])):
            sv = sp["secs"][key]; t = time.time(); stops, n0 = stops_for(sv)
            bb = unary_union([r["geom"] for r in sv] + [Point(m).buffer(6) for m in marks[key]]).bounds
            cc = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
            pat, st = dst2.make_pattern(sv, stops, cc, reg_marks=marks[key])
            base = f"{OUT}/splits/HAKI_GRLN_01_front-scene_{P}_{size}_{names[key]}"; os.makedirs(os.path.dirname(base), exist_ok=True)
            dst2.write(cap_stitches(pat), base); dst2.render(base, base + "_preview.png", s=0.5)
            r = record(base, stops, dict(bbox=bb, origin=cc, marks=marks[key], secs=round(time.time()-t)), basting=True)
            r["fits"] = r["size_mm"][0] <= FRAME[0] - 16 and r["size_mm"][1] <= FRAME[1] - 16
            spl["sections"][names[key]] = r
            print(size, P, names[key], {k: r[k] for k in ("stitches", "trims", "stops", "size_mm", "fits")}, "split y", round(sp["sy"] or 0, 1), flush=True)
        res["splits"] = spl; json.dump(res, open(rp, "w"), default=float, indent=1)
print("DONE", size, which, flush=True)
