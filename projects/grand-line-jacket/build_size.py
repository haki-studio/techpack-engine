"""Per-size production stitch files for the two front pieces (FR, FL): full file + 360 x 360 hoop splits.
usage: python3 build_size.py SIZE [FR|FL ...] [nosplit] [splitsonly]
-> out/01_front-scene/<size>/HAKI_GRLN_01_front-scene_<piece>_<size>.{dst,pes,_preview.png}
   out/01_front-scene/<size>/splits/..._S1_top / _S2_bottom ...   + result_<piece>.json (counts read back from the files)"""
import glcore
import pickle, json, sys, time, os
from shapely.ops import unary_union
from shapely.geometry import Point
import tech
dst2 = glcore.patch_dst2()

size = sys.argv[1]
which = [a for a in sys.argv[2:] if a in glcore.PIECES] or list(glcore.PIECES)
D = pickle.load(open(f"front_{size}.pkl", "rb"))
OUT = f"out/01_front-scene/{size}"; os.makedirs(OUT, exist_ok=True)
FRAME = (360.0, 360.0)

def stops_for(vis):
    st = tech.stops(vis); n0 = len(st); return dst2.merge_stops(st), n0

for P in which:
    rp = f"{OUT}/result_{P}.json"
    res = json.load(open(rp)) if os.path.exists(rp) else {}
    vis = dst2.merge_colours(D[P])
    if "splitsonly" not in sys.argv:
        t = time.time()
        ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
        stops, n0 = stops_for(vis); pat, st = dst2.make_pattern(vis, stops, c)
        base = f"{OUT}/HAKI_GRLN_01_front-scene_{P}_{size}"
        dst2.write(pat, base); v = dst2.verify(base); dst2.render(base, base + "_preview.png", s=0.5)
        res["full"] = dict(v, trims_cmd=st["trims"], travel=st["travel"], jumps_cmd=st["jumps"], stops=len(stops), stops_before_merge=n0,
                           centre=c, art_box=ub, file=base, colours=[s["col"] for s in stops], secs=round(time.time()-t),
                           worst=sorted(st.get("by", {}).items(), key=lambda kv: -kv[1])[:10])
        print(size, P, {k: res["full"][k] for k in ("stitches", "trims_cmd", "trims", "jumps", "stops", "stops_before_merge", "size", "max_stitch", "secs")}, flush=True)
        json.dump(res, open(rp, "w"), default=float, indent=1)
    if "nosplit" not in sys.argv:
        for wm in (70.0, 55.0, 40.0):
            sp = dst2.split_clip(vis, FRAME, whole_max=wm)
            if all(sp["fits"].values()): break
        marks = dst2.split_marks(sp)
        names = {(0, 0): "S1_top", (0, 1): "S2_bottom", (1, 0): "S1b_right", (1, 1): "S2b_right"}
        spl = dict(frame=FRAME, sx=sp["sx"], sy=sp["sy"], cut_mm=sp["cut"], whole_max=wm, sections={})
        for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])):
            sv = sp["secs"][key]; t = time.time(); stops, n0 = stops_for(sv)
            bb = unary_union([r["geom"] for r in sv] + [Point(m).buffer(6) for m in marks[key]]).bounds
            cc = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
            pat, st = dst2.make_pattern(sv, stops, cc, reg_marks=marks[key])
            base = f"{OUT}/splits/HAKI_GRLN_01_front-scene_{P}_{size}_{names[key]}"; os.makedirs(os.path.dirname(base), exist_ok=True)
            dst2.write(pat, base); v = dst2.verify(base); dst2.render(base, base + "_preview.png", s=0.5)
            spl["sections"][names[key]] = dict(v, trims_cmd=st["trims"], stops=len(stops) + 1, bbox=bb, centre=cc, marks=marks[key], file=base,
                                               fits=(bb[2]-bb[0] <= FRAME[0]-16 and bb[3]-bb[1] <= FRAME[1]-16), secs=round(time.time()-t))
            print(size, P, names[key], {k: spl["sections"][names[key]][k] for k in ("stitches", "trims_cmd", "stops", "size", "fits", "secs")}, flush=True)
        res["splits"] = spl; json.dump(res, open(rp, "w"), default=float, indent=1)
print("DONE", size, which, flush=True)
