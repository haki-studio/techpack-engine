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
import sys, json, pickle, os
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
FAM_THREADS = {"curls": ["w1", "w3", "g1"], "drops": ["w1", "w3", "g1"], "stripes": ["b0", "b1", "b2", "b3", "b4", "b5"]}
DROP_MAX = 100.0; SHIFT = 40.0
PULL_DR = float(WC.WV_RULES["DR"][6])          # pull compensation of the drop satins (wavecore rules)

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
        PXY.setdefault(P, {})[view] = (np.where(ok, px, np.nan).astype(np.float32), np.where(ok, py, np.nan).astype(np.float32))
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
    uim = Image.new("I", shape[::-1], 0); du = ImageDraw.Draw(uim)
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
            if fam == "drops":
                hr = lb.get("hr")
                if hr:      # traced at close-up resolution (wavetrace.dots_hr): the silhouette IS input pixels at 4-10 px/mm
                    gh = affinity.translate(WA.rigid(o, a, A, a_mm), *mv)
                    DROP_REF.append((unit_id(f"{view}{i}"), gh.intersection(PC.clip_for(SIZE, P).buffer(-0.4)), hr))
                else:
                    DROP_REF.append((unit_id(f"{view}{i}"), g.intersection(PC.clip_for(SIZE, P).buffer(-0.4)), None))
            for q in WR.polys_of(g):
                d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=255)
                dm.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=int(min(250, round(float(np.hypot(*mv))))) + 1)
                du.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=unit_id(f"{view}{i}"))
                for h in q.interiors: d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in h.coords], fill=0)
    r = np.asarray(im) > 0
    MOVE_RASTER[0] = np.asarray(mvim).astype(np.int32) - 1
    UNIT_RASTER[0] = np.asarray(uim).astype(np.int32)
    clipm = shapely.contains_xy(PC.clip_for(SIZE, P).buffer(-0.4), *grid(P)[1:])
    return r & clipm

from shapely import affinity
MOVES = {}; MOVE_RASTER = [None]; GREY = {}; PXY = {}; DROP_REF = []; UNIT_RASTER = [None]; _UID = {}
def unit_id(u):
    """stable int id of a rigid motif unit (under-collar copies '~uc' count as the same motif)"""
    u = str(u).split("~")[0]
    return _UID.setdefault(u, len(_UID) + 1)

def art_unit_raster(P, bb, shape):
    """id of the art's rigid motif (unit) at each grid px, top layer wins; 0 = stripes / rope / filler (no unit)"""
    im = Image.new("I", shape[::-1], 0); d = ImageDraw.Draw(im)
    for r in sorted(D[P], key=lambda r: r.get("layer", 0)):
        if r["grp"] in ("FM-loop",): continue
        f = unit_id(r["unit"]) if r.get("unit") else 0
        for q in WR.polys_of(r["geom"]):
            d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=f)
    return np.asarray(im).astype(np.int32)

def drops_by_unit(P, bb, al, Aid, ref_units):
    """LESSONS A21 for spray drops: a drop that touches a crest is sewn in the same cream / grey threads, so a family mask
    merges it into the crest. Each reference drop (input pixels, its own traced outline) is compared with the visible DST
    stitches of ITS motif only: every visible segment of the drop threads is attributed to the art motif under its
    midpoint (art_unit_raster). The reference stays input pixels; a drop sewn in the wrong place or shape still fails."""
    shape = al.shape; ua = art_unit_raster(P, bb, shape)
    vis, vcol = _PAT[P]; want = set(FAM_THREADS["drops"])
    from collections import defaultdict
    segs_u = defaultdict(list)
    for (x0, y0, x1, y1), c in zip(vis, vcol):
        if c not in want: continue
        cx, cy = int((x0 + x1) / 2 * PPM), int((y0 + y1) / 2 * PPM)
        if 0 <= cy < shape[0] and 0 <= cx < shape[1] and ua[cy, cx]: segs_u[int(ua[cy, cx])].append((x0, y0, x1, y1))
    lw = max(1, int(round(0.6 * PPM))); rows = []
    lab, n = ndi.label(al)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        comp = lab == k
        us = ref_units[comp]; us = us[us > 0]
        u = int(np.bincount(us).argmax()) if len(us) else 0
        im = Image.new("L", shape[::-1], 0); d = ImageDraw.Draw(im)
        for x0, y0, x1, y1 in segs_u.get(u, []):
            # the fabric pulls each stitch in by about the pull compensation the build added (that is what the compensation
            # is for), so the sewn drop is drawn with every stitch shortened by PULL_DR at both ends (as qa.centreline_match
            # subtracts 2 x pull from a stroke's width)
            L = float(np.hypot(x1 - x0, y1 - y0)); k_ = min(0.45, PULL_DR / L) if L > 0 else 0.0
            dx, dy = (x1 - x0) * k_, (y1 - y0) * k_
            d.line([((x0 + dx) * PPM, (y0 + dy) * PPM), ((x1 - dx) * PPM, (y1 - dy) * PPM)], fill=255, width=lw)
        o = ndi.binary_closing(np.asarray(im) > 0, iterations=2)
        rr = qa.motif_match(comp, o, PPM, min_mm2=4.0)
        for r_ in rr: r_["unit"] = u
        rows += rr
    return rows
