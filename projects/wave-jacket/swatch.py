"""FOAM STRIKE-OFF SWATCH (review items 4 + 6): one small file, one hooping, that sews the SAME crest four times so the
factory and the founder can compare the foam options side by side before the full pieces are sewn:
    A  padded tatami + loop texture, Foam ECRU (#D3CAC1, w1)  = the production files' colour (founder 20 Oct: ecru first)
    B  moss / chenille look on a flat head: flat tatami base + dense scalloped loop spirals (1.0 mm apart), ecru
    C  = A in the Foam white alternate (#F0EDEA, the render colour)
    D  = B in white
Fix round 3 (PR #27 review 2): w1 IS ecru since 20 Oct, so the old 'Foam white' tiles had sewn ecru twice - rebuilt.
The crest is the FL shoulder crest traced from the founder's close-up (LESSONS A12): the 92 x 92 mm window of the FL art with
the most foam inside the close-up footprint. True chenille needs a chenille / moss head (chain stitch, its own file format):
the FM outlines of this file (= ART svg) are the chenille regions if the factory has one (F1 asks).
usage: ./py.sh swatch.py  ->  out/01_wave/M/swatch/HAKI_WAVE_01_wave_FOAM-SWATCH_M.dst/.pes + preview + result json"""
import wavecore as WC
import json, os, pickle, math
import numpy as np
from shapely.geometry import box, Polygon
from shapely.ops import unary_union
from shapely import affinity
import tech, readback, factory, motifs2, motifs
import waveart as WA
dst2 = WC.patch_dst2()

WHITE = WC.FOAM_WHITE_ALT[0]
motifs2.PAL["w1e"] = (WHITE, "Foam white (alternate)", "foam crests in the white alternate (swatch only)"); motifs2.HEX["w1e"] = WHITE; motifs.HEX["w1e"] = WHITE
import specbase as SB
SB.TH["w1e"] = tech.thread_table(["w1e"])["w1e"]
tech.COLOUR_ORDER = [c for c in tech.COLOUR_ORDER if c != "w1e"]
tech.COLOUR_ORDER.insert(tech.COLOUR_ORDER.index("w1") + 1, "w1e")
D = pickle.load(open("art_M.pkl", "rb"))
OUT = "out/01_wave/M/swatch"; os.makedirs(OUT, exist_ok=True)
W = 92.0; GAP = 14.0

def pick_window():
    import json as _j
    H = np.array(_j.load(open("cu_reg.json"))["H"]); import mockmap as MM
    from PIL import Image
    w, h = Image.open("inputs/closeup_mockup_foam.png").size
    c = np.array([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]], float) @ H.T; c = c[:, :2] / c[:, 2:]
    f, _ = MM.body_tf("front", "M"); X, Y = f(c[:, 0], c[:, 1]); foot = Polygon(np.c_[X, Y]).buffer(0)
    foam = unary_union([r["geom"] for r in D["FL"] if r["grp"] == "FM"]).intersection(foot)
    b = foot.bounds; best = None
    for x in np.arange(b[0], b[2] - W + 1, 4.0):
        for y in np.arange(b[1], b[3] - W + 1, 4.0):
            a = foam.intersection(box(x, y, x + W, y + W)).area
            if best is None or a > best[0]: best = (a, x, y)
    return box(best[1], best[2], best[1] + W, best[2] + W), foot

def moss(items):
    """B / D: the raised padded foam becomes a flat tatami base + dense scalloped loop spirals (moss / chenille look)"""
    out = []
    for r in items:
        if r["grp"] == "FM-loop": continue                                        # replaced by the dense loops below
        if r["grp"] == "FM" and r["st"] == "padded": out.append(dict(r, st="tatami"))
        else: out.append(r)
    for r in [q for q in items if q["grp"] == "FM" and q["st"] == "padded"]:
        for p in WA.polys(r["geom"]):
            for lp in WA.loops_for(p, spacing=1.0, inset=0.6):
                lp = lp.intersection(p.buffer(-0.3))
                for q in WA.polys(lp):
                    if q.area > 0.3: out.append(dict(motifs2.R("w3", q, "run", None, "FM-loop"), z=WA.Z["foam"] + 0.5, unit=r.get("unit"), layer=WC.L_LOOP))
    return out

def recolour(items):
    return [dict(r, col="w1e") if r["col"] == "w1" and r["grp"] in ("FM", "DR") else r for r in items]

def tile(items, win, dx, dy):
    out = []
    for r in items:
        g = r["geom"].intersection(win)
        if g.is_empty or g.area < 0.3: continue
        out.append(dict(r, geom=affinity.translate(g, dx, dy).buffer(0)))
    return out

def build():
    win, foot = pick_window()
    base = [r for r in D["FL"] if r["geom"].intersects(win)]
    x0, y0 = win.bounds[0], win.bounds[1]
    tiles = {"A padded, Foam ecru": (base, 0, 0), "B moss, Foam ecru": (moss(base), 1, 0),
             "C padded, Foam white (alt)": (recolour(base), 0, 1), "D moss, Foam white (alt)": (recolour(moss(base)), 1, 1)}
    vis = []
    for nm, (its, i, j) in tiles.items(): vis += tile(its, win, -x0 + i * (W + GAP), -y0 + j * (W + GAP))
    vis = dst2.merge_colours(vis)
    ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0] + ub[2]) / 2, (ub[1] + ub[3]) / 2)
    stops = dst2.merge_stops(tech.stops(vis)); pat, st = dst2.make_pattern(vis, stops, c)
    basep = f"{OUT}/HAKI_WAVE_01_wave_FOAM-SWATCH_M"
    dst2.write(pat, basep); dst2.render(basep, basep + "_preview.png", bg=(39, 47, 67), s=0.5)
    rb = readback.dst(basep + ".dst"); rb["threads"] = factory.check_threads(basep + ".pes")
    rb.update(file=basep, window_FL=[round(v, 1) for v in win.bounds], tiles=list(tiles), tile_mm=W, gap_mm=GAP,
              colours=[s["col"] for s in stops])
    for ps, s in zip(rb["per_stop"], stops): ps["col"] = s["col"]
    json.dump(rb, open(f"{OUT}/result_swatch.json", "w"), indent=1, default=float)
    print("swatch", {k: rb[k] for k in ("stitches", "trims", "stops", "size_mm", "max_stitch", "threads")}, rb["window_FL"])
    return rb

if __name__ == "__main__":
    build()
