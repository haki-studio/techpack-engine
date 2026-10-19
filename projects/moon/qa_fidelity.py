"""Fidelity gates on the SHIPPED size-M / grade-B files (LESSONS A14 / A15) -> out/qa_fidelity.json (+ printed tables).
Reference masks come from the close-up PIXELS, mapped to garment mm the way the art was placed:
  back (01 + 01b, one registration = the moon):
    moon   : close-up moon disc (outside the licensed box)        vs DST moon threads (m1-m5)
    stars  : close-up grey-green star pixels (3 craters)           vs DST crater-dark (m5) stitches
    clouds : close-up cloud masks (cloud3.masks), moved like scene.fit moved each cloud, inside the keep-outs
                                                                   vs DST cloud threads (c1-c5, c1 outside the pole)
    pole   : close-up pole + hardware (grey pixels, wires opened away)  vs DST pole threads, wires opened away
    wires  : close-up wire pixels (grey minus pole), 1.5 mm tolerance   vs DST wire grey, same tolerance
    uncovered: design = union of the reference families (box excluded) vs all DST coverage (01 + 01b)
  front (02 grade B + 03 size M): clouds = traced close-up silhouettes as placed (fit / shrink); pole = front close-up
    pole pixels via the front-pole registration; uncovered over clouds + pole.
  sleeves (04 grade B): clouds = traced close-up silhouettes as placed (fit).
usage: ./py.sh qa_fidelity.py"""
import json, math, pickle
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage import morphology
from shapely import affinity
from shapely.geometry import box
from shapely.ops import unary_union
import pyembroidery as pe
import moonpal, qa, moon3, closeart as CA, scene, cloud3

PPM = 2.0
ALL = json.load(open("out/results/all.json")); M = ALL["sizes"]["M"]; B = ALL["grades"]["B"]
HEX2K = {v[0].upper(): k for k, v in moonpal.PAL.items()}
T_ = scene.traced()

class Grid:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = x0, y0; self.W, self.H = int((x1 - x0) * PPM), int((y1 - y0) * PPM)
        self.XX, self.YY = np.meshgrid(x0 + (np.arange(self.W) + .5) / PPM, y0 + (np.arange(self.H) + .5) / PPM)
    def raster(self, geoms):
        im = Image.new("L", (self.W, self.H), 0); d = ImageDraw.Draw(im)
        for g in geoms:
            if g is None or g.is_empty: continue
            for p in (g.geoms if hasattr(g, "geoms") else [g]):
                if p.geom_type != "Polygon" or p.is_empty: continue
                d.polygon([((x - self.x0) * PPM, (y - self.y0) * PPM) for x, y in p.exterior.coords], fill=255)
                for h in p.interiors: d.polygon([((x - self.x0) * PPM, (y - self.y0) * PPM) for x, y in h.coords], fill=0)
        return np.array(im) > 0
    def dst(self, entries):
        """colour key per pixel of the shipped files (thread 0.45 mm), later stitches on top"""
        lab = np.zeros((self.H, self.W), np.int16); keys = {}
        for r in entries:
            p = pe.read(r["file"] + ".pes"); cols = [HEX2K.get(t.hex_color().upper(), t.hex_color().upper()) for t in p.threadlist]
            cx, cy = r["centre"]; im = Image.new("I", (self.W, self.H), 0); d = ImageDraw.Draw(im); lw = max(1, int(math.ceil(0.45 * PPM)))
            ci = 0; prev = None
            for x, y, c in p.stitches:
                k = c & pe.COMMAND_MASK; q = ((x / 10 + cx - self.x0) * PPM, (y / 10 + cy - self.y0) * PPM)
                if k == pe.STITCH:
                    key = cols[min(ci, len(cols) - 1)]; v = keys.setdefault(key, len(keys) + 1)
                    if prev is not None: d.line([prev, q], fill=v, width=lw)
                    prev = q
                elif k == pe.COLOR_CHANGE: ci += 1; prev = None
                else: prev = None
            a = np.array(im); lab = np.where(a > 0, a, lab)
        return lab, {v: k for k, v in keys.items()}
    def from_px(self, mask, to_px):
        """close-up px mask -> this grid via a mm -> px map"""
        px, py = to_px(self.XX, self.YY); c = np.round(px).astype(int); r = np.round(py).astype(int)
        ok = (r >= 0) & (c >= 0) & (r < mask.shape[0]) & (c < mask.shape[1]); out = np.zeros((self.H, self.W), bool); out[ok] = mask[r[ok], c[ok]]; return out

