"""LESSONS A14 / A15 gates on the SHIPPED size-M DSTs (qa.motif_match, qa.uncovered), per motif family.

Reference = refmask.reference(): the traced label raster (trace_M.npz, 4 px/mm, the grid the art was built on; enclosed
fabric specks < 25 mm2 in the black ground = thread highlights, counted as black), limited to the
area embroidery may occupy (each piece's keep-out clip: zip, seams, welts, hem/cuff bands are garment details, A15) and
with the documented exclusions (SL cream = render highlights, review item 8; sleeve dark = fold shading, never thread).
Stitched = the colour that SHOWS: every sewn stitch of the size-M DST read back, drawn 0.4 mm wide (thread) at 8 px/mm in sew order (later stops
cover earlier ones and their hidden travel), closed 0.125 mm (between rows), eroded 0.25 mm = the fabric pull-in that
the file's pull comp (0.15-0.20 mm per side) compensates (stitch lines are butt-ended: no overshoot past the needle points), so a correctly compensated shape measures at its sewn size.
Families: cream (cords, teeth, lightning), red (hair + crimson shade + streaks), black (ground strokes).
usage: python3 qa_gates.py   -> qa_gates.json (+ printed tables); compare.py prints the tables on the sheets."""
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

def visible(pieces, bb, shape):
    """colour that SHOWS at every pixel (at SS x resolution): the DST stops drawn in sew order, each stitch THREAD mm
    wide, later stops over earlier ones (hidden travel under a later fill is covered by it, as on the garment)"""
    keys = list(rbcore.SEW); S = PPM*SS; H, W = shape[0]*SS, shape[1]*SS
    lab = np.zeros((H, W), np.uint8); w = max(1, int(round(THREAD*S)))
    for P in pieces:
        st = C.stitches(P); nst = len(st["cols"])
        for ci in range(nst):
            im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
            for a, b, c_ in st["segs"]:
                if c_ != ci: continue
                d.line([((a[0]-bb[0])*S, (a[1]-bb[1])*S), ((b[0]-bb[0])*S, (b[1]-bb[1])*S)], fill=255, width=w)
            col = st["cols"][ci]
            if col in keys: lab[np.array(im) > 0] = keys.index(col) + 1
    return lab, keys

THREAD, PULL = 0.4, 0.25     # 40wt thread 0.4 mm, butt-ended lines (no overshoot past the needle points); the file adds pull
                             # comp (0.15-0.20/side) that the fabric pulls back in -> erode by the pull comp (0.25 at 8 px/mm)
def dst_mask(vis, keys, cols):
    m = np.isin(vis, [keys.index(c) + 1 for c in cols if c in keys])
    m = ndi.binary_closing(m, structure=np.ones((3, 3), bool)) | m          # 1 fine px (0.125 mm): between satin rows only
    m = ndi.binary_erosion(m, iterations=int(round(PULL*PPM*SS)))         # the pull-in the file's pull comp is there for
    return m.reshape(m.shape[0]//SS, SS, m.shape[1]//SS, SS).mean(axis=(1, 3)) >= 0.5

def majority(lab):
    cnt = np.stack([ndi.uniform_filter((lab == k).astype(np.float32), 3) for k in range(10)], 0)
    return np.argmax(cnt, 0).astype(np.uint8)

def run():
    out = {}
    for space, pieces in (("F", ("FR", "FL")), ("SR", ("SR",)), ("SL", ("SL",))):
        import refmask
        REF = refmask.reference(T[space], PPM, space); lab = majority(T[space]); bb = tuple(T["bbF"]) if space == "F" else tuple(T["bbS"])
        X, Y = grid(bb, lab.shape)
        allowed = np.zeros(lab.shape, bool)
        for P in pieces: allowed |= shapely.contains_xy(F.piece_clip("M", P).buffer(-0.4), X, Y)
        vis, keys = visible(pieces, bb, lab.shape)
        res = {}
        design = np.zeros(lab.shape, bool); stitched = np.zeros(lab.shape, bool)
        for fam, (codes, cols) in FAM.items():
            ref = REF[fam] & allowed
            if space == "SL" and fam == "cream": ref[:] = False          # render highlights, not thread (review item 8)
            if space != "F" and fam == "black": ref[:] = False           # sleeve dark = fold shading (spec 02)
            dm = dst_mask(vis, keys, cols)
            if not ref.any() and not dm.any(): continue
            rows = qa.motif_match(ref, dm, PPM)
            res[fam] = dict(motifs=len(rows), passed=sum(r["ok"] for r in rows), fails=[r for r in rows if not r["ok"]])
            design |= ref; stitched |= dm
        gaps = qa.uncovered(design, stitched, PPM)
        for g in gaps:                                  # back to garment mm
            g["x_mm"] = round(bb[0] + g["x_mm"], 1); g["y_mm"] = round(bb[1] + g["y_mm"], 1)
        for fam in res:
            for r in res[fam]["fails"]: r["x_mm"] = round(bb[0] + r["x_mm"], 1); r["y_mm"] = round(bb[1] + r["y_mm"], 1)
        out[space] = dict(families=res, uncovered=gaps)
        print(space, {f_: (v["passed"], v["motifs"]) for f_, v in res.items()}, "gaps >= 25 mm2:", len(gaps), flush=True)
    ok = all(v["passed"] == v["motifs"] for s in out.values() for v in s["families"].values()) and not any(s["uncovered"] for s in out.values())
    out["all_pass"] = bool(ok)
    json.dump(out, open("qa_gates.json", "w"), indent=1)
    return out

if __name__ == "__main__":
    r = run()
    for sp, v in r.items():
        if sp == "all_pass": continue
        for fam, d in v["families"].items():
            for f_ in d["fails"][:30]: print(" FAIL", sp, fam, f_)
        for g in v["uncovered"][:20]: print(" GAP", sp, g)
    print("ALL PASS" if r["all_pass"] else "GATES FAIL")
