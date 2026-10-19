"""LESSONS A14 / A15 gates on the SHIPPED size-M DSTs (review item 9 + Rev B brief): per piece and motif family,
qa.motif_match (each mockup motif's silhouette vs what is stitched) and qa.uncovered (mockup-embroidered areas left bare).

Reference = the mockup's own tone classes (wavetrace.classify: the render x4, Lab nearest tone, the close-up inside its
footprint on FL) resampled into the piece's pattern mm through the SAME map the art uses (body: mockmap.body_tf of the size,
inside the piece's render region; sleeves: the seam-length harmonic map of each half, wrap.py). Garment details are masked out
first (A15): keep-out zones (seams, zip, welts, collar, hem/cuff rib), the render's silhouette-edge band (fold highlights).
Families: CURLS = cream + grey components >= 100 mm2 (crests, one row per crest), DROPS = cream components 4-100 mm2,
STRIPES = the blue band tones. Stitched = the DST's sewn stitches of that family's threads (0.6 mm thread, 4 px/mm).
The Rev B wrap moves art near seams on purpose (stretch to the seam, curls moved whole out of a keep-out): each reference
motif is therefore matched at its best local shift (search +/- 40 mm); the shift is REPORTED per row ('moved'), and the
IoU / width / height test of qa.motif_match is applied after it. Coverage gaps >= 25 mm2 are explained automatically only as
'keep-out edge' (inside 6 mm of the art limit) or 'moved by the wrap' (inside 45 mm of a seam the wrap edited, with the art
present within the shift found for that area); anything else is UNEXPLAINED and blocks delivery.
usage: ./py.sh gates.py [--art]  ->  gates_M.json + printed tables"""
import wavecore as WC
import sys, json, pickle
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
import shapely
import pyembroidery as pe
import qa, mockmap as MM, pieces as PC, wrap as WR, waveart as WA, wavetrace as WT

SIZE = "M"; PPM = 4.0; ART = "--art" in sys.argv
D = pickle.load(open(f"art_{SIZE}.pkl", "rb"))
FAM_TONES = {"curls": WT.CREAM + WT.GREY, "drops": WT.CREAM, "stripes": WT.BLUES}
FAM_THREADS = {"curls": ["w1", "w3", "g1"], "drops": ["w1", "b0"], "stripes": ["b0", "b1", "b2", "b3", "b4", "b5"]}
DROP_MAX = 100.0; SHIFT = 40.0

_LAB = {}
def labels(view):
    if view not in _LAB:
        lab, up, b = WT.classify(view); _LAB[view] = (lab, up, b)
    return _LAB[view]

def grid(P):
    b = PC.panel(SIZE, P).bounds; bb = (b[0] - 5, b[1] - 5, b[2] + 5, b[3] + 5)
    W, H = int((bb[2] - bb[0]) * PPM), int((bb[3] - bb[1]) * PPM)
    XX, YY = np.meshgrid(bb[0] + (np.arange(W) + 0.5) / PPM, bb[1] + (np.arange(H) + 0.5) / PPM)
    return bb, XX, YY

def ref_classes(P):
    """mockup tone label (index into WT.NAMES, -1 = none) on the piece grid"""
    bb, XX, YY = grid(P); out = np.full(XX.shape, -1, np.int32)
    maps = WA.piece_maps(SIZE)
    for view in ("back", "front"):
        if P not in WA.VIEW_PIECES[view]: continue
        lab, up, b = labels(view); m, reg, kind = maps[(view, P)]
        if kind == "body":
            f, finv = MM.body_tf(view, SIZE); px, py = finv(XX, YY)
            ok = shapely.contains_xy(reg, px, py)
        else:
            q = m.inv(np.c_[XX.ravel(), YY.ravel()]); px, py = q[:, 0].reshape(XX.shape), q[:, 1].reshape(XX.shape)
            fin = np.isfinite(px); px = np.where(fin, px, 0); py = np.where(fin, py, 0)
            ok = fin & ((XX * m.sgn) >= 0) & shapely.contains_xy(m.target.buffer(0.3), XX, YY) & shapely.contains_xy(reg, px, py)
        sil = MM.silhouette(view); inner = ndi.binary_erosion(sil, iterations=4)      # A15: the render's outline band (fold / edge highlights)
        ix = np.clip(px.astype(int), 0, sil.shape[1] - 1); iy = np.clip(py.astype(int), 0, sil.shape[0] - 1)
        ok &= inner[iy, ix]
        r_ = ((py - b[1]) * up).astype(int); c_ = ((px - b[0]) * up).astype(int)
        ok &= (r_ >= 0) & (r_ < lab.shape[0]) & (c_ >= 0) & (c_ < lab.shape[1])
        v = lab[np.clip(r_, 0, lab.shape[0] - 1), np.clip(c_, 0, lab.shape[1] - 1)]
        out = np.where(ok, v, out)
    clip = PC.clip_for(SIZE, P)
    out = np.where(shapely.contains_xy(clip, XX, YY), out, -1)                      # A15: keep-outs are bare by spec
    return out, bb

