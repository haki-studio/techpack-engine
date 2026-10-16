import pickle, json, sys, time, os, collections
from shapely.ops import unary_union
import dst2, tech

which = [a for a in sys.argv[1:] if a != "split"] or ([] if "split" in sys.argv else ["back", "sleeve", "02R", "02L", "03", "04"])
D = pickle.load(open("back2_vis.pkl", "rb")); F = pickle.load(open("front_vis.pkl", "rb"))
SRC = {"back": D["back"], "sleeve": D["sleeve"], **F}
DIRS = {"back": "01_back-scene", "sleeve": "01_back-scene", "02R": "02_chest-branch", "02L": "02_chest-branch", "03": "03_chest-pine", "04": "04_lower-bamboo"}
NAMES = {"back": "01_back-scene_BACK", "sleeve": "01_back-scene_SLEEVE", "02R": "02_chest-branch_02R", "02L": "02_chest-branch_02L", "03": "03_chest-pine", "04": "04_lower-bamboo"}
res = json.load(open("dst2_results.json")) if os.path.exists("dst2_results.json") else {}
for k in which:
    t = time.time(); vis = SRC[k]
    if k == "sleeve":   # sleeve piece is digitized in seam coordinates (as on the spec)
        import spec2; vis = spec2.VS_SEAM
    vis = dst2.clean_cached(k, vis, "back2_vis.pkl" if k in ("back", "sleeve") else "front_vis.pkl")
    stops = tech.stops(vis, tech.STITCH_LAYER)
    ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
    pat, st = dst2.make_pattern(vis, stops, c)
    base = f"out/{DIRS[k]}/HAKI_jacket_{NAMES[k]}_v2"
    dst2.write(pat, base); v = dst2.verify(base); dst2.render(base, base + "_preview.png", s=0.5 if k == "back" else 1.0)
    by = sorted(st.get("by", {}).items(), key=lambda kv: -kv[1])[:8]
    res[k] = dict(v, trims_cmd=st["trims"], travel=st["travel"], jumps_short=st["jumps"], stops=len(stops), centre=c, size_art=(ub[2]-ub[0], ub[3]-ub[1]), worst=by)
    print(k, res[k], f"{time.time()-t:.0f}s", flush=True)
    json.dump(res, open("dst2_results.json", "w"), default=float, indent=1)

# ---------------------------------------------------------------- hoop splits (pieces larger than a 360 x 360 frame)
if "split" in sys.argv or "back" in which:
    which = [w for w in which if w != "split"]
    FRAME = (360.0, 360.0)
    vis = dst2.clean_cached("back", SRC["back"], "back2_vis.pkl"); sp = dst2.split_clip(vis, FRAME)
    marks = dst2.split_marks(sp)
    names = {(0, 0): "S1_top-left", (1, 0): "S2_top-right", (0, 1): "S3_bottom-left", (1, 1): "S4_bottom-right"}
    info = dict(frame=FRAME, sx=sp["sx"], sy=sp["sy"], cut_mm=sp["cut"], sections={})
    for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])):
        sv = sp["secs"][key]; t = time.time()
        stops = tech.stops(sv, tech.STITCH_LAYER)
        bb = unary_union([r["geom"] for r in sv] + [__import__("shapely.geometry", fromlist=["Point"]).Point(m).buffer(6) for m in marks[key]]).bounds
        c = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
        pat, st = dst2.make_pattern(sv, stops, c, reg_marks=marks[key])
        base = f"out/01_back-scene/splits/HAKI_jacket_01_back-scene_{names[key]}"
        os.makedirs(os.path.dirname(base), exist_ok=True)
        dst2.write(pat, base); v = dst2.verify(base); dst2.render(base, base + "_preview.png", s=0.5)
        info["sections"][names[key]] = dict(v, trims_cmd=st["trims"], stops=len(stops) + 1, bbox=bb, centre=c, marks=marks[key],
                                            fits=(bb[2]-bb[0] <= FRAME[0]-16 and bb[3]-bb[1] <= FRAME[1]-16))
        print(names[key], info["sections"][names[key]], f"{time.time()-t:.0f}s", flush=True)
    json.dump(info, open("dst2_splits.json", "w"), default=float, indent=1)
