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
FAM_LABEL = {"curls": "curls (crests)", "drops": "drops", "stripes": "wave masses (stripes + crests)"}
FAM_THREADS = {"curls": ["w1", "w3", "g1"], "drops": ["w1"], "stripes": ["b0", "b1", "b2", "b3", "b4", "b5"]}
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

def unwarp(P, XX, YY):
    """piece-grid points (final art positions) -> where they were before the seam warp (inverse of the composed field
    saved by seamwarp.warp_grid, by fixed-point iteration) - so the mockup reference goes through the same placement"""
    from scipy.ndimage import map_coordinates
    G = D.get("warp_grid", {}); XS, YS = XX.copy(), YY.copy()
    for key, g in G.items():
        p_, sg = key.split("|"); sg = int(sg)
        if p_ != P: continue
        m = np.ones(XX.shape, bool) if sg == 0 else ((XX > 0) if sg > 0 else (XX <= 0))
        def u(X, Y):
            c = [(Y - g["y0"]) / g["h"], (X - g["x0"]) / g["h"]]
            return map_coordinates(g["ux"], c, order=1, mode="nearest"), map_coordinates(g["uy"], c, order=1, mode="nearest")
        xs, ys = XX[m], YY[m]; x0, y0 = xs.copy(), ys.copy()
        for _ in range(4):
            ux, uy = u(x0, y0); x0, y0 = xs - ux, ys - uy
        XS[m], YS[m] = x0, y0
    return XS, YS

def ref_classes(P):
    """mockup tone label (index into WT.NAMES, -1 = none) on the piece grid, through the art's map AND its seam warp"""
    bb, XX0, YY0 = grid(P); out = np.full(XX0.shape, -1, np.int32)
    XX, YY = unwarp(P, XX0, YY0)
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
            ok = fin & ((XX0 * m.sgn) >= 0) & shapely.contains_xy(m.target.buffer(0.3), XX, YY) & shapely.contains_xy(reg, px, py)
        sil = MM.silhouette(view); inner = ndi.binary_erosion(sil, iterations=4)      # A15: the render's outline band (fold / edge highlights)
        ix = np.clip(px.astype(int), 0, sil.shape[1] - 1); iy = np.clip(py.astype(int), 0, sil.shape[0] - 1)
        ok &= inner[iy, ix]
        r_ = ((py - b[1]) * up).astype(int); c_ = ((px - b[0]) * up).astype(int)
        ok &= (r_ >= 0) & (r_ < lab.shape[0]) & (c_ >= 0) & (c_ < lab.shape[1])
        v = lab[np.clip(r_, 0, lab.shape[0] - 1), np.clip(c_, 0, lab.shape[1] - 1)]
        out = np.where(ok, v, out)
        from scipy.ndimage import map_coordinates as _mc
        img = np.asarray(MM.image(view)).astype(np.float32).mean(-1)
        GREY.setdefault(P, np.full(XX.shape, np.nan, np.float32))
        GREY[P] = np.where(ok, _mc(img, [py, px], order=1, mode="nearest"), GREY[P])
    clip = PC.clip_for(SIZE, P)
    out = np.where(shapely.contains_xy(clip, XX0, YY0), out, -1)                      # A15: keep-outs are bare by spec
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