def ref_family(cls, fam):
    ids = [WT.NAMES.index(n) for n in FAM_TONES[fam]]
    m = np.isin(cls, ids)
    m = ndi.binary_opening(m, iterations=1)
    if fam in ("curls", "drops"):
        lab, n = ndi.label(m); area = ndi.sum(m, lab, range(1, n + 1)) / PPM**2
        keep = np.zeros(n + 1, bool)
        for i, a in enumerate(area, 1): keep[i] = (a >= DROP_MAX) if fam == "curls" else (4.0 <= a < DROP_MAX)
        m = keep[lab]
    return m

_PAT = {}
def dst_family(P, bb, fam):
    """sewn stitches of the family's threads (DST read back), 0.6 mm thread"""
    shape = (int((bb[3] - bb[1]) * PPM), int((bb[2] - bb[0]) * PPM))
    if ART:
        im = Image.new("L", shape[::-1], 0); d = ImageDraw.Draw(im)
        for r in D[P]:
            if r["col"] not in FAM_THREADS[fam] or r["grp"] in ("FM-loop",): continue
            if fam == "stripes" and r["grp"] not in ("WV",): continue
            for q in WR.polys_of(r["geom"]):
                d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=255)
                for h in q.interiors: d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in h.coords], fill=0)
        return np.asarray(im) > 0
    if P not in _PAT:
        r = json.load(open(f"out/01_wave/{SIZE}/result_{P}.json"))["full"]
        _PAT[P] = (pe.read(r["file"] + ".dst"), [s["col"] for s in r["per_stop"]], r["origin"])
    p, cols, (ox, oy) = _PAT[P]
    im = Image.new("L", shape[::-1], 0); d = ImageDraw.Draw(im); lw = max(1, int(round(0.6 * PPM))); ci = 0; prev = None
    want = set(FAM_THREADS[fam])
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; q = ((x / 10 + ox - bb[0]) * PPM, (y / 10 + oy - bb[1]) * PPM)
        if k == pe.STITCH:
            if prev is not None and cols[min(ci, len(cols) - 1)] in want: d.line([prev, q], fill=255, width=lw)
            prev = q
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        else: prev = None
    return ndi.binary_closing(np.asarray(im) > 0, iterations=2)

def align(ref, out, max_mm=SHIFT):
    """each ref component pasted at its best shift (max overlap with `out` within +/- max_mm, FFT correlation, a small
    distance penalty so ties keep the mapped position). Returns (aligned mask, source-id image, {id: shift mm})"""
    from scipy.signal import fftconvolve
    lab, n = ndi.label(ref); A = np.zeros_like(ref); Aid = np.zeros(ref.shape, np.int32); shifts = {}
    R = int(max_mm * PPM); H, W = out.shape
    pad = np.pad(out.astype(np.float32), R)
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1]; pen = 0.002 * (yy * yy + xx * xx)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        m = (lab[sl] == k); h, w = m.shape; y0, x0 = sl[0].start, sl[1].start
        win = pad[y0:y0 + h + 2 * R, x0:x0 + w + 2 * R]
        cc = fftconvolve(win, m[::-1, ::-1].astype(np.float32), mode="valid") - pen
        dy, dx = np.unravel_index(int(np.argmax(cc)), cc.shape); dy -= R; dx -= R
        Y0, X0 = y0 + dy, x0 + dx
        ys, xs = np.nonzero(m); ys = ys + Y0; xs = xs + X0
        ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
        A[ys[ok], xs[ok]] = True; Aid[ys[ok], xs[ok]] = k
        shifts[k] = round(float(np.hypot(dx, dy)) / PPM, 1)
    return A, Aid, shifts

