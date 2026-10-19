"""Graded stitch files (no wrap): 02R/02L chest clouds, 04R/04L sleeve clouds. One file per art grade:
A 92 % (XS-S), B 100 % (M-XL), C 108 % (XXL-3XL). usage: ./py.sh build_grade.py A|B|C [pieces]"""
import sys, pickle, json, time, os
from shapely.ops import unary_union
from shapely import affinity
import moonstitch as MS, scene
G = sys.argv[1]; SC = scene.SCALE[G]; LAB = {"A": "XS-S", "B": "M-XL", "C": "XXL-3XL"}[G]
which = sys.argv[2:] or ["02R", "02L", "04R", "04L"]
A = pickle.load(open("art_graded.pkl", "rb"))
RES = f"out/results/grade_{G}.json"; os.makedirs("out/results", exist_ok=True)
res = json.load(open(RES)) if os.path.exists(RES) else {}
DIRS = {"02R": "02_chest-clouds", "02L": "02_chest-clouds", "04R": "04_sleeve-clouds", "04L": "04_sleeve-clouds"}
for k in which:
    t = time.time(); vis = A[k]
    ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0] + ub[2]) / 2, (ub[1] + ub[3]) / 2)
    if SC != 1:
        vis = [dict(r, geom=affinity.scale(r["geom"], SC, SC, origin=c), **({"rows": affinity.scale(r["rows"], SC, SC, origin=c)} if r.get("rows") is not None else {})) for r in vis]
    base = f"out/{DIRS[k]}/grade-{G}/HAKI_moon_{DIRS[k]}_{k}_{G}-{LAB}"
    r = MS.make(vis, base, 1.0, origin=c); r["m_centre"] = c
    w, h = r["size"]
    import factory
    FR_ = tuple(float(v) for v in factory.largest_frame())
    if w > FR_[0] - 16 or h > FR_[1] - 16:          # larger than the frame: split into hoopings (sleeve = back half + front half)
        import moonsplit
        sp = moonsplit.grid_split(vis, FR_, whole_max=260.0); r["sections"] = {}
        for key in sorted(sp["secs"], key=lambda q: (q[1], q[0])):
            bb = sp["bbs"][key]; cc = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
            sb = f"{base}_{sp['names'][key]}"
            rs = MS.make(sp["secs"][key], sb, 1.0, reg_marks=sp["marks"][key], origin=cc)
            rs.update(bbox=bb, fits=sp["fits"][key]); r["sections"][sp["names"][key]] = rs
            print(G, k, sp["names"][key], {kk: rs[kk] for kk in ("stitches", "trims_dst", "stops", "threads", "size", "fits")}, flush=True)
    res[k] = r
    print(G, k, {kk: r[kk] for kk in ("stitches", "trims_dst", "stops", "threads", "size", "max_stitch")}, f"{time.time()-t:.0f}s", flush=True)
    json.dump(res, open(RES, "w"), default=float, indent=1)
print("DONE", G)
