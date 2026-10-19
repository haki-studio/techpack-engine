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
OPEN_MM = 15 * 0.436      # = the reference opening (disk radius 7 close-up px at 0.436 mm/px): wires drop out of both
ALL = M = B = ART_M = T_ = None
def load():
    global ALL, M, B, ART_M, T_
    ALL = json.load(open("out/results/all.json")); M = ALL["sizes"]["M"]; B = ALL["grades"]["B"]
    ART_M = pickle.load(open("art_M.pkl", "rb")); T_ = scene.traced()
HEX2K = {v[0].upper(): k for k, v in moonpal.PAL.items()}

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

# wires: both masks dilated by a 7.5 mm disc: a 1.6 mm cord passes (IoU >= 0.70) while the stitched centreline is <= ~1.6 mm
# off the close-up's and fails from ~2 mm (0.5 mm raster); proven red-then-green in out/_wip/guard_wires.py
# (same path 1.00 pass, 1.4 / 1.6 mm 0.70 / 0.71 pass, 3 mm 0.54 FAIL, wire missing -> wires_missing row)
WIRE_DIL = 7.5
def dil(m): return ndi.binary_dilation(m, structure=qa.disk(WIRE_DIL, PPM))
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

pole_sil = CA.pole_sil          # the art's own silhouette trace (closeart.pole_sil) is the reference

def at(G, rr):
    """grid mm -> garment mm (x from CB / CF, y from the neck seam; sleeves: sleeve pattern coords)"""
    for r in rr: r["x_mm"] = round(r["x_mm"] + G.x0, 1); r["y_mm"] = round(r["y_mm"] + G.y0, 1)
    return rr
def fix(G, d): return {k: at(G, v) for k, v in d.items()}

# A15 explanations: (element, family, x mm, y mm, radius mm, reason) - a reported gap within radius of (x, y) is explained
EXPLAIN = []

DBG = {}
def keep(el, fam, ref, out, G):
    DBG[(el, fam)] = (ref, out, G); return ref, out
def save_dbg():
    import os; os.makedirs("out/_wip/fid", exist_ok=True)
    for (el, fam), (r, o, G) in DBG.items():
        im = np.zeros(r.shape + (3,), np.uint8); im[r & ~o] = (230, 40, 40); im[o & ~r] = (40, 200, 60); im[r & o] = (235, 235, 235)
        Image.fromarray(im).save(f"out/_wip/fid/{el}_{fam}.png")

def wire_rows(G, ref_w, out_w, lines, excl, clip):
    """A14 per wire: corridor = 6 mm either side of the stitched centreline (art_M.pkl wire_lines); inside it the
    close-up wire pixels vs the DST wire stitches, both dilated (WIRE_DIL: pass <=> <= 1.5 mm off) -> qa.motif_match per visible
    stretch (stretches hidden behind hardware / clouds drop out). A wire whose corridor holds < 30 % of a wire's worth of
    close-up pixels has no reference there: listed as generated (not traced). Then every close-up wire stretch >= 25 mm2
    outside all corridors = a reference wire not stitched (qa.uncovered)."""
    from shapely.geometry import LineString
    dref = dil(ref_w) & ~excl & clip
    dout = dil(out_w) & ~excl
    rows = []; allc = np.zeros_like(dref)
    for wid, cs in lines:
        ln = LineString(cs); corr = G.raster([ln.buffer(6.0)]); allc |= corr
        r = dref & corr; o = dout & corr; a = r.sum() / PPM**2
        c = ln.interpolate(0.5, normalized=True)
        base = dict(motif=wid, x_mm=round(c.x - G.x0, 1), y_mm=round(c.y - G.y0, 1), area_mm2=round(float(a), 1))
        if a < 0.3 * ln.length * (WIRE_DIL + 1.6):
            rows.append(dict(base, iou=None, w_ratio=None, h_ratio=None, ok=True, generated=True)); continue
        fr = qa.motif_match(r, o, PPM, min_mm2=40)
        iou = float((r & o).sum() / max((r | o).sum(), 1))
        rows.append(dict(base, iou=round(iou, 2), w_ratio=min([f["w_ratio"] for f in fr] or [1.0]), h_ratio=min([f["h_ratio"] for f in fr] or [1.0]),
                         stretches=len(fr), ok=bool(all(f["ok"] for f in fr)), generated=False))
    miss = qa.uncovered(dref & ~allc, dout, PPM, min_mm2=25.0, open_mm=0)
    return rows, miss

