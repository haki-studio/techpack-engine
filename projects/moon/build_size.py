"""Per-size stitch files: 01 back (+ placeholder basting stop) + 2x2 360² splits, 03L + 03R lower fronts.
usage: ./py.sh build_size.py SIZE [nosplit] [only=back,03L,03R]  ->  out/<el>/by-size/<SIZE>/..., result json"""
import sys, pickle, json, time, os
from shapely.ops import unary_union
from shapely.geometry import Point
import moonstitch as MS, dst2
size = sys.argv[1]; args = sys.argv[2:]
only = next((a.split("=")[1].split(",") for a in args if a.startswith("only=")), ["back", "03L", "03R"])
splitsonly = "splitsonly" in args
if splitsonly: only = []
D = pickle.load(open(f"art_{size}.pkl", "rb")); info = D["info"]
RES = f"out/results/size_{size}.json"; os.makedirs("out/results", exist_ok=True)
res = json.load(open(RES)) if os.path.exists(RES) else {}
res["info"] = {k: v for k, v in info.items()}
PATH = {"back": ("01_back-scene", "01_back-scene_BACK"), "03L": ("03_lower-front", "03_lower-front_03L"), "03R": ("03_lower-front", "03_lower-front_03R")}
SRC = {"back": "back", "03L": "F03L", "03R": "F03R"}
for k in only:
    t = time.time(); d, nm = PATH[k]
    base = f"out/{d}/by-size/{size}/HAKI_moon_{nm}_{size}"
    r = MS.make(D[SRC[k]], base, 0.5 if k == "back" else 1.0, placeholder=info["box"] if k == "back" else None)
    res[k] = r
    print(size, k, {kk: r[kk] for kk in ("stitches", "trims_dst", "stops", "threads", "size", "max_stitch")}, f"{time.time()-t:.0f}s", flush=True)
    json.dump(res, open(RES, "w"), default=float, indent=1)
if ("back" in only or splitsonly) and "nosplit" not in args:
    FRAME = (360.0, 360.0); vis = D["back"]
    import moonsplit
    sp = moonsplit.grid_split(vis, FRAME)
    marks = sp["marks"]; names = sp["names"]
    bx = info["box"]; boxc = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
    # the placeholder basting outline goes to the section that can hold it inside the frame (with its crosses)
    def _fits_with_box(key):
        b = sp["bbs"][key]; b = (min(b[0], bx[0]), min(b[1], bx[1]), max(b[2], bx[2]), max(b[3], bx[3]))
        return b[2] - b[0] <= FRAME[0] - 16 and b[3] - b[1] <= FRAME[1] - 16
    def _d(k): b = sp["bbs"][k]; return abs((b[0] + b[2]) / 2 - boxc[0]) + abs((b[1] + b[3]) / 2 - boxc[1])
    key_box = sorted(sp["secs"], key=lambda k: (not _fits_with_box(k), _d(k)))[0]
    from shapely.geometry import box as _box, LineString as _LS
    ring = _LS([(bx[0], bx[1]), (bx[2], bx[1]), (bx[2], bx[3]), (bx[0], bx[3]), (bx[0], bx[1])])
    PH = {}
    if _fits_with_box(key_box): PH[key_box] = bx
    else:                                   # box straddles a split: each section bastes its own part of the outline
        for k in sp["secs"]:
            part = ring.intersection(sp["allowed"][k].intersection(_box(*sp["bbs"][k])).buffer(0.01))
            segs = [part] if part.geom_type == "LineString" else [g_ for g_ in getattr(part, "geoms", []) if g_.geom_type == "LineString"]
            segs = [list(g_.coords) for g_ in segs if g_.length > 3]
            if segs: PH[k] = segs
    spl = dict(frame=FRAME, grid=(sp["nx"], sp["ny"]), xs=sp["xs"], ys=sp["ys"], cut_mm=sp["cut"], box_section=", ".join(names[k] for k in PH), sections={})
    for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])):
        sv = sp["secs"][key]; t = time.time()
        ph = PH.get(key)
        bb = sp["bbs"][key]
        if ph: pb = MS.ph_bounds(ph); bb = (min(bb[0], pb[0]), min(bb[1], pb[1]), max(bb[2], pb[2]), max(bb[3], pb[3]))
        cc = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
        base = f"out/01_back-scene/by-size/{size}/splits/HAKI_moon_01_back-scene_{size}_{names[key]}"
        r = MS.make(sv, base, 0.5, placeholder=ph, reg_marks=marks[key], origin=cc)
        r.update(bbox=bb, marks=marks[key], fits=(bb[2] - bb[0] <= FRAME[0] - 16 and bb[3] - bb[1] <= FRAME[1] - 16))
        spl["sections"][names[key]] = r
        print(size, names[key], {kk: r[kk] for kk in ("stitches", "trims_dst", "stops", "threads", "size", "fits")}, f"{time.time()-t:.0f}s", flush=True)
    res["splits"] = spl; json.dump(res, open(RES, "w"), default=float, indent=1)
print("DONE", size, flush=True)
