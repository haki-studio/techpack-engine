"""LESSONS A14 / A15 gates on the SHIPPED size-M DSTs (qa.motif_match, qa.uncovered), per motif family.

Reference = refmask.reference(refmask.from_inputs(space)): the colour classification of the INPUT IMAGES re-run here
(front.png / closeup_mockup_head.png, 4 px/mm garment grid; never the art, the scene or trace_M.npz; enclosed
fabric specks < 25 mm2 in the black ground = thread highlights, counted as black), limited to the
area embroidery may occupy (each piece's keep-out clip: zip, seams, welts, hem/cuff bands are garment details, A15) and
with the documented exclusions (SL cream = render highlights, review item 8; sleeve dark = fold shading, never thread).
Stitched = the colour that SHOWS: every sewn stitch of the size-M DST read back, drawn 0.4 mm wide (thread) at 8 px/mm in sew order (later stops
cover earlier ones and their hidden travel), closed 0.125 mm (between rows), eroded 0.25 mm = the fabric pull-in that
the file's pull comp (0.15-0.20 mm per side) compensates (stitch lines are butt-ended: no overshoot past the needle points), so a correctly compensated shape measures at its sewn size.
Families: cream (cords, teeth, lightning), red (hair + crimson shade + streaks), black (ground strokes).
Metric per motif (Rev B3): THIN motifs (median traced width < THIN_MM: cords, lightning, strands, streaks, the
black between strands) use a CENTRELINE check - recall = share of the reference centreline within TOL_MM of stitched
thread, precision = share of the stitched centreline near that motif within TOL_MM of the reference, width ratio =
stitched / reference median width; area IoU is meaningless for a 1-3 mm stroke (0.5 mm offset = IoU 0.6). BLOB
motifs (teeth, broad strands, black patches) use qa.motif_match (IoU >= 0.70, width/height >= 80 %).
usage: python3 qa_gates.py [selftest]   -> qa_gates.json (+ printed tables); compare.py prints the tables on the sheets."""
import rbcore
import json
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
import shapely
import qa, front as F, compare as C

T = np.load("trace_M.npz"); PPM = float(T["ppm"])
FAM = {"cream": ({4}, {"rb_cream", "rb_white"}), "red": ({1, 2}, {"rb_red", "rb_crimson"}), "black": ({3}, {"rb_black"})}

def grid(bb, shape):
    xs = bb[0] + (np.arange(shape[1]) + 0.5)/PPM; ys = bb[1] + (np.arange(shape[0]) + 0.5)/PPM
    return np.meshgrid(xs, ys)

SS = 2                       # stitch raster is drawn at SS x the trace resolution, then reduced (mean >= 0.5)

def visible(pieces, bb, shape, sts=None):
    """colour that SHOWS at every pixel (at SS x resolution): the DST stops drawn in sew order, each stitch THREAD mm
    wide, later stops over earlier ones (hidden travel under a later fill is covered by it, as on the garment)"""
    keys = list(rbcore.SEW); S = PPM*SS; H, W = shape[0]*SS, shape[1]*SS
    lab = np.zeros((H, W), np.uint8); w = max(1, int(round(THREAD*S)))
    for st in (sts if sts is not None else [C.stitches(P) for P in pieces]):
        nst = len(st["cols"])
        for ci in range(nst):
            im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
            for a, b, c_ in st["segs"]:
                if c_ != ci: continue
                d.line([((a[0]-bb[0])*S, (a[1]-bb[1])*S), ((b[0]-bb[0])*S, (b[1]-bb[1])*S)], fill=255, width=w)
            col = st["cols"][ci]
            if col in keys: lab[np.array(im) > 0] = keys.index(col) + 1
    return lab, keys

CLOSE_PX = 3                 # 0.375 mm; gate_cal.py: on isolated shapes of known size closing 1-3 px changes nothing
THREAD, PULL = 0.4, 0.25     # 40wt thread 0.4 mm, butt-ended lines (no overshoot past the needle points); the file adds pull
                             # comp (0.15-0.20/side) that the fabric pulls back in -> erode by the pull comp (0.25 at 8 px/mm)