def gate_piece(P):
    cls, bb = ref_classes(P); res = {}
    for fam in ("curls", "drops", "stripes"):
        ref = ref_family(cls, fam); out = dst_family(P, bb, fam)
        if fam == "stripes":
            al, Aid, sh = ref, None, {}
            rows = qa.motif_match(ref, out | dst_family(P, bb, "curls"), PPM, min_mm2=25.0)    # the band runs on under its crests
        else:
            al, Aid, sh = align(ref, out)
            rows = qa.motif_match(al, out, PPM, min_mm2=4.0)
        for r_ in rows:
            if Aid is not None:
                cy, cx = int(r_["y_mm"] * PPM), int(r_["x_mm"] * PPM); w = int(2 * PPM)
                ids = Aid[max(0, cy - w):cy + w, max(0, cx - w):cx + w]; ids = ids[ids > 0]
                r_["moved_mm"] = sh.get(int(np.bincount(ids).argmax()), 0.0) if len(ids) else 0.0
            r_["x_mm"] = round(r_["x_mm"] + bb[0], 1); r_["y_mm"] = round(r_["y_mm"] + bb[1], 1)
        ok = sum(r_["ok"] for r_ in rows)
        res[fam] = dict(n=len(rows), passed=ok, rows=rows, shifts=sh)
    # coverage (A15): any-art reference vs any stitch
    ref_any = np.isin(cls, [WT.NAMES.index(n) for n in WT.CREAM + WT.GREY + WT.BLUES]); ref_any = ndi.binary_opening(ref_any, iterations=1)
    out_any = dst_family(P, bb, "curls") | dst_family(P, bb, "stripes") | dst_family(P, bb, "drops")
    out_any = ndi.binary_dilation(out_any, iterations=int(1.0 * PPM))
    gaps = qa.uncovered(ref_any, out_any, PPM)
    clipb = PC.clip_for(SIZE, P).boundary
    seams = [WR.SeamSide(SIZE, sm, w_).line for sm in WR.seams(SIZE) for w_ in ("A", "B") if sm[w_][0] == P]
    from shapely.geometry import box as _box
    for g in gaps:
        x, y = g["x_mm"] + bb[0], g["y_mm"] + bb[1]; g["x_mm"], g["y_mm"] = round(x, 1), round(y, 1)
        gb = _box(x - g["w_mm"] / 2, y - g["h_mm"] / 2, x + g["w_mm"] / 2, y + g["h_mm"] / 2)
        art_near = any(r["geom"].intersects(gb.buffer(SHIFT)) for r in D[P])
        if gb.distance(clipb) < 6.0 and g["area_mm2"] < 400: g["why"] = "keep-out edge"
        elif seams and min(s.distance(gb) for s in seams) < 45.0 and art_near: g["why"] = "moved by the wrap"
        else: g["why"] = "UNEXPLAINED"
    res["uncovered"] = gaps
    return res

def summary(res):
    rows = []
    for P, r in res.items():
        for fam in ("curls", "drops", "stripes"):
            f = r[fam]; mv = [v for v in f["shifts"].values() if v > 3.0]
            rows.append(dict(piece=P, family=fam, motifs=f["n"], passed=f["passed"], failed=f["n"] - f["passed"],
                             moved=len(mv), max_move=max(mv) if mv else 0.0,
                             iou_median=round(float(np.median([x["iou"] for x in f["rows"]])), 2) if f["rows"] else None))
    return rows

if __name__ == "__main__":
    res = {P: gate_piece(P) for P in WC.PIECES}
    S = summary(res)
    for r in S: print(r)
    for P in WC.PIECES:
        un = [g for g in res[P]["uncovered"] if g["why"] == "UNEXPLAINED"]
        print(P, "uncovered", len(res[P]["uncovered"]), "unexplained", len(un), [(g["x_mm"], g["y_mm"], g["area_mm2"]) for g in un[:6]])
    json.dump(dict(summary=S, pieces=res, mode="art" if ART else "dst"), open(f"gates_{SIZE}{'_art' if ART else ''}.json", "w"), indent=1, default=float)