for _P in WC.PIECES:
    for _r in D[_P]:
        if _r.get("unit") and (_P, _r["unit"]) not in MOVES: MOVES[(_P, _r["unit"])] = tuple(_r.get("mv", (0.0, 0.0)))
_PAT = {}; _RAW = {}
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
        # LESSONS A17: the motif gate reads the VISIBLE top layer of the written DST (qa.visible_segments, z-buffer in sew
        # order at 12 ppm), i.e. what the eye sees on the sewn piece. Hidden travel runs under later fills (up to 58 mm long
        # on FL, sewn in cream before the crests covering them) no longer join neighbouring crests into one blob (A21).
        r = json.load(open(f"out/01_wave/{SIZE}/result_{P}.json"))["full"]
        p = pe.read(r["file"] + ".dst"); cols = [s["col"] for s in r["per_stop"]]; ox, oy = r["origin"]
        segs, sc, prev, ci = [], [], None, 0
        for x, y, cmd in p.stitches:
            k = cmd & pe.COMMAND_MASK; q = (x / 10 + ox - bb[0], y / 10 + oy - bb[1])
            if k == pe.STITCH:
                if prev is not None and prev != q: segs.append((prev[0], prev[1], q[0], q[1])); sc.append(cols[min(ci, len(cols) - 1)])
                prev = q
            else:
                prev = None
                if k == pe.COLOR_CHANGE: ci += 1
        vis, ix = qa.visible_segments(segs, (0.0, 0.0, bb[2] - bb[0], bb[3] - bb[1]), ppm=12.0, return_index=True)
        _PAT[P] = (vis, [sc[i] for i in ix]); _RAW[P] = (np.array(segs, float), sc)
    vis, vcol = _PAT[P]
    im = Image.new("L", shape[::-1], 0); d = ImageDraw.Draw(im); lw = max(1, int(round(0.6 * PPM)))
    want = set(FAM_THREADS[fam])
    for (x0, y0, x1, y1), c in zip(vis, vcol):
        if c in want: d.line([(x0 * PPM, y0 * PPM), (x1 * PPM, y1 * PPM)], fill=255, width=lw)
    if fam == "curls":
        import live
        rec = json.load(open(f"out/01_wave/{SIZE}/result_{P}.json"))["full"].get("chenille")
        if rec: live.draw_chenille(im, rec, bb, PPM, flat={"w1": 255, "w3": 255, "w1e": 255})
    return ndi.binary_closing(np.asarray(im) > 0, iterations=2)

def object_raster(P, bb, shape):
    """index (1-based) of the art object on top at each grid px (sew-layer order), 0 = none"""
    im = Image.new("I", shape[::-1], 0); d = ImageDraw.Draw(im)
    for i, r in sorted(enumerate(D[P], 1), key=lambda t: t[1].get("layer", 0)):
        if r["grp"] in ("FM-loop",): continue
        for q in WR.polys_of(r["geom"]):
            d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=i)
    return np.asarray(im).astype(np.int32)

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