def dst_mask(vis, keys, cols):
    m = np.isin(vis, [keys.index(c) + 1 for c in cols if c in keys])
    m = ndi.binary_closing(m, structure=np.ones((2*CLOSE_PX + 1,)*2, bool)) | m   # CLOSE_PX fine px: between satin rows and
    # between abutting objects of one family (a hair stroke + its crimson shade edge read as ONE strand on the garment)
    m = ndi.binary_erosion(m, iterations=int(round(PULL*PPM*SS)))         # the pull-in the file's pull comp is there for
    return m.reshape(m.shape[0]//SS, SS, m.shape[1]//SS, SS).mean(axis=(1, 3)) >= 0.5

def majority(lab):
    cnt = np.stack([ndi.uniform_filter((lab == k).astype(np.float32), 3) for k in range(10)], 0)
    return np.argmax(cnt, 0).astype(np.uint8)

THIN_MM, TOL_MM, REC_MIN, PREC_MIN, WR_MIN = 4.0, 1.0, 0.85, 0.85, 0.70
def motif_rows(ref, out, ppm, min_mm2=4.0, pad_mm=3.0):
    """one row per reference motif: centreline check for thin motifs, qa.motif_match for blobs"""
    from skimage.morphology import skeletonize
    lab, n = ndi.label(ref); pad = int(round(pad_mm*ppm)); tol = TOL_MM*ppm
    d_out = ndi.distance_transform_edt(~out); d_ref = ndi.distance_transform_edt(~ref)
    dt_ref = ndi.distance_transform_edt(ref); dt_out = ndi.distance_transform_edt(out)
    rows = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        y0, y1 = max(0, sl[0].start - pad), min(ref.shape[0], sl[0].stop + pad)
        x0, x1 = max(0, sl[1].start - pad), min(ref.shape[1], sl[1].stop + pad)
        r = lab[y0:y1, x0:x1] == k; area = r.sum()/ppm**2
        if area < min_mm2: continue
        sk = skeletonize(r) & r
        if not sk.any(): sk = r & (dt_ref[y0:y1, x0:x1] == dt_ref[y0:y1, x0:x1][r].max())
        w_ref = 2*np.median(dt_ref[y0:y1, x0:x1][sk])/ppm
        cx, cy = round((x0 + x1)/2/ppm, 1), round((y0 + y1)/2/ppm, 1)
        if w_ref >= THIN_MM:
            m = qa.motif_match(np.pad(r, 0), out[y0:y1, x0:x1], ppm, min_mm2=0.0, pad_mm=0.0)
            m = max(m, key=lambda q: q["area_mm2"]) if m else dict(iou=0.0, w_ratio=0.0, h_ratio=0.0, ok=False)
            rows.append(dict(motif=k, kind="blob", x_mm=cx, y_mm=cy, area_mm2=round(float(area), 1), w_ref=round(float(w_ref), 2),
                             iou=m["iou"], w_ratio=m["w_ratio"], h_ratio=m["h_ratio"], ok=bool(m["ok"])))
            continue
        rec = float((d_out[y0:y1, x0:x1][sk] <= tol).mean())
        o = out[y0:y1, x0:x1] & ndi.binary_dilation(r, iterations=int(round(1.5*tol)))     # stitched thread at this motif
        sko = skeletonize(o) & o
        prec = float((d_ref[y0:y1, x0:x1][sko] <= tol).mean()) if sko.any() else 0.0
        on = sko & ndi.binary_dilation(r, iterations=int(round(tol)))      # stitched centreline ON this motif
        w_out = 2*np.median(dt_out[y0:y1, x0:x1][on])/ppm if on.any() else 0.0
        wr = w_out/max(w_ref, 1e-9)
        ok = rec >= REC_MIN and prec >= PREC_MIN and min(wr, 1/max(wr, 1e-9)) >= WR_MIN
        rows.append(dict(motif=k, kind="line", x_mm=cx, y_mm=cy, area_mm2=round(float(area), 1), w_ref=round(float(w_ref), 2),
                         recall=round(rec, 2), precision=round(prec, 2), width_ratio=round(float(wr), 2), ok=bool(ok)))
    return rows

def run():
    out = {}
    for space, pieces in (("F", ("FR", "FL")), ("SR", ("SR",)), ("SL", ("SL",))):
        import refmask
        RAW = refmask.from_inputs(space)
        REF = refmask.reference(RAW, PPM, space); lab = majority(RAW); bb = tuple(T["bbF"]) if space == "F" else tuple(T["bbS"])
        X, Y = grid(bb, lab.shape)
        allowed = np.zeros(lab.shape, bool)
        for P in pieces: allowed |= shapely.contains_xy(F.piece_clip("M", P).buffer(-0.4), X, Y)
        import os
        key = "|".join(f"{C.stitches(P)['file']}:{os.path.getmtime(C.stitches(P)['file']):.0f}" for P in pieces)
        cache = f"out/gate_vis_{space}.npz"
        if os.path.exists(cache) and str(np.load(cache)["key"]) == key:
            vis = np.load(cache)["vis"]; keys = list(rbcore.SEW)
        else:
            vis, keys = visible(pieces, bb, lab.shape); np.savez_compressed(cache, vis=vis, key=key)
        res = {}
        design = np.zeros(lab.shape, bool); stitched = np.zeros(lab.shape, bool)
        for fam, (codes, cols) in FAM.items():
            ref = REF[fam] & allowed
            if space == "SL" and fam == "cream": ref[:] = False          # render highlights, not thread (review item 8)
            if space != "F" and fam == "black": ref[:] = False           # sleeve dark = fold shading (spec 02)
            dm = dst_mask(vis, keys, cols)
            if not ref.any() and not dm.any(): continue
            rows = motif_rows(ref, dm, PPM)
            res[fam] = dict(motifs=len(rows), passed=sum(r["ok"] for r in rows), lines=sum(r["kind"] == "line" for r in rows),
                            fails=[r for r in rows if not r["ok"]], rows=rows)
            if SELFTEST: res[fam]["selftest"] = selftest(ref)
            design |= ref; stitched |= dm
        gaps = qa.uncovered(design, stitched, PPM)
        for g in gaps:                                  # back to garment mm
            g["x_mm"] = round(bb[0] + g["x_mm"], 1); g["y_mm"] = round(bb[1] + g["y_mm"], 1)
        for fam in res:
            for r in res[fam]["rows"]: r["x_mm"] = round(bb[0] + r["x_mm"], 1); r["y_mm"] = round(bb[1] + r["y_mm"], 1)
        out[space] = dict(families=res, uncovered=gaps)
        print(space, {f_: (v["passed"], v["motifs"]) for f_, v in res.items()}, "gaps >= 25 mm2:", len(gaps), flush=True)
    ok = all(v["passed"] == v["motifs"] for s in out.values() for v in s["families"].values()) and not any(s["uncovered"] for s in out.values())
    out["all_pass"] = bool(ok)
    json.dump(out, open("qa_gates.json", "w"), indent=1)
    return out

def selftest(ref):
    """red-then-green on the real reference: stitched == reference passes every row; deleting a motif, shifting one
    by 2.5 mm and thinning one to 40 % must each fail that motif's row"""
    rows = motif_rows(ref, ref, PPM); green = all(r["ok"] for r in rows)
    lab, n = ndi.label(ref); sizes = ndi.sum(ref, lab, np.arange(1, n + 1)); out = {}
    if n == 0: return dict(green=green)
    big = [i + 1 for i in np.argsort(-sizes)[:3]]
    def row_for(test, k):
        rr = motif_rows(ref, test, PPM); return next((r for r in rr if r["motif"] == k), None)
    t = ref & (lab != big[0]); out["deleted"] = not row_for(t, big[0])["ok"]
    k = big[min(1, len(big) - 1)]; m = lab == k; sh = int(round(2.5*PPM))
    t = ref & ~m; t[sh:, :] |= m[:-sh, :]; out["shifted_2.5mm"] = not row_for(t, k)["ok"]
    k = big[min(2, len(big) - 1)]; m = lab == k
    th = ndi.binary_erosion(m, iterations=max(1, int(round(0.3*ndi.distance_transform_edt(m).max()))))
    t = (ref & ~m) | th; out["thinned"] = not row_for(t, k)["ok"]
    return dict(green=green, **out)

SELFTEST = False
if __name__ == "__main__":
    import sys
    SELFTEST = "selftest" in sys.argv
    r = run()
    for sp, v in r.items():
        if sp == "all_pass": continue
        for fam, d in v["families"].items():
            for f_ in d["fails"][:30]: print(" FAIL", sp, fam, f_)
        for g in v["uncovered"][:20]: print(" GAP", sp, g)
    print("ALL PASS" if r["all_pass"] else "GATES FAIL")
