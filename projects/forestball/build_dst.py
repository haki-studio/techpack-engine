"""Production stitch files per art grade: 01 back (+ 360² hoop splits), 02R, 02L.
usage: ./py.sh build_dst.py <grade A|B|C> [back] [02R] [02L] [nosplit] [splitsonly]"""
import pickle, json, sys, time, os
import fbcore
from shapely.ops import unary_union
from shapely.geometry import Point, box
from shapely import affinity
import dst2, tech, factory
PROF = factory.load(); FRAME = tuple(float(v) for v in factory.largest_frame(PROF))     # factory.json (never hard-coded)

def render_preview(base, out_png, s=0.5):
    """DST read-back preview (dst2.render) with the placeholder basting drawn thick so it reads at preview scale"""
    import pyembroidery as pe
    from PIL import Image, ImageDraw
    dst2.render(base, out_png, s=s)
    p = pe.read(base + ".pes"); ex = p.extents(); im = Image.open(out_png); d = ImageDraw.Draw(im)
    cols = [t.hex_color().upper() for t in p.threadlist]; ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; P_ = ((x-ex[0])*s + 10, (y-ex[1])*s + 10)
        if k == pe.COLOR_CHANGE: ci += 1; prev = None; continue
        if k == pe.STITCH and cols[min(ci, len(cols)-1)] == "#00A3FF":
            if prev: d.line([prev, P_], fill=(0, 163, 255), width=4)
            prev = P_
        else: prev = None
    im.save(out_png)

def balanced_split(vis, frame, whole_max):
    """dst2.split_clip, with the split-line score = cut length + 2 mm per 1,000 stitches of imbalance between the
    two sections each line separates (Rev B: S4 136k vs S1 44k). Implemented by wrapping dst2.cut_length."""
    pts = [(r["geom"].representative_point(), tech.stitches(r)) for r in vis if r["geom"].area > 0.5]
    ys_ = [p.y for p, _ in pts]; xs_ = [p.x for p, _ in pts]; ymid = (min(ys_) + max(ys_)) / 2; xmid = (min(xs_) + max(xs_)) / 2
    orig = dst2.cut_length
    def cut_bal(GS, line, GT):
        c = orig(GS, line, GT); (x0, y0), (x1, y1) = line.coords[0], line.coords[-1]
        if abs(x1 - x0) < 1e-6:          # vertical line: balance the heavier (bottom) row left/right
            l = sum(w for p, w in pts if p.x < x0 and p.y > ymid); r_ = sum(w for p, w in pts if p.x >= x0 and p.y > ymid)
        else:
            l = sum(w for p, w in pts if p.y < y0); r_ = sum(w for p, w in pts if p.y >= y0)
        return c + 2.0 * abs(l - r_) / 1000.0
    dst2.cut_length = cut_bal
    try: sp = dst2.split_clip(vis, frame, whole_max=whole_max)
    finally: dst2.cut_length = orig
    return sp

def trim_protrusions(sp, limit=8.0, overlap=1.2):
    """no motif may reach more than `limit` mm past its section's split line (reviewer: an S4 grass blade stuck out
    ~50 mm): the overhang is cut off at the line (+ overlap for fills) and moved to the neighbouring section."""
    sx, sy = sp["sx"], sp["sy"]; BIG = 1e4; moved = 0
    def zone(key, ext):
        i, j = key
        x0 = -BIG if (sx is None or i == 0) else sx - ext; x1 = BIG if (sx is None or i == 1) else sx + ext
        y0 = -BIG if (sy is None or j == 0) else sy - ext; y1 = BIG if (sy is None or j == 1) else sy + ext
        return box(x0, y0, x1, y1)
    keys = list(sp["secs"]); add = {k: [] for k in keys}
    for k in keys:
        Z = zone(k, limit); keep = []
        for r in sp["secs"][k]:
            if r["grp"] == "PH" or Z.contains(r["geom"]): keep.append(r); continue
            ov = overlap if r["st"] in ("tatami", "padded", "satin") else 0.0
            inside = r["geom"].intersection(zone(k, ov))
            if not inside.is_empty: keep.append(dict(r, geom=inside))
            rest = r["geom"].difference(zone(k, 0.0))
            for k2 in keys:
                if k2 == k: continue
                q = rest.intersection(zone(k2, 0.0))
                if not q.is_empty and q.area > 0.3: add[k2].append(dict(r, geom=q)); moved += 1
        sp["secs"][k] = keep
    for k in keys: sp["secs"][k] += add[k]
    return moved

GRADES = {"A": (0.90, "XS-S"), "B": (1.00, "M-XL"), "C": (1.08, "XXL-3XL")}
G = sys.argv[1]; SC, GLAB = GRADES[G]
args = sys.argv[2:]
which = [a for a in args if a not in ("nosplit", "splitsonly")] or ["back", "02R", "02L"]
DIRS = {"back": "01_back-scene", "02R": "02_chest-branch", "02L": "02_chest-branch"}
NAMES = {"back": "01_back-scene", "02R": "02_chest-branch_02R", "02L": "02_chest-branch_02L"}
D = pickle.load(open("back_vis.pkl", "rb")); F = pickle.load(open("front_vis.pkl", "rb"))
SRC = {"back": D["back"], **F}

