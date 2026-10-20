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
HZ_S = 199.0 * glcore.GRADE[size][1]           # horizon of this size (scene.HORIZON scaled about the CF neck point)

# split_clip with a wider split-line search (engine searches 40-60 % of the height only): every frame-legal y is tried
_src = inspect.getsource(dst2.split_clip).replace(
    "ys = np.linspace(b[1] + (b[3]-b[1])*0.40, b[1] + (b[3]-b[1])*0.60, 21) if ny == 2 else [None]",
    "ys = np.linspace(b[1] + (b[3]-b[1])*0.30, b[1] + (b[3]-b[1])*0.88, 59) if ny == 2 else [None]")
assert "0.88, 59" in _src, "engine split_clip changed: update the y-search patch"
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

def reg_in_first_colour(pat):
    """factory limit (12 colours incl. registration): drop the dedicated basting thread; the crosses sew at the start of
    stop 1 in stop 1's thread (long 4 mm stitches, picked out after the last hooping)"""
    import pyembroidery as pe
    if len(pat.threadlist) < 2 or pat.threadlist[0].catalog_number != "WSB": return pat
    pat.threadlist.pop(0)
    for i, (x, y, c) in enumerate(pat.stitches):
        if (c & pe.COMMAND_MASK) == pe.COLOR_CHANGE: del pat.stitches[i]; break
    return pat

def trim_exposed(pat, stops, runs, origin, limit=2.0, forgive=0.8, tol=0.3):
    """review C2: a travel run with more than `limit` mm on bare fabric (same measure as dst2.exposed_travel) is replaced by
    TRIM + JUMP. Runs are found in the stitch stream by their exact coordinates, in emission order."""
    import pyembroidery as pe
    from shapely.strtree import STRtree
    from shapely.geometry import LineString
    from shapely.ops import substring
    gs, ix = [], []
    for i, s in enumerate(stops):
        for r in s["regions"]:
            if r["st"] in dst2.FILL_ST or r["st"] == "bean":
                for p in dst2.polys(r["geom"]): gs.append(p); ix.append(i)
    tree = STRtree(gs); ix = np.array(ix); bad = []
    for si, pts in runs:
        ln = LineString(pts); e = 0.0
        if ln.length > 2*forgive:
            ln2 = substring(ln, forgive, ln.length - forgive)
            hits = [h for h in tree.query(ln2.buffer(tol), predicate="intersects") if ix[h] >= si]
            bare = ln2.difference(unary_union([gs[h].buffer(tol, 4) for h in hits])) if hits else ln2
            if not bare.is_empty: e = max(g.length for g in getattr(bare, "geoms", [bare]))
        sea = stops[si]["col"] in ("gl_deep", "gl_teal", "gl_tealt", "gl_foam")
        # Rev E3: a cloud / islet thread travelling over the SEA (below the horizon) shows on the dashes just the same
        over_sea = min(p_[1] for p_ in pts) > HZ_S + 1.0
        bad.append(e > (0.8 if (sea or over_sea) else limit))            # Rev D item 10: in the sea any visible connector > 0.8 mm is trimmed
    import pyembroidery as pe
    ox, oy = origin; S = pat.stitches; out = []; k = 0; ri = 0; n_fix = 0; U = dst2.U
    def at(k, tr):
        """the whole run must match stitch by stitch (a first-stitch-only match once swallowed a COLOR_CHANGE)"""
        if k + len(tr) > len(S): return False
        for i, q in enumerate(tr):
            x_, y_, c_ = S[k + i]
            if (c_ & pe.COMMAND_MASK) != pe.STITCH or abs(x_ - (q[0]-ox)*U) > 0.05 or abs(y_ - (q[1]-oy)*U) > 0.05: return False
        return True
    while k < len(S):
        while ri < len(runs) and not runs[ri][1][1:-1]: ri += 1
        if ri < len(runs) and at(k, runs[ri][1][1:-1]):
            tr = runs[ri][1][1:-1]
            if bad[ri]:
                nx, ny = (runs[ri][1][-1][0]-ox)*U, (runs[ri][1][-1][1]-oy)*U
                out.append([nx, ny, pe.TRIM]); out.append([nx, ny, pe.JUMP]); n_fix += 1
            else:
                out.extend(S[k:k+len(tr)])
            k += len(tr); ri += 1; continue
        out.append(S[k]); k += 1
    n_cc = lambda L: sum(1 for x_, y_, c_ in L if (c_ & pe.COMMAND_MASK) == pe.COLOR_CHANGE)
    assert n_cc(out) == n_cc(S), "trim_exposed changed the number of colour changes"
    pat.stitches = out
    return pat, dict(runs=len(runs), exposed_over_limit=int(sum(bad)), trimmed=n_fix)

