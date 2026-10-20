"""Per-size production stitch files for the five wave pieces (BK, FR, FL, SR, SL): full file + hoop splits for the factory frame.
usage: python3 build_size.py SIZE [BK|FR|FL|SR|SL ...] [nosplit] [splitsonly]
Every number written to result_<piece>.json is read back from the DST (readback.dst, LESSONS B8/B20):
stitches, trims, jumps, stops, per-stop counts, max stitch, size. 'sews' per stop = the region codes the build put in it."""
import wavecore as glcore
import pickle, json, sys, time, os, math, inspect
import numpy as np
from shapely.ops import unary_union
from shapely.geometry import Point
import tech, readback, factory
dst2 = glcore.patch_dst2()

size = sys.argv[1]
which = [a for a in sys.argv[2:] if a in glcore.PIECES] or list(glcore.PIECES)
D = pickle.load(open(f"art_{size}.pkl", "rb"))
OUT = f"out/01_wave/{size}"; os.makedirs(OUT, exist_ok=True)
FRAME = tuple(float(v) for v in factory.largest_frame(factory.load()))

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

TINY_MM2 = 120.0
def merge_tiny(stops, clear=0.4):
    """review item 10: a colour stop with very little in it (< TINY_MM2 of art) costs a colour change for a few dozen
    stitches. Its regions move to another stop of the same colour - an earlier one if nothing of another colour sewn in
    between touches them (clear mm), else a later one if nothing sewn in between touches them (then the move cannot put
    them under or over anything). Same stitches, same order where they overlap anything; only the stop changes."""
    import shapely
    def area(s): return sum(r["geom"].area for r in s["regions"])
    changed = True
    while changed:
        changed = False
        for j, s in enumerate(stops):
            if area(s) >= TINY_MM2: continue
            U = unary_union([r["geom"] for r in s["regions"]]).buffer(clear)
            def free(a, b):    # nothing of another colour in stops a..b-1 touches U
                return all(not (stops[i]["col"] != s["col"] and any(r["geom"].intersects(U) for r in stops[i]["regions"])) for i in range(a, b))
            cand = [i for i in range(j) if stops[i]["col"] == s["col"] and free(i + 1, j)]
            cand += [k for k in range(j + 1, len(stops)) if stops[k]["col"] == s["col"] and free(j + 1, k)]
            if not cand: continue
            k = cand[0]; stops[k] = dict(stops[k], regions=stops[k]["regions"] + s["regions"]); del stops[j]; changed = True; break
    return stops

def stops_for(vis):
    st = tech.stops(vis); n0 = len(st); return merge_tiny(dst2.merge_stops(st)), n0

def sews(stops, basting=False):
    """what each colour stop sews: region codes + stitch types (underlay/edge runs are part of every fill object)"""
    out = []
    for s in stops:
        codes = sorted({tech.rule_for(r["grp"]) for r in s["regions"]})
        types = sorted({r["st"] for r in s["regions"]})
        out.append(dict(col=s["col"], codes=codes, types=types, objects=len(s["regions"])))
    if basting and out: out[0]["codes"] = ["REG crosses"] + out[0]["codes"]
    return out

def record(base, stops, extra, basting=False):
    rb = readback.dst(base + ".dst"); rb["threads"] = factory.check_threads(base + ".pes")
    info = sews(stops, basting)
    assert len(info) == rb["stops"], f"{base}: {len(info)} stops built vs {rb['stops']} in the DST"
    for ps, si in zip(rb["per_stop"], info): ps.update(si)
    rb.update(extra, file=base); return rb

PROF = factory.load()
FOAM_GRPS = ("FM", "FM-loop", "FM-curl")
def hoop_plan(P, ub):
    """factory answers 19 Oct (factory.json): fronts one hooping (340 x 505 confirmed); back two hoopings side by side
    (690 x 575 confirmed: each <= 345 x 575); sleeves split to fit the 400 x 450 frame (one hooping if a sleeve fits)"""
    w, h = ub[2] - ub[0], ub[3] - ub[1]
    one = PROF.get("single_hooping_confirmed_mm", {}).get("front")
    if P in ("FR", "FL") and one and w <= one[0] and h <= one[1]: return ("one", None)
    if P == "BK" and PROF.get("two_hoopings_confirmed_mm", {}).get("back"):
        bw, bh = PROF["two_hoopings_confirmed_mm"]["back"]; return ("split", (bw / 2 + 16.0, bh + 16.0 + 40.0))
    if w <= FRAME[0] - 16 and h <= FRAME[1] - 16: return ("one", None)
    return ("split", FRAME)

