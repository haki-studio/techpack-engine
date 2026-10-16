"""Per-size v3 stitch files for 01 back + sleeve wrap (+ 360² splits). usage: python3 build_size.py SIZE [nosplit]"""
import pickle, json, sys, time, os
from shapely.ops import unary_union
from shapely.geometry import Point
import dst2, tech

size = sys.argv[1]; D = pickle.load(open(f"back_{size}.pkl", "rb")); info = D["info"]
OUT = f"out/01_back-scene/v3_by-size/{size}"; os.makedirs(OUT, exist_ok=True)
def prep(vis):
    vis = dst2.merge_colours(vis)
    return [dict(r, layer=4.55) if tech.rule_for(r["grp"]) == "BD-hl" else r for r in vis]
def stops_for(vis):
    st = tech.stops(vis, tech.STITCH_LAYER); n0 = len(st); return dst2.merge_stops(st), n0
res = {"info": {k: v for k, v in info.items()}}
for k in ("back", "sleeve"):
    t = time.time(); vis = prep(D[k])
    ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
    stops, n0 = stops_for(vis); pat, st = dst2.make_pattern(vis, stops, c)
    base = f"{OUT}/HAKI_jacket_01_back-scene_{k.upper()}_v3_{size}"
    dst2.write(pat, base); v = dst2.verify(base); dst2.render(base, base + "_preview.png", s=0.5 if k == "back" else 1.0)
    res[k] = dict(v, trims_cmd=st["trims"], travel=st["travel"], stops=len(stops), stops_before_merge=n0, centre=c, art_box=ub, file=base)
    print(size, k, {kk: res[k][kk] for kk in ("stitches", "trims_cmd", "stops", "size", "max_stitch")}, f"{time.time()-t:.0f}s", flush=True)
    json.dump(res, open(f"{OUT}/result.json", "w"), default=float, indent=1)
if "nosplit" not in sys.argv:
    FRAME = (360.0, 360.0); vis = prep(D["back"])
    for wm in (70.0, 55.0, 40.0):
        sp = dst2.split_clip(vis, FRAME, whole_max=wm)
        if all(sp["fits"].values()): break
    marks = dst2.split_marks(sp)
    names = {(0, 0): "S1_top-left", (1, 0): "S2_top-right", (0, 1): "S3_bottom-left", (1, 1): "S4_bottom-right"}
    spl = dict(frame=FRAME, sx=sp["sx"], sy=sp["sy"], cut_mm=sp["cut"], whole_max=wm, sections={})
    for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])):
        sv = sp["secs"][key]; t = time.time(); stops, n0 = stops_for(sv)
        bb = unary_union([r["geom"] for r in sv] + [Point(m).buffer(6) for m in marks[key]]).bounds
        cc = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
        pat, st = dst2.make_pattern(sv, stops, cc, reg_marks=marks[key])
        base = f"{OUT}/splits/HAKI_jacket_01_back-scene_v3_{size}_{names[key]}"; os.makedirs(os.path.dirname(base), exist_ok=True)
        dst2.write(pat, base); v = dst2.verify(base); dst2.render(base, base + "_preview.png", s=0.5)
        spl["sections"][names[key]] = dict(v, trims_cmd=st["trims"], stops=len(stops) + 1, bbox=bb, centre=cc, marks=marks[key], file=base,
                                           fits=(bb[2]-bb[0] <= FRAME[0]-16 and bb[3]-bb[1] <= FRAME[1]-16))
        print(size, names[key], {kk: spl["sections"][names[key]][kk] for kk in ("stitches", "trims_cmd", "stops", "size", "fits")}, f"{time.time()-t:.0f}s", flush=True)
    res["splits"] = spl; json.dump(res, open(f"{OUT}/result.json", "w"), default=float, indent=1)
print("DONE", size, flush=True)