def scaled(vis, s, origin):
    if s == 1.0: return vis
    out = []
    for r in vis:
        r2 = dict(r, geom=affinity.scale(r["geom"], s, s, origin=origin).buffer(0) if r["st"] not in ("run", "bean") else affinity.scale(r["geom"], s, s, origin=origin))
        if isinstance(r["ang"], tuple):
            a = r["ang"]; ox, oy = origin; r2["ang"] = (a[0], ox + (a[1] - ox) * s, oy + (a[2] - oy) * s)
        out.append(r2)
    return out

def prep(k):
    vis = dst2.merge_colours(SRC[k])
    # leaves sew BEFORE the twigs + bark: travel between the leaves of a spray hides under the twig sewn later (LESSONS B2)
    vis = [dict(r, layer=4.5) if r["grp"] in ("LF", "LF-dark") else r for r in vis]
    ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
    return scaled(vis, SC, c), c

def stops_for(vis):
    st = tech.stops(vis, fbcore.STITCH_LAYER); n0 = len(st)
    return dst2.merge_stops(st), n0

def base_of(k, extra=""):
    return f"out/{DIRS[k]}/{G}_{GLAB}/HAKI_FB_{NAMES[k]}_{G}-{GLAB}{extra}"

RES = f"dst_results_{G}.json"
res = json.load(open(RES)) if os.path.exists(RES) else {}
for k in ([] if "splitsonly" in args else which):
    t = time.time(); vis, c = prep(k)
    stops, n0 = stops_for(vis)
    pat, st = dst2.make_pattern(vis, stops, c)
    base = base_of(k); os.makedirs(os.path.dirname(base), exist_ok=True)
    dst2.write(pat, base); v = dst2.verify(base); render_preview(base, base + "_preview.png", s=0.5 if k == "back" else 1.0)
    ub = unary_union([r["geom"] for r in vis]).bounds
    res[k] = dict(v, trims_cmd=st["trims"], travel=st["travel"], stops=len(stops), stops_before_merge=n0, centre=c,
                  threads=len({s["col"] for s in stops}), size_art=(ub[2]-ub[0], ub[3]-ub[1]), file=base,
                  worst=sorted(st.get("by", {}).items(), key=lambda kv: -kv[1])[:8], secs=round(time.time()-t))
    print(G, k, {kk: res[k][kk] for kk in ("stitches", "trims_cmd", "stops", "threads", "size", "max_stitch")}, f"{time.time()-t:.0f}s", flush=True)
    cur = json.load(open(RES)) if os.path.exists(RES) else {}           # merge: another process may own other pieces
    cur[k] = res[k]; json.dump(cur, open(RES, "w"), default=float, indent=1)

if "back" in which and "nosplit" not in args:
    vis, c = prep("back")
    def fits_all(sp, marks):          # same measure as the section files: art + basting crosses within frame - 16
        for key, sv in sp["secs"].items():
            bb = unary_union([r["geom"] for r in sv] + [Point(m).buffer(6) for m in marks[key]]).bounds
            if bb[2]-bb[0] > FRAME[0]-16 or bb[3]-bb[1] > FRAME[1]-16: return False
        return True
    for wm in (70.0, 55.0, 40.0, 30.0, 20.0):
        # 8 mm frame margin for the split-line crosses' arms (split_clip's ext only counts the outer crosses)
        sp = balanced_split(vis, FRAME, wm); n_mv = trim_protrusions(sp); marks = dst2.split_marks(sp)
        if all(sp["fits"].values()) and fits_all(sp, marks): break
        print("split whole_max", wm, "does not fit the frame with its crosses, retrying", flush=True)
    names = {(0, 0): "S1_top-left", (1, 0): "S2_top-right", (0, 1): "S3_bottom-left", (1, 1): "S4_bottom-right"}
    info = dict(frame=FRAME, sx=sp["sx"], sy=sp["sy"], cut_mm=sp["cut"], whole_max=wm, protrusions_moved=n_mv, sections={})
    for key in sorted(sp["secs"], key=lambda k: (k[1], k[0])):
        sv = sp["secs"][key]; t = time.time()
        stops, n0 = stops_for(sv)
        bb = unary_union([r["geom"] for r in sv] + [Point(m).buffer(6) for m in marks[key]]).bounds
        cc = ((bb[0]+bb[2])/2, (bb[1]+bb[3])/2)
        pat, st = dst2.make_pattern(sv, stops, cc, reg_marks=marks[key])
        base = base_of("back", f"_{names[key]}").replace(f"{G}_{GLAB}/", f"{G}_{GLAB}/splits/")
        os.makedirs(os.path.dirname(base), exist_ok=True)
        dst2.write(pat, base); v = dst2.verify(base); render_preview(base, base + "_preview.png", s=0.5)
        info["sections"][names[key]] = dict(v, trims_cmd=st["trims"], stops=len(stops) + 1, bbox=bb, centre=cc, marks=marks[key], file=base,
                                            placeholder=any(r["grp"] == "PH" for r in sv),
                                            fits=(bb[2]-bb[0] <= FRAME[0]-16 and bb[3]-bb[1] <= FRAME[1]-16))
        print(G, names[key], {kk: info["sections"][names[key]][kk] for kk in ("stitches", "trims_cmd", "stops", "size", "fits")}, f"{time.time()-t:.0f}s", flush=True)
    json.dump(info, open(f"dst_splits_{G}.json", "w"), default=float, indent=1)
print("DONE", G)