def write_set(sv, origin, base, reg=None, primary=True, plan=False):
    """Rev B fix round (20 Oct, LESSONS B33): the PRIMARY file is all lockstitch - foam as padded tatami, rows along the curl
    (A16) + spiral curl cord + loop spiral (the Rev B 'alt_padded' set). Chenille has no confirmed machine format
    (factory.json chenille_format = null), so it is a PLAN (json + preview, chenille.plan), never a machine file."""
    stops, n0 = stops_for(sv); pat, st = dst2.make_pattern(sv, stops, origin, reg_marks=reg)
    pat = cap_stitches(reg_in_first_colour(pat) if reg else pat)
    dst2.write(pat, base); dst2.render(base, base + "_preview.png", bg=(39, 47, 67), s=0.5)
    out = dict(stops=stops, n0=n0, st=st)
    if plan:
        foam = [r for r in sv if r["grp"] == "FM"]; cords = [r for r in sv if r["grp"] == "FM-curl"]
        if foam:
            import chenille
            d = os.path.join(os.path.dirname(base), "chenille_plan"); os.makedirs(d, exist_ok=True)
            out["chenille_plan"] = chenille.plan(foam, cords, origin, os.path.join(d, os.path.basename(base) + "_CHENILLE-PLAN"))
    return out

for P in which:
    rp = f"{OUT}/result_{P}.json"
    res = {}
    vis = dst2.merge_colours(D[P])
    ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
    plan, frame = hoop_plan(P, ub)
    for variant, primary in (("primary", True),):
        sub = ""; os.makedirs(f"{OUT}/{sub}", exist_ok=True)
        t = time.time(); base = f"{OUT}/{sub}HAKI_WAVE_01_wave_{P}_{size}"
        w = write_set(vis, c, base, primary=primary, plan=True); stops = w["stops"]
        ex = dst2.exposed_travel(stops, w["st"].get("runs", []))
        full = record(base, stops, dict(origin=c, art_box=ub, stops_before_merge=w["n0"], secs=round(time.time()-t), satin_guard=dict(glcore.COV_LOG),
                                        exposed_travel=dict(runs_over_1mm=sum(1 for e in ex if e > 1.0), runs_over_2mm=sum(1 for e in ex if e > 2.0), max_mm=round(max(ex), 1) if ex else 0.0),
                                        build_trims_by_code=sorted(w["st"].get("by", {}).items(), key=lambda kv: -kv[1])[:10]))
        if "chenille_plan" in w: full["chenille_plan"] = w["chenille_plan"]
        print(size, P, variant, {k: full[k] for k in ("stitches", "trims", "stops", "size_mm", "max_stitch")}, ("chenille plan " + str({k: w["chenille_plan"][k] for k in ("paths", "needle_points", "length_m")})) if "chenille_plan" in w else "", flush=True)
        R = dict(full=full, plan=plan)
        if plan == "split":
            for wm in (70.0, 55.0, 40.0):
                sp = split_clip_wide(vis, frame, whole_max=wm)
                if all(sp["fits"].values()): break
            import glob as _g
            for fn in _g.glob(f"{OUT}/{sub}splits/HAKI_WAVE_01_wave_{P}_{size}_*"): os.remove(fn)
            marks = dst2.split_marks(sp, ext=4.0)
            keys = [k for k in sorted(sp["secs"], key=lambda k: (k[1], k[0])) if sp["secs"][k]]
            def nm_(k):
                i, j = k; pos = ("top" if sp["sy"] is not None and j == 0 else "bottom" if sp["sy"] is not None else "") + \
                                ("-left" if sp["sx"] is not None and i == 0 else "-right" if sp["sx"] is not None else "")
                return f"S{keys.index(k) + 1}_{pos.strip('-')}"
            names = {k: nm_(k) for k in keys}
            spl = dict(frame=frame, sx=sp["sx"], sy=sp["sy"], xs=[sp["sx"]] if sp["sx"] is not None else [], ys=[sp["sy"]] if sp["sy"] is not None else [],
                       cut_mm=sp["cut"], whole_max=wm, method="split_clip", sections={})
            import absorb
            keys, alog = absorb.absorb_tiny(sp["secs"], marks, keys, frame)
            if alog:
                names = {k: f"S{i + 1}_{names[k].split('_', 1)[1]}" if "_" in names[k] else f"S{i + 1}" for i, k in enumerate(keys)}
            spl["absorbed"] = alog
            for key in keys:
                sv = sp["secs"][key]; t = time.time()
                bb = unary_union([r["geom"] for r in sv] + [Point(m).buffer(6) for m in marks[key]]).bounds
                cc = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
                bs = f"{OUT}/{sub}splits/HAKI_WAVE_01_wave_{P}_{size}_{names[key]}"; os.makedirs(os.path.dirname(bs), exist_ok=True)
                w = write_set(sv, cc, bs, reg=marks[key], primary=primary)
                r = record(bs, w["stops"], dict(bbox=bb, origin=cc, marks=marks[key], secs=round(time.time()-t)), basting=True)
                fw, fh = frame
                r["fits"] = (r["size_mm"][0] <= fw - 16 and r["size_mm"][1] <= fh - 16) or (r["size_mm"][1] <= fw - 16 and r["size_mm"][0] <= fh - 16)
                spl["sections"][names[key]] = r
                print(size, P, variant, names[key], {k: r[k] for k in ("stitches", "trims", "stops", "size_mm", "fits")}, flush=True)
            R["splits"] = spl; R["hoopings"] = len(spl["sections"])
        else:
            R["hoopings"] = 1
        if primary: res.update(R)
        else: res["alt_padded"] = R
    json.dump(res, open(rp, "w"), default=float, indent=1)
print("DONE", size, which, flush=True)
