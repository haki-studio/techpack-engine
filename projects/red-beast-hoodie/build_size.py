"""Per-size production stitch files for the four embroidered pieces (FR, FL fronts = 01; SR, SL sleeves = 02):
full file + hoop splits for the factory's largest frame (factory.json).
usage: python3 build_size.py SIZE [FR FL SR SL] [nosplit] [splitsonly]
Every number written to result_<piece>.json is read back from the DST (readback.dst, LESSONS B8/B20)."""
import rbcore
import pickle, json, sys, time, os, math, inspect
from shapely.ops import unary_union
from shapely.geometry import Point
import tech, readback, factory
dst2 = rbcore.patch_dst2()

size = sys.argv[1]
which = [a for a in sys.argv[2:] if a in rbcore.PIECES] or list(rbcore.PIECES)
D = pickle.load(open(f"art_{size}.pkl", "rb"))
FRAME = tuple(float(v) for v in factory.largest_frame(factory.load()))
MAXC = factory.max_threads()

# split_clip with a wider split-line search (engine searches 40-60 % of the height only; Grand Line ENGINE_NOTES 8)
_src = inspect.getsource(dst2.split_clip)
for a in ("ys", "xs"):
    ax = "1" if a == "ys" else "0"; ax2 = "3" if a == "ys" else "2"
    old = f"{a} = np.linspace(b[{ax}] + (b[{ax2}]-b[{ax}])*0.40, b[{ax}] + (b[{ax2}]-b[{ax}])*0.60, 21)"
    assert old in _src, "engine split_clip changed: update the search patch"
    _src = _src.replace(old, f"{a} = np.linspace(b[{ax}] + (b[{ax2}]-b[{ax}])*0.12, b[{ax}] + (b[{ax2}]-b[{ax}])*0.88, 77)")
_ns = dict(vars(dst2)); exec(_src, _ns); _split_clip = _ns["split_clip"]
# Rev B (review item 10): the split line must avoid the cream cords + teeth - a cut cord shows as a step when the two
# hoopings meet. Cut length through cream counts CREAM_W times, so the search moves the line off the outline/teeth.
CREAM_W = 40.0
_cut0 = dst2.cut_length
def split_clip_wide(vis, frame, **kw):
    import shapely
    cg = [p for r in vis if r["col"] in ("rb_cream", "rb_white") for p in dst2.polys(r["geom"])]
    ct = shapely.STRtree(cg) if cg else None
    def cut_w(GS, line, tree=None):
        return _cut0(GS, line, tree) + (CREAM_W*_cut0(cg, line, ct) if cg else 0.0)
    _ns["cut_length"] = cut_w
    try: return _split_clip(vis, frame, **kw)
    finally: _ns["cut_length"] = _cut0

def cream_cut(vis, sy):
    from shapely.geometry import LineString
    if sy is None: return 0.0
    u = [p for r in vis if r["col"] in ("rb_cream", "rb_white") for p in dst2.polys(r["geom"])]
    ln = LineString([(-1e4, sy), (1e4, sy)])
    return round(sum(p.intersection(ln).length for p in u), 1)

REG_COL = "rb_crimson"
def reg_in_dark_thread(pat):
    """factory limit (12 colours incl. registration, B5): the crosses sew as their own first stop in Deep crimson (a thread
    of this jacket, dark on washed black, never cream - review item 10). Distinct colours per file stay <= 5."""
    if len(pat.threadlist) < 2 or pat.threadlist[0].catalog_number != "WSB": return pat
    import specbase as SB_
    from motifs2 import PAL as PAL_
    th = pat.threadlist[0]; th.set_hex_color(HEXC[REG_COL]); pn = SB_.TH[REG_COL]["polyneon"]
    th.description = f"{PAL_[REG_COL][1]} - REGISTRATION crosses, pick out after the last hooping"; th.catalog_number = pn[0]; th.brand = "Madeira Polyneon"
    return pat
from motifs2 import HEX as HEXC

def stops_for(vis):
    st = tech.stops(vis); n0 = len(st); return dst2.merge_stops(st), n0

def sews(stops, basting=False):
    out = [dict(col=REG_COL, codes=["REG crosses (basting, remove)"], types=["run"], objects=0)] if basting else []
    for s in stops:
        out.append(dict(col=s["col"], codes=sorted({tech.rule_for(r["grp"]) for r in s["regions"]}),
                        types=sorted({r["st"] for r in s["regions"]}), objects=len(s["regions"])))
    return out