def explain_gaps(P, gaps, bb):
    """A15: a gap >= 25 mm2 is explained only as 'keep-out edge' (inside 6 mm of the art limit, < 400 mm2) or 'moved by the
    wrap' (inside 45 mm of a seam the wrap edited, art within SHIFT); anything else is UNEXPLAINED (gapfill.py fills those).
    gaps: qa.uncovered rows in grid px-mm (from bb[0], bb[1]); converted to piece mm in place."""
    clipb = PC.clip_for(SIZE, P).boundary
    seams = [WR.SeamSide(SIZE, sm, w_).line for sm in WR.seams(SIZE) for w_ in ("A", "B") if sm[w_][0] == P]
    from shapely.geometry import box as _box
    for g in gaps:
        x, y = g["x_mm"] + bb[0], g["y_mm"] + bb[1]; g["x_mm"], g["y_mm"] = round(x, 1), round(y, 1)
        gb = _box(x - g["w_mm"] / 2, y - g["h_mm"] / 2, x + g["w_mm"] / 2, y + g["h_mm"] / 2)
        art_near = any(r["geom"].intersects(gb.buffer(SHIFT)) for r in D[P])
        # PR #27 review 2: 'moved by the wrap' (within 45 mm of a seam, art within 40 mm) excused real bare navy; it is no
        # longer an explanation - gapfill.py fills those areas from the mockup tones. Only the spec'd art limit may stay bare.
        # fix round 4 (PR #27 review of b448e33, item 1): the reference is already clipped to the art limit, so a gap near
        # the limit is mockup art INSIDE the allowed area (SL 228.9/117.0: a crest the rigid curl move left 10-15 mm short of
        # the sleeve edge). Only a sliver along the limit (< 2 mm across) is excused; gapfill.py fills the rest.
        if gb.distance(clipb) < 2.0 and min(g["w_mm"], g["h_mm"]) < 2.0: g["why"] = "keep-out edge"
        else: g["why"] = "UNEXPLAINED"
    return gaps

_CUIMG = {}
def closeup_grey12(P, shape12, up):
    """A16 reference at 12 ppm from the founder close-ups (register_closeups.py, cu_regs.json): the piece grid's render-px
    coordinates (same map + seam warp as the A14 reference) are upsampled x`up` and each point inside a close-up footprint
    samples the CLOSE-UP (4-10 px/mm, the thread grain is resolved); weight 1 there, 0 elsewhere (render only: the
    direction gate masks those tiles instead of judging blur). Artefact pixels of the sleeve composite count as no data."""
    from scipy.ndimage import zoom as _zoom, map_coordinates as _mc
    import wavetrace as _WT
    from shapely.geometry import Polygon as _Poly
    g = np.full(shape12, np.nan, np.float32); w = np.zeros(shape12, np.float32)
    regs = json.load(open("cu_regs.json")) if os.path.exists("cu_regs.json") else []
    for view, (px, py) in PXY.get(P, {}).items():
        X = _zoom(np.nan_to_num(px, nan=-1e4), up, order=1)[:shape12[0], :shape12[1]]
        Y = _zoom(np.nan_to_num(py, nan=-1e4), up, order=1)[:shape12[0], :shape12[1]]
        okv = _zoom(np.isfinite(px).astype(np.float32), up, order=0)[:shape12[0], :shape12[1]] > 0.5
        for c in regs:
            if c["view"] != view or not c["ok"]: continue
            foot = _Poly(c["footprint_render_px"]).buffer(-2.0)
            ins = okv & shapely.contains_xy(foot, X, Y) & (w == 0)
            if not ins.any(): continue
            if c["name"] not in _CUIMG:
                a, valid = _WT.closeup_pixels(c); _CUIMG[c["name"]] = (a.mean(-1), valid)
            a, valid = _CUIMG[c["name"]]; Hi = np.linalg.inv(np.array(c["H"]))
            q = Hi @ np.stack([X[ins], Y[ins], np.ones(ins.sum())]); u, v = q[0] / q[2], q[1] / q[2]
            good = _mc(valid.astype(np.float32), [v, u], order=0) > 0.5
            vals = _mc(a, [v, u], order=1)
            iy, ix = np.nonzero(ins)
            g[iy, ix] = vals; w[iy[good], ix[good]] = 1.0
    return g, w

