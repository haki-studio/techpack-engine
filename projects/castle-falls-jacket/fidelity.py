"""Fidelity gates on the SHIPPED size-M DSTs (LESSONS A14 / A15): qa.motif_match per motif family and qa.uncovered per piece.
ref masks come from the tonal trace of the registered close-up composite (trace.tone_map + the same stitched-sky rule as
scene.revb_structure); dst masks are the DST read back and drawn stitch by stitch (0.5 mm) on the same garment-mm grid.
usage: python3 fidelity.py  -> out/fidelity_M.json (+ prints the tables); exit 1 if any motif fails or a gap >= 25 mm2
is unexplained (keep-outs are outside the design mask, so every gap left is unexplained)."""
import cfcore
import json, sys, pickle
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, box
from shapely import contains_xy
import qa, keepout as KO, trace as TRC, scene as SC, compare as C

PPM = 4.0          # DST drawn 1 px = 0.25 mm wide (≈ thread edge), so the stitched silhouette is not inflated
TI = TRC.TI
HEX2K = {v[0].upper(): k for k, v in cfcore.CF_PAL.items()}

def grid(P):
    b = KO.panel("M", P).bounds; b = (b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2)
    W, H = int((b[2] - b[0]) * PPM), int((b[3] - b[1]) * PPM)
    X, Y = np.meshgrid(b[0] + (np.arange(W) + .5) / PPM, b[1] + (np.arange(H) + .5) / PPM)
    return b, X, Y

def tone_on_grid(P, X, Y):
    res = TRC.tone_map(P); t = res["t"].astype(int).copy(); ppm = res["ppm"]; bb = res["bbox"]
    art = t >= 0                                       # stitched sky inside the art (scene.revb_structure, step 1)
    env = ndi.binary_fill_holes(ndi.binary_closing(art, structure=TRC.disk(24.0))) & ndi.binary_erosion(np.ones_like(art), iterations=2)
    t[env & ~art] = TI["cf_navy"]
    c = np.clip(((X - bb[0]) * ppm).astype(int), 0, t.shape[1] - 1); r = np.clip(((Y - bb[1]) * ppm).astype(int), 0, t.shape[0] - 1)
    return t[r, c]

def dst_masks(P, b, shape):
    S, Ci, cols, _ = C.segments(P, "M"); keys = [HEX2K.get(h.upper(), h) for h in cols]
    out = {}
    for ci in np.unique(Ci):
        im = Image.new("L", (shape[1], shape[0]), 0); d = ImageDraw.Draw(im)
        for s in S[Ci == ci]:
            d.line([((s[0] - b[0]) * PPM, (s[1] - b[1]) * PPM), ((s[2] - b[0]) * PPM, (s[3] - b[1]) * PPM)], fill=255, width=1)
        m = np.asarray(im) > 0
        m = ndi.binary_closing(m, structure=qa.disk(1.0, PPM))
        m = ndi.binary_opening(m, structure=qa.disk(1.6, PPM))        # drop single travel / run lines (hidden travel, not coverage)
        out[keys[ci]] = out.get(keys[ci], np.zeros(shape, bool)) | m
    return out

def fam(dm, keys, shape):
    m = np.zeros(shape, bool)
    for k in keys:
        if k in dm: m |= dm[k]
    return m

def merged(P, keys):
    plan = json.load(open("merge_plan.json"))[P]; return {plan.get(k, k) for k in keys}

def poly_mask(polys, X, Y):
    m = np.zeros(X.shape, bool)
    for p in polys: m |= contains_xy(p if hasattr(p, "area") else Polygon(p), X, Y)
    return m