def record(base, stops, extra, basting=False):
    rb = readback.dst(base + ".dst"); rb["threads"] = factory.check_threads(base + ".pes")
    info = sews(stops, basting)
    assert len(info) == rb["stops"], f"{base}: {len(info)} stops built vs {rb['stops']} in the DST"
    for ps, si in zip(rb["per_stop"], info): ps.update(si)
    assert rb["max_stitch"] <= 7.5, f"{base}: max stitch {rb['max_stitch']}"
    rb.update(extra, file=base); return rb

for P in which:
    OUT = rbcore.outdir(P, size); os.makedirs(OUT, exist_ok=True)
    rp = f"{OUT}/result_{P}.json"
    res = json.load(open(rp)) if os.path.exists(rp) else {}
    vis = dst2.merge_colours(D[P])
    if not vis: print(size, P, "no art"); continue
    if "splitsonly" not in sys.argv:
        t = time.time()
        ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
        stops, n0 = stops_for(vis); pat, st = dst2.make_pattern(vis, stops, c)
        base = f"{OUT}/{rbcore.fname(P, size)}"
        dst2.write(pat, base); dst2.render(base, base + "_preview.png", bg=(43, 48, 57), s=0.5)
        ex = dst2.exposed_travel(stops, st["runs"])
        res["full"] = record(base, stops, dict(origin=c, art_box=ub, stops_before_merge=n0, secs=round(time.time()-t),
                                               exposed_runs_gt1mm=sum(1 for v in ex if v > 1.0),
                                               trim_why=st.get("why", {}),
                                               build_trims_by_code=sorted(st.get("by", {}).items(), key=lambda kv: -kv[1])[:10]))
        f_ = res["full"]
        print(size, P, {k: f_[k] for k in ("stitches", "trims", "jumps", "stops", "size_mm", "max_stitch", "threads")}, f"{f_['secs']}s", flush=True)
        json.dump(res, open(rp, "w"), default=float, indent=1)
    if "nosplit" not in sys.argv:
        ub = unary_union([r["geom"] for r in vis]).bounds
        if ub[2]-ub[0] <= FRAME[0] - 16 - 2*18.5 and ub[3]-ub[1] <= FRAME[1] - 16 - 2*18.5:
            res["splits"] = dict(frame=FRAME, sections={}, note="fits one hooping"); json.dump(res, open(rp, "w"), default=float, indent=1)
            print(size, P, "one hooping", flush=True); continue
        for wm in (70.0, 55.0, 40.0):
            sp = split_clip_wide(vis, FRAME, whole_max=wm)
            if all(sp["fits"].values()): break
        marks = dst2.split_marks(sp)
        names = {(0, 0): "S1_top", (0, 1): "S2_bottom", (1, 0): "S1b_right", (1, 1): "S2b_right"}
        spl = dict(frame=FRAME, sx=sp["sx"], sy=sp["sy"], cut_mm=sp["cut"], cream_cut_mm=cream_cut(vis, sp["sy"]), whole_max=wm, sections={})
        for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])):
            sv = sp["secs"][key]; t = time.time(); stops, n0 = stops_for(sv)
            bb = unary_union([r["geom"] for r in sv] + [Point(m).buffer(6) for m in marks[key]]).bounds
            cc = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
            pat, st = dst2.make_pattern(sv, stops, cc, reg_marks=marks[key])
            base = f"{OUT}/splits/{rbcore.fname(P, size, names[key])}"; os.makedirs(os.path.dirname(base), exist_ok=True)
            dst2.write(reg_in_dark_thread(pat), base); dst2.render(base, base + "_preview.png", bg=(43, 48, 57), s=0.5)
            r = record(base, stops, dict(bbox=bb, origin=cc, marks=marks[key], secs=round(time.time()-t)), basting=True)
            r["fits"] = r["size_mm"][0] <= FRAME[0] - 16 and r["size_mm"][1] <= FRAME[1] - 16
            spl["sections"][names[key]] = r
            print(size, P, names[key], {k: r[k] for k in ("stitches", "trims", "stops", "size_mm", "fits")}, "split y", round(sp["sy"] or 0, 1), flush=True)
        res["splits"] = spl; json.dump(res, open(rp, "w"), default=float, indent=1)
print("DONE", size, which, flush=True)