def rigid_ref(P, fam, bb, shape):
    """CURLS / DROPS reference: each motif's own render pixels (cream + grey classes inside its traced outline), placed the
    way the art places it - rigid, at the local mean scale about its anchor (waveart.items_for: no oval curls). The Rev B wrap
    then moves some of them (seam stretch / push): align() finds that shift."""
    from PIL import Image, ImageDraw
    import trace as TR
    im = Image.new("L", shape[::-1], 0); d = ImageDraw.Draw(im); maps = WA.piece_maps(SIZE)
    mvim = Image.new("L", shape[::-1], 0); dm = ImageDraw.Draw(mvim)
    ids = [WT.NAMES.index(n) for n in FAM_TONES["curls"]]
    for view in ("back", "front"):
        if P not in WA.VIEW_PIECES[view]: continue
        lab, up, b = labels(view); m, reg, kind = maps[(view, P)]; own = WA.lobe_owner(SIZE, view)
        for i, lb in enumerate(WA.traced(view)["lobes"]):
            if own.get(i) != P: continue
            if (lb["kind"] == "dot") != (fam == "drops"): continue
            o = lb["outline"]; ob = o.bounds
            x0, y0 = int((ob[0] - b[0]) * up) - 2, int((ob[1] - b[1]) * up) - 2
            x1, y1 = int((ob[2] - b[0]) * up) + 3, int((ob[3] - b[1]) * up) + 3
            if x1 <= 0 or y1 <= 0 or x0 >= lab.shape[1] or y0 >= lab.shape[0]: continue
            x0, y0 = max(0, x0), max(0, y0)
            sub = np.isin(lab[y0:y1, x0:x1], ids)
            mk = WA.rasterize(o, (b[0] + x0 / up, b[1] + y0 / up, b[0] + x1 / up, b[1] + y1 / up), up)[:sub.shape[0], :sub.shape[1]]
            sub = sub[:mk.shape[0], :mk.shape[1]] & mk
            if not sub.any(): continue
            g = TR.polys_of(sub, up, (b[0] + x0 / up, b[1] + y0 / up), min_px=1, simplify=0.05)
            if g.is_empty: continue
            a = lb["anchor"]; A = WA.lin_at(m, kind, view, SIZE, a)
            a_mm = m(np.array([a[0]]), np.array([a[1]])); a_mm = (float(np.ravel(a_mm[0])[0]), float(np.ravel(a_mm[1])[0]))
            if A is None or not all(map(np.isfinite, a_mm)): continue
            g = WA.rigid(g, a, A, a_mm)
            mv = MOVES.get((P, f"{view}{i}"))
            if mv is None: continue                                  # the motif is not on this piece any more (cleaned / clipped away)
            g = affinity.translate(g, *mv)
            for q in WR.polys_of(g):
                d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=255)
                dm.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=int(min(250, round(float(np.hypot(*mv))))) + 1)
                for h in q.interiors: d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in h.coords], fill=0)
    r = np.asarray(im) > 0
    MOVE_RASTER[0] = np.asarray(mvim).astype(np.int32) - 1
    clipm = shapely.contains_xy(PC.clip_for(SIZE, P).buffer(-0.4), *grid(P)[1:])
    return r & clipm

from shapely import affinity
MOVES = {}; MOVE_RASTER = [None]; GREY = {}
for _P in WC.PIECES:
    for _r in D[_P]:
        if _r.get("unit") and (_P, _r["unit"]) not in MOVES: MOVES[(_P, _r["unit"])] = tuple(_r.get("mv", (0.0, 0.0)))
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
    if fam == "curls":
        import live
        rec = json.load(open(f"out/01_wave/{SIZE}/result_{P}.json"))["full"].get("chenille")
        if rec: live.draw_chenille(im, rec, bb, PPM, flat={"w1": 255, "w3": 255, "w1e": 255})
    return ndi.binary_closing(np.asarray(im) > 0, iterations=2)