def cover(m, close_mm=1.2): return ndi.binary_closing(m, structure=qa.disk(close_mm, PPM)) | m
def is_(lab, keys, S): return np.isin(lab, [i for i, k in keys.items() if k in S])

def pole_masks(img, box_px, excl_fig=None):
    a = np.asarray(img.convert("RGB")).astype(float); H, W = a.shape[:2]
    sat = a.max(2) - a.min(2); lum = a.mean(2); blue = a[..., 2] - a[..., 0]
    g = ((sat < 42) & (lum > 52) & (blue < 25)) | ((lum <= 52) & (lum > 18) & (blue < 12))
    win = np.zeros_like(g); x0, y0, x1, y1 = box_px; win[y0:y1, x0:x1] = True; g &= win
    g = ndi.binary_closing(g, iterations=1)
    pole = morphology.binary_opening(g, morphology.disk(5)); pole = morphology.remove_small_objects(pole, 400)
    wires = g & ~ndi.binary_dilation(pole, iterations=3)
    wires = morphology.remove_small_objects(wires, 40)
    if excl_fig is not None: pole &= ~excl_fig; wires &= ~excl_fig
    return pole, wires

def at(G, rr):
    """grid mm -> garment mm (x from CB / CF, y from the neck seam; sleeves: sleeve pattern coords)"""
    for r in rr: r["x_mm"] = round(r["x_mm"] + G.x0, 1); r["y_mm"] = round(r["y_mm"] + G.y0, 1)
    return rr
def fix(G, d): return {k: at(G, v) for k, v in d.items()}

