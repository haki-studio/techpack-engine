"""v3 production stitch files: 15 threads, consolidated stops, production density, 3 art grades + 360² back splits.
usage: python3 build_dst3.py <grade A|B|C> [pieces...] [nosplit]"""
import pickle, json, sys, time, os
from shapely.ops import unary_union
from shapely.geometry import Point
from shapely import affinity
import dst2, tech

GRADES = {"A": (0.92, "XS-S"), "B": (1.00, "M-XL"), "C": (1.08, "XXL-3XL")}
G = sys.argv[1]; SC, GLAB = GRADES[G]
args = sys.argv[2:]
which = [a for a in args if a != "nosplit"] or ["back", "sleeve", "02R", "02L", "03", "04"]
DIRS = {"back": "01_back-scene", "sleeve": "01_back-scene", "02R": "02_chest-branch", "02L": "02_chest-branch", "03": "03_chest-pine", "04": "04_lower-bamboo"}
NAMES = {"back": "01_back-scene_BACK", "sleeve": "01_back-scene_SLEEVE", "02R": "02_chest-branch_02R", "02L": "02_chest-branch_02L", "03": "03_chest-pine", "04": "04_lower-bamboo"}
D = pickle.load(open("back2_vis.pkl", "rb")); F = pickle.load(open("front_vis.pkl", "rb"))
SRC = {"back": D["back"], "sleeve": None, **F}

def scaled(vis, s, origin):
    if s == 1.0: return vis
    out = []
    for r in vis:
        r2 = dict(r, geom=affinity.scale(r["geom"], s, s, origin=origin))
        if isinstance(r["ang"], tuple):
            a = r["ang"]; ox, oy = origin
            r2["ang"] = (a[0], ox + (a[1] - ox) * s, oy + (a[2] - oy) * s)
        out.append(r2)
    return out

def prep(k):
    if k == "sleeve":
        import spec2; raw = spec2.VS_SEAM; src = "back2_vis.pkl"
    else:
        raw = SRC[k]; src = "back2_vis.pkl" if k == "back" else "front_vis.pkl"
    vis = dst2.clean_cached(k, raw, src)
    vis = dst2.merge_colours(vis)
    vis = [dict(r, layer=4.55) if tech.rule_for(r["grp"]) == "BD-hl" else r for r in vis]   # bud highlights first: travel hides under bud bodies
    ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
    return scaled(vis, SC, c), c

def stops_for(vis):
    st = tech.stops(vis, tech.STITCH_LAYER); n0 = len(st)
    st = dst2.merge_stops(st)
    return st, n0

RES = f"dst3_results_{G}.json"
res = json.load(open(RES)) if os.path.exists(RES) else {}
for k in which:
    t = time.time(); vis, c = prep(k)
    stops, n0 = stops_for(vis)
    pat, st = dst2.make_pattern(vis, stops, c)
    base = f"out/{DIRS[k]}/v3_{G}/HAKI_jacket_{NAMES[k]}_v3_{G}-{GLAB}"
    os.makedirs(os.path.dirname(base), exist_ok=True)
    dst2.write(pat, base); v = dst2.verify(base); dst2.render(base, base + "_preview.png", s=0.5 if k == "back" else 1.0)
    ub = unary_union([r["geom"] for r in vis]).bounds
    res[k] = dict(v, trims_cmd=st["trims"], travel=st["travel"], stops=len(stops), stops_before_merge=n0, centre=c,
                  size_art=(ub[2]-ub[0], ub[3]-ub[1]), file=base, worst=sorted(st.get("by", {}).items(), key=lambda kv: -kv[1])[:8])
    print(G, k, {kk: res[k][kk] for kk in ("stitches", "trims_cmd", "stops", "stops_before_merge", "size", "max_stitch")}, f"{time.time()-t:.0f}s", flush=True)
    json.dump(res, open(RES, "w"), default=float, indent=1)

if "back" in which and "nosplit" not in args:
    FRAME = (360.0, 360.0)
    vis, c = prep("back")
    for wm in (70.0, 55.0, 40.0):
        sp = dst2.split_clip(vis, FRAME, whole_max=wm)
        if all(sp["fits"].values()): break
    marks = dst2.split_marks(sp)
    names = {(0, 0): "S1_top-left", (1, 0): "S2_top-right", (0, 1): "S3_bottom-left", (1, 1): "S4_bottom-right"}
    info = dict(frame=FRAME, sx=sp["sx"], sy=sp["sy"], cut_mm=sp["cut"], whole_max=wm, sections={})
    for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])):
        sv = sp["secs"][key]; t = time.time()
        stops, n0 = stops_for(sv)
        bb = unary_union([r["geom"] for r in sv] + [Point(m).buffer(6) for m in marks[key]]).bounds
        cc = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
        pat, st = dst2.make_pattern(sv, stops, cc, reg_marks=marks[key])
        base = f"out/01_back-scene/v3_{G}/splits/HAKI_jacket_01_back-scene_v3_{G}-{GLAB}_{names[key]}"
        os.makedirs(os.path.dirname(base), exist_ok=True)
        dst2.write(pat, base); v = dst2.verify(base); dst2.render(base, base + "_preview.png", s=0.5)
        info["sections"][names[key]] = dict(v, trims_cmd=st["trims"], stops=len(stops) + 1, bbox=bb, centre=cc, marks=marks[key], file=base,
                                            fits=(bb[2]-bb[0] <= FRAME[0]-16 and bb[3]-bb[1] <= FRAME[1]-16))
        print(G, names[key], {kk: info["sections"][names[key]][kk] for kk in ("stitches", "trims_cmd", "stops", "size", "fits")}, f"{time.time()-t:.0f}s", flush=True)
    json.dump(info, open(f"dst3_splits_{G}.json", "w"), default=float, indent=1)
print("DONE", G)