def family_raster(P, bb, shape):
    """1 = stripes + rope cords, 2 = foam (crests, shades, hollows, curl cords), 3 = drops - from the art (what each area IS)"""
    im = Image.new("L", shape[::-1], 0); d = ImageDraw.Draw(im)
    code = lambda g: 1 if g in ("WV", "RP") else (3 if g in ("DR", "DR-b") else 2)
    for r in sorted(D[P], key=lambda r: r.get("layer", 0)):
        for q in WR.polys_of(r["geom"]):
            d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=code(r["grp"]))
    return np.asarray(im)

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
    allart = [WT.NAMES.index(n) for n in WT.CREAM + WT.GREY + WT.BLUES]
    for fam in ("curls", "drops", "stripes"):
        if fam == "stripes":
            # WAVE silhouette: the band masses (stripes with their crests + rope lines), mockup through the art's map
            ref = ndi.binary_closing(np.isin(cls, allart), iterations=4)
            lab_, n_ = ndi.label(ref); ar_ = ndi.sum(ref, lab_, range(1, n_ + 1)) / PPM**2 if n_ else []
            keep = np.zeros(n_ + 1, bool)
            for i_, a_ in enumerate(ar_, 1): keep[i_] = a_ >= 400
            ref = keep[lab_]
            out = ndi.binary_closing(dst_family(P, bb, "stripes") | dst_family(P, bb, "curls"), iterations=4)
            al, Aid, sh = ref, None, {}
            rows = qa.motif_match(ref, out, PPM, min_mm2=400.0)
        else:
            ref = rigid_ref(P, fam, bb, cls.shape); out = dst_family(P, bb, fam)
            if fam == "curls":                                     # crests: the art's lobes merge into crests, compare crest by crest
                ref = ndi.binary_closing(ref, iterations=2)
            al, Aid, sh = align(ref, out, max_mm=4.0)               # residual registration only: the wrap's own moves are applied above
            rows = qa.motif_match(al, out, PPM, min_mm2=4.0)
        for r_ in rows:
            if Aid is not None:
                cy, cx = int(r_["y_mm"] * PPM), int(r_["x_mm"] * PPM); w = int(2 * PPM)
                ids = Aid[max(0, cy - w):cy + w, max(0, cx - w):cx + w]; ids = ids[ids > 0]
                r_["residual_mm"] = sh.get(int(np.bincount(ids).argmax()), 0.0) if len(ids) else 0.0
                mvw = MOVE_RASTER[0][max(0, cy - w):cy + w, max(0, cx - w):cx + w]; mvw = mvw[mvw >= 0]
                r_["moved_mm"] = float(np.median(mvw)) if len(mvw) else 0.0
            r_["x_mm"] = round(r_["x_mm"] + bb[0], 1); r_["y_mm"] = round(r_["y_mm"] + bb[1], 1)
        clipb = PC.clip_for(SIZE, P).boundary
        foam = [r["geom"] for r in D[P] if r["grp"] in ("FM", "FM-sh", "FM-gr")]
        from shapely.geometry import Point as _Pt
        import shapely as _sh
        ftree = _sh.STRtree(foam) if foam else None
        for r_ in rows:
            if r_["ok"]: continue
            c = _Pt(r_["x_mm"], r_["y_mm"]); rad = np.sqrt(r_["area_mm2"] / np.pi)
            if c.distance(clipb) < rad + 3.0: r_["why"] = "keep-out edge (cut by the spec'd art limit)"
            elif P in ("SR", "SL") and abs(r_["x_mm"]) < 8.0 and r_["area_mm2"] < 30: r_["why"] = "render's sleeve-fold highlight (not art)"
            elif fam == "drops" and ftree is not None and len(ftree.query(c.buffer(rad + 1.0), predicate="intersects")): r_["why"] = "drop merged into a crest"
            elif r_["iou"] >= 0.4 and any(r.get("gen") == "under collar" and r["geom"].distance(c) < rad + 2 for r in D[P]): r_["why"] = "crest continued under the collar fall (generated)"
            elif r_["iou"] >= 0.5 and fam != "stripes" and MOVE_RASTER[0] is not None and (lambda w: len(w) and (w.max() - w.min()) > 3)(
                    (lambda a: a[a >= 0])(MOVE_RASTER[0][max(0, int((r_["y_mm"] - bb[1] - rad) * PPM)):int((r_["y_mm"] - bb[1] + rad) * PPM),
                                                         max(0, int((r_["x_mm"] - bb[0] - rad) * PPM)):int((r_["x_mm"] - bb[0] + rad) * PPM)])):
                r_["why"] = "lobes of the crest moved by different amounts (seam warp)"
            elif r_["iou"] >= 0.5 and fam == "stripes" and any(abs(sm_.distance(c)) < rad for sm_ in [WR.SeamSide(SIZE, q, w_).line for q in WR.seams(SIZE) for w_ in ("A", "B") if q[w_][0] == P and q["kind"] != "zip"]):
                r_["why"] = "wave mass reshaped by the seam warp / tapers (generated)"
            else: r_["why"] = "MISSING / misshapen"
        ok = sum(r_["ok"] for r_ in rows)
        lab_o, n_o = ndi.label(out); ar = ndi.sum(out, lab_o, range(1, n_o + 1)) / PPM**2 if n_o else []
        lo, hi = {"curls": (DROP_MAX, 1e9), "drops": (4.0, DROP_MAX), "stripes": (400.0, 1e9)}[fam]
        dst_count = int(sum(1 for a in ar if lo <= a < hi))
        res[fam] = dict(n=len(rows), passed=ok, rows=rows, shifts=sh, dst_count=dst_count)
    # stitch direction (A16): DST stitch angles vs the render's grain (input pixels, same map + seam warp), 8 mm tiles
    g = GREY.get(P)
    if g is not None and not ART:
        g = np.where(np.isfinite(g), g, np.nanmean(g))
        r = json.load(open(f"out/01_wave/{SIZE}/result_{P}.json"))["full"]
        segs = qa.dst_segments(r["file"] + ".dst", origin=(r["origin"][0] - bb[0], r["origin"][1] - bb[1]))
        if r.get("chenille"): segs += qa.dst_segments(r["chenille"]["file"] + ".dst", origin=(r["chenille"]["origin"][0] - bb[0], r["chenille"]["origin"][1] - bb[1]))
        # LESSONS A17: the direction gate needs a >= 12 px/mm reference. The mockup itself is ~0.7 px/mm (the render) - the
        # 4 ppm piece reference is resampled x3 (bilinear) so the visible-layer z-buffer and the thread width are resolved;
        # the GRAIN it reads is still the render's (blur at thread scale), so the result is reported as indicative.
        from scipy.ndimage import zoom as _zoom
        UP = 3; P12 = PPM * UP
        g12 = _zoom(g, UP, order=1)
        dm = qa.direction_match(g12, P12, segs, tile_mm=8.0)
        # per motif family (A16 sets the direction per family; WIP patch 19 Oct): stripes + rope cords on 8 mm tiles, foam
        # curls and drops turn within a few mm -> 4 mm tiles. Family of a stitch = the art region under its midpoint.
        fam_of = family_raster(P, bb, g.shape)
        vis = qa.visible_segments(segs, (0.0, 0.0, g.shape[1] / PPM, g.shape[0] / PPM), ppm=P12)
        by = {1: [], 2: [], 3: []}
        for q in vis:
            cx, cy = int((q[0] + q[2]) / 2 * PPM), int((q[1] + q[3]) / 2 * PPM)
            if 0 <= cy < fam_of.shape[0] and 0 <= cx < fam_of.shape[1] and fam_of[cy, cx] in by: by[fam_of[cy, cx]].append(q)
        fams = {}
        for k, nm, tm, ms in ((1, "stripes", 8.0, 12), (2, "foam", 4.0, 6), (3, "drops", 4.0, 4)):
            f_ = qa.direction_match(g12, P12, by[k], tile_mm=tm, min_stitches=ms, visible=False)
            fams[nm] = dict(tile_mm=tm, tiles=f_["tiles"], pct_ok=f_["pct_ok"], fail_dev=len(f_["fail_dev"]), fail_chaos=len(f_["fail_chaos"]))
        dm["by_family"] = fams; dm["ref_ppm"] = P12; dm["source_px_per_mm"] = 0.7
        for k in ("fail_dev", "fail_chaos"):
            for t_ in dm[k]: t_["at_mm"] = [round(t_["at_mm"][0] + bb[0], 1), round(t_["at_mm"][1] + bb[1], 1)]
        dm["tile_mm"] = 8.0; res["direction"] = dm
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
            f = r[fam]; mv = [x.get("moved_mm", 0.0) for x in f["rows"] if x.get("moved_mm", 0.0) > 3.0]
            rows.append(dict(piece=P, family=fam, motifs=f["n"], passed=f["passed"], failed=f["n"] - f["passed"],
                             moved=len(mv), max_move=max(mv) if mv else 0.0,
                             iou_median=round(float(np.median([x["iou"] for x in f["rows"]])), 2) if f["rows"] else None))
    return rows