def run():
    res = {}
    # ======================================================== back
    G = Grid(-300, 100, 300, 590); BOX = box(*M["info"]["box"]) if isinstance(M.get("info"), dict) and "box" in M["info"] else box(-34, 268, 34, 347)
    lab, keys = G.dst([M["back"], M["moonbox"]])
    boxm = G.raster([BOX]); cb, cw = scene.back_clips("M"); clipm = G.raster([cb]); wirem = G.raster([cw])
    to_px = lambda x, y: moon3.to_px(x, y)
    # moon
    ref_moon = (np.hypot(G.XX, G.YY - 244) < 120) & ~boxm
    out_moon = cover(is_(lab, keys, {"m1", "m2", "m3", "m4", "m5"}))
    # clouds (each moved as scene.fit moved it)
    cl = [affinity.translate(c["sil"], *scene.fit(c["vis"], cb)[1]).intersection(cb) for c in T_["back_clouds"]]
    ref_cl = G.raster(cl)
    # pole + wires (close-up pixels; figure + box never traced)
    fig = np.zeros(CA.CB.size[::-1], bool); fig[:500, 600:850] = True
    pp, ww = CA.pole_masks(CA.CB, (380, 470, 1448, 1086), (600, 850, 500))
    ref_pole = G.from_px(pp, to_px) & clipm & ~boxm
    ref_wire = G.from_px(ww, to_px) & wirem & ~ref_cl & ~ref_moon
    allp = cover(is_(lab, keys, {"p2", "p3", "p4", "c1"}))
    out_pole = morphology.binary_opening(allp, qa.disk(4.0, PPM)) & ~cover(ref_cl, 0)
    out_cl = cover(is_(lab, keys, {"c1", "c2", "c3", "c5"})) & ~ndi.binary_dilation(out_pole, iterations=4)
    out_wire = cover(is_(lab, keys, {"p2", "p4", "c1"}), 0.6) & ~ndi.binary_dilation(out_pole, iterations=4) & ~out_cl
    dil = lambda m: ndi.binary_dilation(m, structure=qa.disk(3.0, PPM))           # wires: 1.5 mm tolerance each side
    # stars: traced star regions (MN-mare radial) are the close-up grey-green pixels (moon3); out = m5 stitches near them
    st = [r["geom"] for r in T_["moon"] if r["grp"] == "MN-mare" and isinstance(r["ang"], tuple)]
    ref_st = G.raster(st); out_st = cover(is_(lab, keys, {"m5", "p3"})) & ndi.binary_dilation(ref_st, iterations=8)
    res["01"] = dict(
        moon=qa.motif_match(ref_moon, out_moon, PPM, min_mm2=200),
        stars=qa.motif_match(ref_st, out_st, PPM),
        clouds=qa.motif_match(ref_cl, out_cl, PPM, min_mm2=20),
        pole=qa.motif_match(ref_pole, out_pole, PPM, min_mm2=50),
        wires=qa.motif_match(dil(ref_wire), dil(out_wire), PPM, min_mm2=40),
        uncovered=qa.uncovered((ref_moon | ref_cl | ref_pole) & clipm & ~boxm, cover(lab > 0), PPM)); res["01"] = fix(G, res["01"])
    # ======================================================== front
    G = Grid(-300, 40, 300, 520)
    lab, keys = G.dst([M["03L"], M["03R"], B["02R"], B["02L"]])
    fc = scene.front_clips("M"); clipF = unary_union([fc["F01"][0], fc["F02"][0]]); clipm = G.raster([clipF])
    sils = []
    scene.chest_art()
    for c, (k, org, mv) in zip(T_["chest"], scene.CHEST_TF):
        g = affinity.translate(affinity.scale(c["sil"], k, k, origin=org), *mv); sils.append(g.intersection(clipF))
    for c in T_["lower"]:
        mv = scene.fit(c["vis"], unary_union([fc["F01"][0], fc["F02"][0], box(-15.5, -100, 15.5, 900)]))[1]
        sils.append(affinity.translate(c["sil"], *mv).intersection(clipF))
    ref_cl = G.raster(sils)
    fpf = CA.front_pole_f()
    def fpx(x, y):          # inverse of front_pole_f (affine per axis)
        a0 = fpf(0.0, 0.0); a1 = fpf(1.0, 1.0); kx = float(a1[0] - a0[0]); ky = float(a1[1] - a0[1])
        return (x - float(a0[0])) / kx, (y - float(a0[1])) / ky
    pp, ww = CA.pole_masks(CA.CF, (930, 480, 1448, 1040))
    ref_pole = G.from_px(pp, fpx) & clipm
    allp = cover(is_(lab, keys, {"p2", "p3", "p4", "c1"}))
    out_pole = morphology.binary_opening(allp, qa.disk(4.0, PPM)) & ~cover(ref_cl, 0)
    out_cl = cover(is_(lab, keys, {"c1", "c2", "c3", "c5"})) & ~ndi.binary_dilation(out_pole, iterations=4)
    res["02_03"] = dict(clouds=qa.motif_match(ref_cl, out_cl, PPM, min_mm2=20),
                        pole=qa.motif_match(ref_pole, out_pole, PPM, min_mm2=50),
                        uncovered=qa.uncovered((ref_cl | ref_pole) & clipm, cover(lab > 0), PPM)); res["02_03"] = fix(G, res["02_03"])
    # ======================================================== sleeves
    import pattern as PT
    g_, mt = PT.draft("M")
    for k in ("04R", "04L"):
        b_ = g_["S01" if k == "04R" else "S02"].sew_poly().bounds; G = Grid(*b_)
        lab, keys = G.dst([B[k]]); clip = scene.sleeve_clip("M", k).buffer(-1.0)
        sils = []
        for s_ in T_["sleeves"]:
            if s_["sleeve"] != k or s_.get("sil") is None: continue
            mv = scene.fit(s_["vis"], scene.sleeve_clip("M", k))[1]
            sils.append(affinity.translate(s_["sil"], *mv).intersection(clip))
        ref_cl = G.raster(sils); out_cl = cover(lab > 0)
        res[k] = fix(G, dict(clouds=qa.motif_match(ref_cl, out_cl, PPM, min_mm2=20), uncovered=qa.uncovered(ref_cl, out_cl, PPM)))
    json.dump(res, open("out/qa_fidelity.json", "w"), indent=1)
    bad = []
    for el, fam in res.items():
        for f, rr in fam.items():
            if f == "uncovered":
                print(f"{el:6} uncovered gaps >= 25 mm2: {len(rr)}", [(r['x_mm'], r['y_mm'], r['area_mm2']) for r in rr[:6]])
                bad += [(el, f, r) for r in rr]
            else:
                fails = [r for r in rr if not r["ok"]]
                print(f"{el:6} {f:7} motifs {len(rr):3}  fail {len(fails)}", [(r['x_mm'], r['y_mm'], r['area_mm2'], r['iou'], r['w_ratio'], r['h_ratio']) for r in fails[:8]])
                bad += [(el, f, r) for r in fails]
    print("FIDELITY GATE:", "PASS" if not bad else f"{len(bad)} items to explain / fix")

if __name__ == "__main__":
    run()