def run():
    load(); res = {}
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
    pp = pole_sil(CA.CB, (380, 470, 1448, 1086), (600, 850, 500)); ww = scene.wire_mask()
    ref_pole = G.from_px(pp, to_px) & clipm & ~boxm
    ref_cl &= ~ndi.binary_dilation(ref_pole, iterations=2)          # the pole + hardware sit in front of the clouds
    ref_wire = G.from_px(ww, to_px) & wirem & ~ref_cl & ~ref_moon
    allp = cover(is_(lab, keys, {"p2", "p3", "p4", "c1"}))
    out_pole = ndi.binary_fill_holes(morphology.binary_opening(allp, qa.disk(OPEN_MM, PPM))) & ~cover(ref_cl, 0)
    out_cl = cover(is_(lab, keys, {"c1", "c2", "c3", "c5"})) & ~ndi.binary_dilation(out_pole, iterations=4)
    out_wire = cover(is_(lab, keys, {"p2", "p4", "c1"}), 0.6) & ~ndi.binary_dilation(out_pole, iterations=4) & ~out_cl
    # stars: traced star regions (MN-mare radial) are the close-up grey-green pixels (moon3); out = m5 stitches near them
    st = [r["geom"] for r in T_["moon"] if r["grp"] == "MN-mare" and isinstance(r["ang"], tuple)]
    ref_st = G.raster(st); out_st = cover(is_(lab, keys, {"m5", "p3"})) & ndi.binary_dilation(ref_st, iterations=8)
    res["01"] = dict(
        moon=qa.motif_match(*keep("01","moon",ref_moon, out_moon,G), PPM, min_mm2=200),
        stars=qa.motif_match(*keep("01","stars",ref_st, out_st,G), PPM),
        clouds=qa.motif_match(*keep("01","clouds",ref_cl, out_cl,G), PPM, min_mm2=20),
        pole=qa.motif_match(*keep("01","pole",ref_pole, out_pole,G), PPM, min_mm2=50),
        wires=None,
        uncovered=qa.uncovered((ref_moon | ref_cl | ref_pole) & clipm & ~boxm, cover(lab > 0), PPM))
    excl = ndi.binary_dilation(ref_pole | out_pole, iterations=4) | ref_cl | out_cl | ref_moon | boxm
    keep("01", "wires", dil(ref_wire) & ~excl, dil(out_wire) & ~excl, G)
    res["01"]["wires"], res["01"]["wires_missing"] = wire_rows(G, ref_wire, out_wire, ART_M["info"]["wire_lines"], excl, wirem)
    res["01"] = fix(G, res["01"])
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
    pp = pole_sil(CA.CF, (930, 480, 1448, 1040)); ww = scene.front_ctx()["W"]
    ref_pole = G.from_px(pp, fpx) & clipm
    ref_cl &= ~ndi.binary_dilation(ref_pole, iterations=2)          # the pole sits in front of the clouds
    wclip = G.raster([unary_union([fc["F01"][1], fc["F02"][1]])])
    ref_wire = G.from_px(ww, fpx) & wclip & ~ref_cl
    allp = cover(is_(lab, keys, {"p2", "p3", "p4", "c1"}))
    out_pole = ndi.binary_fill_holes(morphology.binary_opening(allp, qa.disk(OPEN_MM, PPM))) & ~cover(ref_cl, 0)
    out_cl = cover(is_(lab, keys, {"c1", "c2", "c3", "c5"})) & ~ndi.binary_dilation(out_pole, iterations=4)
    res["02_03"] = dict(clouds=qa.motif_match(*keep("02_03","clouds",ref_cl, out_cl,G), PPM, min_mm2=20),
                        pole=qa.motif_match(*keep("02_03","pole",ref_pole, out_pole,G), PPM, min_mm2=50),
                        uncovered=qa.uncovered((ref_cl | ref_pole) & clipm, cover(lab > 0), PPM))
    out_wire = cover(is_(lab, keys, {"p2", "p4", "c1"}), 0.6) & ~ndi.binary_dilation(out_pole, iterations=4) & ~out_cl
    excl = ndi.binary_dilation(ref_pole | out_pole, iterations=4) | ref_cl | out_cl
    keep("02_03", "wires", dil(ref_wire) & ~excl, dil(out_wire) & ~excl, G)
    res["02_03"]["wires"], res["02_03"]["wires_missing"] = wire_rows(G, ref_wire, out_wire, ART_M["info"]["front"]["wire_lines"], excl, wclip)
    res["02_03"] = fix(G, res["02_03"])
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
        res[k] = fix(G, dict(clouds=qa.motif_match(*keep(k,"clouds",ref_cl, out_cl,G), PPM, min_mm2=20), uncovered=qa.uncovered(ref_cl, out_cl, PPM)))
    for el, fam in res.items():                      # A15: a gap passes only with a reason (design-bare / keep-out / ...)
        for f in ("uncovered", "wires_missing"):
            for r in fam.get(f, []):
                w = next((e[5] for e in EXPLAIN if e[0] == el and e[1] == f and math.hypot(r["x_mm"] - e[2], r["y_mm"] - e[3]) <= e[4]), None)
                if w: r["why"] = w
    save_dbg()
    bad = []
    for el, fam in res.items():
        for f, rr in fam.items():
            if f in ("uncovered", "wires_missing"):
                print(f"{el:6} {f} gaps >= 25 mm2: {len(rr)}", [(r['x_mm'], r['y_mm'], r['area_mm2'], r.get('why', 'UNEXPLAINED')[:40]) for r in rr[:12]])
                bad += [(el, f, r) for r in rr if not r.get("why")]
            else:
                fails = [r for r in rr if not r["ok"]]
                print(f"{el:6} {f:7} motifs {len(rr):3}  fail {len(fails)}", [(r['x_mm'], r['y_mm'], r['area_mm2'], r['iou'], r['w_ratio'], r['h_ratio']) for r in fails[:8]])
                bad += [(el, f, r) for r in fails]
    res["_gate"] = dict(pass_=not bad, open=len(bad))
    json.dump(res, open("out/qa_fidelity.json", "w"), indent=1)
    print("FIDELITY GATE:", "PASS" if not bad else f"{len(bad)} items to explain / fix")

if __name__ == "__main__":
    run()