if __name__ == "__main__":
    res = {P: gate_piece(P) for P in WC.PIECES}
    S = summary(res)
    for r in S: print(r)
    for P in WC.PIECES:
        d_ = res[P].get("direction")
        if d_: print(P, "direction", d_["pct_ok"], "% OK of", d_["tiles"], "tiles; off-grain", len(d_["fail_dev"]), "chaotic", len(d_["fail_chaos"]), "| by family", d_.get("by_family"))
    for P in WC.PIECES:
        un = [g for g in res[P]["uncovered"] if g["why"] == "UNEXPLAINED"]
        print(P, "uncovered", len(res[P]["uncovered"]), "unexplained", len(un), [(g["x_mm"], g["y_mm"], g["area_mm2"]) for g in un[:6]])
        for fam in ("curls", "drops", "stripes"):
            bad = [(r_["x_mm"], r_["y_mm"], r_["area_mm2"], r_["iou"]) for r_ in res[P][fam]["rows"] if not r_["ok"] and r_.get("why", "").startswith("MISSING")]
            if bad: print("   ", P, fam, "MISSING", bad)
    json.dump(dict(summary=S, pieces=res, mode="art" if ART else "dst"), open(f"gates_{SIZE}{'_art' if ART else ''}.json", "w"), indent=1, default=float)