def stops_for(vis):
    st = tech.stops(vis); n0 = len(st); return dst2.merge_stops(st), n0

def sews(stops, basting=False):
    """what each colour stop sews: region codes + stitch types (underlay/edge runs are part of every fill object)"""
    out = []
    for s in stops:
        codes = sorted({tech.rule_for(r["grp"]) for r in s["regions"]})
        types = sorted({r["st"] for r in s["regions"]})
        out.append(dict(col=s["col"], codes=codes, types=types, objects=len(s["regions"])))
    if basting and out: out[0]["codes"] = ["REG crosses"] + out[0]["codes"]
    return out

def record(base, stops, extra, basting=False, pat=None):
    rb = readback.dst(base + ".dst"); rb["threads"] = factory.check_threads(base + ".pes")
    info = sews(stops, basting)
    # pair build stops with DST stops by the stitches each build stop actually emitted: a stop with 0 stitches has no
    # colour change in the written DST, so pairing by position or by thread list shifts every later label (Rev D bug)
    import pyembroidery as pe
    counts = [0]
    for x, y, c in pat.stitches:
        k = c & pe.COMMAND_MASK
        if k == pe.COLOR_CHANGE: counts.append(0)
        elif k == pe.STITCH: counts[-1] += 1
    if basting and len(counts) == len(info) + 1: counts = [counts[0] + counts[1]] + counts[2:]   # crosses sew at the start of stop 1
    assert len(counts) == len(info), f"{base}: {len(counts)} colour segments in the pattern vs {len(info)} build stops"
    live = [s for s, n in zip(info, counts) if n > 0]
    assert len(live) == rb["stops"], f"{base}: {len(live)} non-empty build stops vs {rb['stops']} DST stops"
    for ps, si, n in zip(rb["per_stop"], live, [n for n in counts if n > 0]):
        assert abs(ps["stitches"] - n) <= 10*(ps["trims"] + 2) + 0.06*n, f"{base}: stop {ps['stop']} DST {ps['stitches']} vs build {n}"
        ps.update(si)
    rb.update(extra, file=base); return rb

for P in which:
    rp = f"{OUT}/result_{P}.json"
    res = json.load(open(rp)) if os.path.exists(rp) else {}
    vis = dst2.merge_colours(D[P])
    if "splitsonly" not in sys.argv:
        t = time.time()
        ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
        stops, n0 = stops_for(vis); pat, st = dst2.make_pattern(vis, stops, c)
        pat, tfix = trim_exposed(pat, stops, st.get("runs", []), c)
        base = f"{OUT}/HAKI_GRLN_01_front-scene_{P}_{size}"
        dst2.write(cap_stitches(pat), base); dst2.render(base, base + "_preview.png", s=0.5)
        res["full"] = record(base, stops, pat=pat, extra=dict(origin=c, art_box=ub, stops_before_merge=n0, secs=round(time.time()-t), exposed_travel=tfix,
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
            pat, tfix = trim_exposed(pat, stops, st.get("runs", []), cc)
            base = f"{OUT}/splits/HAKI_GRLN_01_front-scene_{P}_{size}_{names[key]}"; os.makedirs(os.path.dirname(base), exist_ok=True)
            dst2.write(cap_stitches(reg_in_first_colour(pat)), base); dst2.render(base, base + "_preview.png", s=0.5)
            r = record(base, stops, pat=pat, basting=True, extra=dict(bbox=bb, origin=cc, marks=marks[key], secs=round(time.time()-t), exposed_travel=tfix))
            r["fits"] = r["size_mm"][0] <= FRAME[0] - 16 and r["size_mm"][1] <= FRAME[1] - 16
            spl["sections"][names[key]] = r
            print(size, P, names[key], {k: r[k] for k in ("stitches", "trims", "stops", "size_mm", "fits")}, "split y", round(sp["sy"] or 0, 1), flush=True)
        res["splits"] = spl; json.dump(res, open(rp, "w"), default=float, indent=1)
print("DONE", size, which, flush=True)