def run(P):
    b, X, Y = grid(P); t = tone_on_grid(P, X, Y); sh = X.shape
    clip = contains_xy(KO.clip("M", P).buffer(-1.0), X, Y)
    dm = dst_masks(P, b, sh); allst = np.zeros(sh, bool)
    for m in dm.values(): allst |= m
    T = lambda ks: np.isin(t, [TI[k] for k in ks])
    rows = {}
    def mm(name, ref, keys, win=None, close=1.0):
        ref = ndi.binary_closing(ref, structure=qa.disk(close, PPM)) & clip      # same 1 mm closing as the DST mask (row gaps / cracks)
        ref = ndi.binary_opening(ref, structure=qa.disk(1.6, PPM)); out = fam(dm, merged(P, keys), sh)
        if win is not None: out &= win
        rows[name] = qa.motif_match(ref, out, PPM, min_mm2=8.0)
    notsky = ~T(["cf_sky", "cf_skylt"])
    bz = np.zeros(sh, bool)
    for name, (fn, args, Zp) in SC.BUILDINGS.get(P, {}).items():
        O = fn(*args)[1]; Z = Polygon(Zp).intersection(O.buffer(6)) if Zp else O.buffer(6)
        win = poly_mask([Z], X, Y) & notsky; bz |= win
        rows[name] = qa.motif_match(win & clip, allst & win, PPM, min_mm2=8.0)
    fz = poly_mask(SC.FALL_ZONE.get(P, []), X, Y)
    if fz.any():
        fref = fz & ~bz & T(["cf_white", "cf_cream", "cf_skylt"])
        mm("falls", fref, ["cf_white", "cf_cream", "cf_skylt"], win=fz & ~bz & ~(T(["cf_sky"]) & ~ndi.binary_dilation(fref, iterations=8)), close=2.0)   # falls: blue streaks inside the stream
    vz = poly_mask([box(*z) for z in SC.VILLAGE.get(P, [])], X, Y)
    if vz.any(): mm("village roofs", vz & T(["cf_navy", "cf_sky"]), ["cf_navy", "cf_sky"], win=vz)
    mm("clouds", ~bz & ~fz & T(["cf_white", "cf_cream", "cf_mist"]), ["cf_white", "cf_cream", "cf_mist"], win=~bz & ~fz)
    mm("blossom", T(["cf_pinklt", "cf_pink", "cf_rose"]), ["cf_pinklt", "cf_pink", "cf_rose"])
    mm("foliage", ~bz & T(["cf_grndk", "cf_grn", "cf_grnlt"]), ["cf_grndk", "cf_grn", "cf_grnlt"], win=~bz)
    design = (t >= 0) & clip
    gaps = qa.uncovered(design, allst, PPM)
    for g in gaps: g["x_mm"] = round(g["x_mm"] + b[0], 1); g["y_mm"] = round(g["y_mm"] + b[1], 1)
    for rs in rows.values():
        for r in rs: r["x_mm"] = round(r["x_mm"] + b[0], 1); r["y_mm"] = round(r["y_mm"] + b[1], 1)
    return rows, gaps

if __name__ == "__main__":
    R = {}; bad = False
    for P in [a for a in sys.argv[1:] if a in cfcore.PIECES] or cfcore.PIECES:
        rows, gaps = run(P); R[P] = dict(families={}, gaps=gaps)
        for fam_, rs in rows.items():
            n = len(rs); ok = sum(r["ok"] for r in rs)
            R[P]["families"][fam_] = dict(motifs=n, passed=ok, failed=[r for r in rs if not r["ok"]],
                                          iou_min=min([r["iou"] for r in rs], default=None))
            bad |= ok < n
            print(P, f"{fam_:14s} motifs {n:4d}  pass {ok:4d}  min IoU {R[P]['families'][fam_]['iou_min']}", flush=True)
        bad |= bool(gaps)
        print(P, "uncovered gaps >= 25 mm2:", len(gaps), gaps[:5], flush=True)
    json.dump(R, open("out/fidelity_M.json", "w"), indent=1, default=float)
    print("FIDELITY GATES FAIL" if bad else "FIDELITY GATES PASS")
    sys.exit(1 if bad else 0)