def drops_hr_gate(P, bb):
    """Drops at 12 ppm (PR #27 review 1): a 5 mm2 drop is 80 px at 4 ppm, so one boundary pixel moved IoU by 0.15. Each
    reference drop (its traced silhouette: close-up resolution where a close-up covers it, else the x4 render trace) is
    rasterised at 12 ppm in its own window. Fix round 3: the SEWN drop is the z-buffer of every DST stitch in that window
    (sew order, house thread width 0.42 mm, each stitch shortened by the drop pull compensation = the fabric pull-in);
    a pixel counts when its TOP stitch is a drop thread of ITS motif (unit attribution by stitch midpoint, A21).
    qa.visible_segments' re-centred visible-length segments were used before: on a satin zigzag each stroke hides most of
    the previous one, so the re-centred pieces left false holes and false bare rims (BK drop 98: art = ref 0.98, gate
    0.67). Only stitches within 1.0 mm of the drop count (as near_mm for the crests: a neighbour's stray stitch no longer
    stretches its width / height). Same pass rule as qa.motif_match (IoU >= 0.70, width + height >= 80 %)."""
    PP = 12.0
    shape = (int((bb[3] - bb[1]) * PPM), int((bb[2] - bb[0]) * PPM))
    ua = art_unit_raster(P, bb, shape)
    S, sc = _RAW[P]; want = set(FAM_THREADS["drops"]); isw = np.array([c in want for c in sc])
    S = S + np.array([bb[0], bb[1], bb[0], bb[1]])
    mx = ((S[:, 0] + S[:, 2]) / 2 - bb[0]) * PPM; my = ((S[:, 1] + S[:, 3]) / 2 - bb[1]) * PPM
    ix_, iy_ = np.clip(mx.astype(int), 0, shape[1] - 1), np.clip(my.astype(int), 0, shape[0] - 1)
    su = np.where(isw, ua[iy_, ix_], 0)
    lo_x, hi_x = S[:, [0, 2]].min(1), S[:, [0, 2]].max(1); lo_y, hi_y = S[:, [1, 3]].min(1), S[:, [1, 3]].max(1)
    rows = []
    for u, g, hr in DROP_REF:
        if g.is_empty or g.area < 4.0: continue
        b = g.bounds; wb = (b[0] - 2.0, b[1] - 2.0, b[2] + 2.0, b[3] + 2.0)
        W, H = int((wb[2] - wb[0]) * PP) + 1, int((wb[3] - wb[1]) * PP) + 1
        rim = Image.new("L", (W, H), 0); d = ImageDraw.Draw(rim)
        for q in WR.polys_of(g):
            d.polygon([((x - wb[0]) * PP, (y - wb[1]) * PP) for x, y in q.exterior.coords], fill=255)
            for h in q.interiors: d.polygon([((x - wb[0]) * PP, (y - wb[1]) * PP) for x, y in h.coords], fill=0)
        sel = np.nonzero((hi_x >= wb[0]) & (lo_x <= wb[2]) & (hi_y >= wb[1]) & (lo_y <= wb[3]))[0]
        zim = Image.new("I", (W, H), 0); dz = ImageDraw.Draw(zim); lw = max(1, int(round(0.42 * PP)))
        for j, i in enumerate(sel, 1):                       # sew order: sel is sorted, last writer = top thread
            x0, y0, x1, y1 = S[i]
            L = float(np.hypot(x1 - x0, y1 - y0)); k_ = min(0.45, PULL_DR / L) if L > 0 else 0.0
            dx, dy = (x1 - x0) * k_, (y1 - y0) * k_
            dz.line([((x0 + dx - wb[0]) * PP, (y0 + dy - wb[1]) * PP), ((x1 - dx - wb[0]) * PP, (y1 - dy - wb[1]) * PP)], fill=j, width=lw)
        z = np.asarray(zim); mine = np.zeros(len(sel) + 1, bool); mine[1:] = su[sel] == u
        r_ = np.asarray(rim) > 0; o_ = ndi.binary_closing(mine[z], iterations=2)
        rr = qa.motif_match(r_, o_, PP, min_mm2=4.0, pad_mm=1.5, near_mm=1.0)
        rr = [max(rr, key=lambda x: x["area_mm2"])] if rr else []
        for x in rr:
            x["x_mm"] = round(x["x_mm"] + wb[0] - bb[0], 1); x["y_mm"] = round(x["y_mm"] + wb[1] - bb[1], 1)
            x["unit"] = u; x["ref"] = f"close-up {hr}" if hr else "render x4"; x["gate_ppm"] = PP
        rows += rr
    return rows

def gate_piece(P):
    DROP_REF.clear()
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
            # A21 (fix round 3): each wave mass vs the stitches within 1.5 mm of IT, as for crests and drops. Without it a
            # thin sewn bridge to a neighbouring mass made motif_match score the WHOLE neighbour against the band (SR 54/140:
            # a 2,490 mm2 band scored against 3,100 mm2 of stitches, IoU 0.34, although the band itself is sewn).
            rows = qa.motif_match(ref, out, PPM, min_mm2=400.0, near_mm=1.5)
        else:
            ref = rigid_ref(P, fam, bb, cls.shape); out = dst_family(P, bb, fam)
            if fam == "curls":                                     # crests: the art's lobes merge into crests, compare crest by crest
                ref = ndi.binary_closing(ref, iterations=2)
            if fam == "drops" and not ART:
                # drops: NO residual shift. The reference drop is placed by the same rigid map + wrap move as the art, and a
                # 4 mm search against the whole cream / grey family pulled small drops onto a neighbouring crest (IoU 0)
                al, sh = ref, {}; Aid, _ = ndi.label(ref)
            else:
                al, Aid, sh = align(ref, out, max_mm=4.0)           # residual registration only: the wrap's own moves are applied above
            # A21: each motif is compared with the family's stitches within near_mm of IT (touching crests / a drop sewn
            # against a crest no longer merge into one blob); 1.5 mm for crests, 1.0 mm for drops
            if fam == "drops" and not ART:
                # each drop vs its OWN stitches (A21); ref_units moved with the residual shift
                ru = np.zeros(al.shape, np.int32); lab_r, _ = ndi.label(ref)
                for kk, sl_ in enumerate(ndi.find_objects(lab_r), 1):
                    m_ = lab_r[sl_] == kk; uu = UNIT_RASTER[0][sl_][m_]; uu = uu[uu > 0]
                    if not len(uu): continue
                    ys_, xs_ = np.nonzero(Aid == kk); ru[ys_, xs_] = int(np.bincount(uu).argmax())
                rows = drops_hr_gate(P, bb)
            else:
                rows = qa.motif_match(al, out, PPM, min_mm2=4.0, near_mm=1.5 if fam == "curls" else 1.0)
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
        # PR #27 review of b448e33 (should-fix): WHY the render and DST counts differ. A DST blob in the band that touches
        # no reference motif of the family is 'extra' (a crest tip cut off by a stripe, a gap fill, a lobe at a seam edge);
        # reference motifs that share one sewn blob were 'merged' (touching crests sew as one mass).
        refd = ndi.binary_dilation(al if fam != "stripes" else ref, iterations=int(1.0 * PPM)); lab_r, n_r = ndi.label(al if fam != "stripes" else ref)
        extra = merged = 0; seen_r = {}
        for k_, a_ in enumerate(ar, 1):
            if not (lo <= a_ < hi): continue
            m_ = lab_o == k_
            if not (m_ & refd).any(): extra += 1; continue
            ids = np.unique(lab_r[ndi.binary_dilation(m_, iterations=int(1.0 * PPM))]); ids = ids[ids > 0]
            if len(ids) > 1: merged += len(ids) - 1
        res[fam] = dict(n=len(rows), passed=ok, rows=rows, shifts=sh, dst_count=dst_count, dst_extra=extra, ref_merged=merged)
    # stitch direction (A16): DST stitch angles vs the render's grain (input pixels, same map + seam warp), 8 mm tiles
    g = GREY.get(P)
    if g is not None and not ART and "--nodir" not in sys.argv:
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
        cg, cw = closeup_grey12(P, g12.shape, UP)
        g12 = np.where(cw > 0, cg, g12); W12 = cw
        dm_plain = qa.direction_match(g12, P12, segs, tile_mm=8.0, weight=W12)     # every 8 mm tile pools every object in it
        # per motif family (A16 sets the direction per family; WIP patch 19 Oct): stripes + rope cords on 8 mm tiles, foam
        # curls and drops turn within a few mm -> 4 mm tiles. Family of a stitch = the art region under its midpoint.
        fam_of = family_raster(P, bb, g.shape)
        vis = qa.visible_segments(segs, (0.0, 0.0, g.shape[1] / PPM, g.shape[0] / PPM), ppm=P12)
        by = {1: [], 2: [], 3: []}
        for q in vis:
            cx, cy = int((q[0] + q[2]) / 2 * PPM), int((q[1] + q[3]) / 2 * PPM)
            if 0 <= cy < fam_of.shape[0] and 0 <= cx < fam_of.shape[1] and fam_of[cy, cx] in by: by[fam_of[cy, cx]].append(q)
        # per OBJECT (konpeito ENGINE_NOTES 14, qa.direction_match groups): a tile on the border of two stripes (or a stripe
        # and a rope cord) holds two deliberate directions; it is judged on the object with the most visible thread in it
        obj = object_raster(P, bb, g.shape)
        grp_of = {}
        for k in by:
            gl = []
            for q in by[k]:
                cx, cy = int((q[0] + q[2]) / 2 * PPM), int((q[1] + q[3]) / 2 * PPM)
                gl.append(int(obj[cy, cx]) if 0 <= cy < obj.shape[0] and 0 <= cx < obj.shape[1] else 0)
            grp_of[k] = gl
        fams = {}
        for k, nm, tm, ms in ((1, "stripes", 8.0, 12), (2, "foam", 4.0, 6), (3, "drops", 4.0, 4)):
            f_ = qa.direction_match(g12, P12, by[k], tile_mm=tm, min_stitches=ms, visible=False, weight=W12, groups=grp_of[k])
            fams[nm] = dict(tile_mm=tm, tiles=f_["tiles"], pct_ok=f_["pct_ok"], fail_dev=len(f_["fail_dev"]), fail_chaos=len(f_["fail_chaos"]), masked=f_.get("masked", 0),
                            dev_tiles=[dict(t_, at_mm=[round(t_["at_mm"][0] + bb[0], 1), round(t_["at_mm"][1] + bb[1], 1)]) for t_ in f_["fail_dev"]][:400],
                            chaos_tiles=[dict(t_, at_mm=[round(t_["at_mm"][0] + bb[0], 1), round(t_["at_mm"][1] + bb[1], 1)]) for t_ in f_["fail_chaos"]][:400])
        # fix round 4: the all-visible headline is judged PER OBJECT as the families are (qa.direction_match groups,
        # konpeito ENGINE_NOTES 14): an 8 mm tile on the border of a foam crest and a stripe holds two deliberate
        # directions and read as "chaos" by construction. The pooled figure is kept as pct_ok_pooled (reported on G8).
        allv = by[1] + by[2] + by[3]; allg = grp_of[1] + grp_of[2] + grp_of[3]
        dm = qa.direction_match(g12, P12, allv, tile_mm=8.0, visible=False, weight=W12, groups=allg)
        dm["pct_ok_pooled"] = dm_plain["pct_ok"]; dm["pooled_tiles"] = dm_plain["tiles"]
        dm["pooled_chaos"] = len(dm_plain["fail_chaos"]); dm["pooled_dev"] = len(dm_plain["fail_dev"])
        dm["by_family"] = fams; dm["ref_ppm"] = P12; dm["source"] = "founder close-ups (4-10 px/mm) inside their footprints; render-only tiles masked"; dm["closeup_share"] = round(float((W12 > 0).mean()), 3)
        for k in ("fail_dev", "fail_chaos"):
            for t_ in dm[k]: t_["at_mm"] = [round(t_["at_mm"][0] + bb[0], 1), round(t_["at_mm"][1] + bb[1], 1)]
        dm["tile_mm"] = 8.0; res["direction"] = dm
    # coverage (A15): any-art reference vs any stitch
    ref_any = np.isin(cls, [WT.NAMES.index(n) for n in WT.CREAM + WT.GREY + WT.BLUES]); ref_any = ndi.binary_opening(ref_any, iterations=1)
    out_any = dst_family(P, bb, "curls") | dst_family(P, bb, "stripes") | dst_family(P, bb, "drops")
    out_any = ndi.binary_dilation(out_any, iterations=int(1.0 * PPM))
    gaps = explain_gaps(P, qa.uncovered(ref_any, out_any, PPM), bb)
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
