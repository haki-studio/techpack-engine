"""Stitch-check + stitch-count for a knocked-out layer stack."""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely.ops import unary_union
from shapely.geometry import Polygon

LINE_ROLES = ("outline", "texture", "needles", "mist", "vein")
SATIN_ROLES = ("blossom", "bud", "leaf", "bamboo", "hub", "calyx", "highlight", "inner", "snow shadow", "eye", "stamens")

def is_line(role): return any(k in role for k in LINE_ROLES)

def rast(g, px):
    minx, miny, maxx, maxy = g.bounds
    W, H = int((maxx-minx)*px) + 8, int((maxy-miny)*px) + 8
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    polys = [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
    for p in polys:
        T = lambda cs: [((x-minx)*px+4, (y-miny)*px+4) for x, y in cs]
        d.polygon(T(p.exterior.coords), fill=255)
        for r in p.interiors: d.polygon(T(r.coords), fill=0)
    return np.array(im) > 127

def disk(mm, px):
    r = mm*px/2; n = int(np.ceil(r)); y, x = np.ogrid[-n:n+1, -n:n+1]; return x*x + y*y <= r*r

def check_geom(g, min_stroke, min_gap, min_counter):
    span = max(g.bounds[2]-g.bounds[0], g.bounds[3]-g.bounds[1])
    px = 40 if span < 60 else (20 if span < 150 else 12)
    ink = rast(g, px)
    if ink.sum() == 0: return None
    thin = ink & ~ndi.binary_opening(ink, structure=disk(min_stroke, px))
    # separate tapered tips (short thin bits) from real thin runs (thin for > 2.5 mm)
    lab, n = ndi.label(thin)
    long_area = 0.0; n_long = 0
    if n:
        sl = ndi.find_objects(lab)
        for i, s in enumerate(sl, 1):
            ext = max(s[0].stop - s[0].start, s[1].stop - s[1].start) / px
            if ext > 2.5:
                a = (lab[s] == i).sum() / px**2
                long_area += a; n_long += 1
    return dict(area=ink.sum()/px**2, thin_area=thin.sum()/px**2, long_area=long_area, n_long=n_long,
                small_holes=[], merges=0, parts=0)

def rast_box(g, bounds, px):
    minx, miny, maxx, maxy = bounds
    W, H = int((maxx-minx)*px), int((maxy-miny)*px)
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    polys = [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
    for p in polys:
        T = lambda cs: [((xx-minx)*px, (yy-miny)*px) for xx, yy in cs]
        d.polygon(T(p.exterior.coords), fill=255)
        for r in p.interiors: d.polygon(T(r.coords), fill=0)
    return np.array(im) > 127

def silhouette_check(vis, W, H, px=25, tile=120.0, min_gap=0.5, min_hole=0.6):
    """Whole design (all threads): bare-fabric gaps narrower than min_gap that thread will close,
    and enclosed fabric holes smaller than min_hole. Tiled."""
    from shapely.geometry import box
    U = unary_union([g for _, _, g, _ in vis if not g.is_empty])
    gaps_area, n_holes, n_gaps = 0.0, 0, 0
    pad = 6.0
    y = 0.0
    while y < H:
        x = 0.0
        while x < W:
            B = box(x - pad, y - pad, x + tile + pad, y + tile + pad)
            g = U.intersection(B)
            if not g.is_empty:
                ink = rast_box(g, B.bounds, px)
                m = int(pad*px)
                core = np.zeros_like(ink); core[m:-m, m:-m] = True
                fill = (ndi.binary_closing(ink, structure=disk(min_gap, px)) | ink) & ~ink & core
                lab, n = ndi.label(fill)
                if n:
                    sizes = np.array(ndi.sum(fill, lab, range(1, n+1))) / px**2
                    real = sizes > 0.05
                    n_gaps += int(real.sum()); gaps_area += float(sizes[real].sum())
                bg = ~ink; lab, n = ndi.label(bg)
                if n:
                    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
                    bdt = ndi.distance_transform_edt(bg)
                    mx = ndi.maximum(bdt, lab, index=np.arange(1, n+1))
                    n_holes += sum(1 for i, mv in zip(range(1, n+1), mx) if i not in border and mv > 1 and 2*mv/px < min_hole)
            x += tile
        y += tile
    return dict(gaps=n_gaps, gap_area=gaps_area, small_holes=n_holes)

def stitch_report(vis):
    """vis: [(z, colour, geom, role)] -> per (colour, class) stats + stitch estimate."""
    groups = {}
    for z, col, g, role in vis:
        if g.is_empty: continue
        cls = "line" if is_line(role) else ("satin" if any(k in role for k in SATIN_ROLES) else "fill")
        groups.setdefault((col, cls), []).append(g)
    rows = []
    for (col, cls), gs in sorted(groups.items()):
        u = unary_union(gs)
        if cls == "line": th = (0.6, 0.35, 0.45)
        else: th = (0.8, 0.5, 0.6)
        parts = [u] if u.geom_type == "Polygon" else list(u.geoms)
        agg = dict(area=0, thin_area=0, long_area=0, n_long=0, small_holes=0, merges=0, parts=0)
        for p in parts:
            if p.area < 0.05: continue
            r = check_geom(p, *th)
            if not r: continue
            agg["area"] += r["area"]; agg["thin_area"] += r["thin_area"]
            agg["long_area"] += r["long_area"]; agg["n_long"] += r["n_long"]
            agg["small_holes"] += len(r["small_holes"]); agg["merges"] += r["merges"]; agg["parts"] += r["parts"]
        area = u.area
        if cls == "line":
            length = area / 0.7
            stitches = length * 1.36                # triple run, 2.2 mm stitch
        elif cls == "satin":
            stitches = area * 1.25                  # satin 0.4 spacing + underlay + pull comp
        else:
            stitches = area * 0.90                  # tatami 0.4 spacing, 4 mm length, + underlay
        rows.append(dict(col=col, cls=cls, area=area, thin_pct=100*agg["thin_area"]/max(agg["area"], 1e-9),
                         thin_area=agg["thin_area"], long_pct=100*agg["long_area"]/max(agg["area"], 1e-9),
                         n_long=agg["n_long"], small_holes=agg["small_holes"], merges=agg["merges"],
                         stitches=stitches))
    return rows


# ---------------------------------------------------------------- fidelity gates (LESSONS A14, A15)
def motif_match(ref, out, ppm, min_mm2=4.0, iou_min=0.70, ratio_min=0.80, pad_mm=3.0, near_mm=None, out_stops=None):
    """Every motif in the reference vs what was stitched, one row per motif (LESSONS A14).
    ref, out: bool masks on the SAME garment-mm grid (ppm px per mm). ref = the motif family traced from the mockup /
    close-up (e.g. the cream islet pixels); out = the same family rendered from the shipped DST. A motif passes when the
    stitched shape overlapping it has IoU >= iou_min and keeps >= ratio_min of the reference width AND height (a
    generated stand-in of the right size but the wrong silhouette fails here, a flattened one fails on height).
    ref MUST be derived from input pixels only (mockup / close-up / reference image) - never from the art, scene
    data or a template, or the gate only proves DST == art (circular; Koi Rev B review).
    Touching motifs (letters, overlapping candies; konpeito ENGINE_NOTES 3): with out_stops, `out` is a dict
    {stop: mask} (qa.dst_stop_masks) and only the stops in out_stops (the family's own stops) are compared; with
    near_mm, each motif is compared only with the stitches within near_mm of IT, so a neighbour's stitched shape that
    touches it no longer merges into one DST blob. Defaults (None, None) = the old behaviour."""
    if out_stops is not None:
        ms = [out[s] for s in out_stops if s in out]
        out = np.any(ms, axis=0) if ms else np.zeros(ref.shape, bool)
    lab, n = ndi.label(ref); rows = []; pad = int(round(pad_mm * ppm))
    it = max(1, int(round(near_mm * ppm))) if near_mm is not None else 0
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        y0, y1 = max(0, sl[0].start - pad), min(ref.shape[0], sl[0].stop + pad)
        x0, x1 = max(0, sl[1].start - pad), min(ref.shape[1], sl[1].stop + pad)
        r = lab[y0:y1, x0:x1] == k; area = r.sum() / ppm**2
        if area < min_mm2: continue
        win = out[y0:y1, x0:x1]
        if it: win = win & ndi.binary_dilation(r, iterations=it)
        ol, _ = ndi.label(win); keep = np.unique(ol[r & (ol > 0)])
        o = np.isin(ol, keep) & (ol > 0)
        iou = (r & o).sum() / max((r | o).sum(), 1)
        def ext(m, ax):
            idx = np.nonzero(m.any(axis=ax))[0]; return (idx[-1] - idx[0] + 1) / ppm if len(idx) else 0.0
        wr, hr = ext(o, 0) / max(ext(r, 0), 1e-9), ext(o, 1) / max(ext(r, 1), 1e-9)
        ok = iou >= iou_min and min(wr, 1/max(wr, 1e-9)) >= ratio_min and min(hr, 1/max(hr, 1e-9)) >= ratio_min
        rows.append(dict(motif=k, x_mm=round((x0 + x1) / 2 / ppm, 1), y_mm=round((y0 + y1) / 2 / ppm, 1),
                         area_mm2=round(float(area), 1), iou=round(float(iou), 2), w_ratio=round(float(wr), 2), h_ratio=round(float(hr), 2), ok=bool(ok)))
    return rows


# ---------------------------------------------------------------- thin strokes + file masks (ENGINE_PLAN M5, konpeito ENGINE_NOTES 4/8/9)
def _prune(sk, n):
    """remove skeleton spurs shorter than n px (endpoint erosion, then regrow from the surviving endpoints)"""
    k = np.ones((3, 3)); cur = sk.copy()
    for _ in range(n):
        nb = ndi.convolve(cur.astype(int), k, mode="constant") - cur
        cur = cur & ~(nb <= 1)
    nb = ndi.convolve(cur.astype(int), k, mode="constant") - cur
    grow = cur & (nb == 1)
    for _ in range(n): grow = ndi.binary_dilation(grow, structure=np.ones((3, 3))) & sk
    return cur | grow


def skeleton(mask, ppm, spur_mm=0.6):
    """(pruned skeleton, smoothed mask) of a stroke mask"""
    from skimage.morphology import skeletonize
    m = ndi.gaussian_filter(mask.astype(float), 1.0) > 0.5
    return _prune(skeletonize(m), max(1, int(spur_mm * ppm))), m


def centreline_match(ref, out, ppm, name="", pull=0.0, near_mm=1.0, d_max=0.5, w_tol=0.20, spur_mm=0.6):
    """Thin strokes (< 1.2 mm: lettering, line art) gated on CENTRELINES, not area (konpeito ENGINE_NOTES 4 + 8,
    LESSONS A19): a 0.2 mm registration error on a 0.7 mm line already costs ~30 % IoU, so area IoU fails good files.
    Skeleton-to-skeleton mean distance (symmetric mean of both directions) <= d_max mm AND the visible width (2 x the
    distance transform on the skeleton, median; minus 2 x pull) within +-w_tol of the reference's.
    ref: input-pixel / founder-art mask; out: the DST's stitches of this family's stop(s) drawn at thread width
    (qa.dst_stop_masks), limited here to near_mm of ref. Returns dict(family, mean_d, p90_d, w_ref, w_dst, ratio, ok)."""
    from scipy.spatial import cKDTree
    o = out & ndi.binary_dilation(ref, iterations=max(1, int(near_mm * ppm)))
    sr, mr = skeleton(ref, ppm, spur_mm); so, mo = skeleton(o, ppm, spur_mm)
    pts = lambda sk: np.c_[(np.nonzero(sk)[1] + 0.5) / ppm, (np.nonzero(sk)[0] + 0.5) / ppm]
    R, O = pts(sr), pts(so)
    if len(O) == 0 or len(R) == 0:
        return dict(family=name, mean_d=None, p90_d=None, w_ref=None, w_dst=None, ratio=None, ok=False)
    d1, _ = cKDTree(O).query(R); d2, _ = cKDTree(R).query(O)
    md = float((d1.mean() + d2.mean()) / 2); p90 = float(np.percentile(np.r_[d1, d2], 90))
    def width(m, sk):
        v = 2 * ndi.distance_transform_edt(m)[sk] / ppm; return float(np.median(v)) if v.size else 0.0
    wr = width(mr, sr); wo = width(mo, so) - 2 * pull; ratio = wo / wr if wr else 0.0
    return dict(family=name, mean_d=round(md, 2), p90_d=round(p90, 2), w_ref=round(wr, 2), w_dst=round(wo, 2),
                ratio=round(ratio, 2), ok=bool(md <= d_max and abs(ratio - 1) <= w_tol))


def dst_stitches(dst, origin=(0.0, 0.0)):
    """[(stop index 0-based, (x0, y0), (x1, y1))] of every SEWN stitch in the DST read-back, garment mm"""
    import pyembroidery as pe
    p = pe.read(dst); out = []; ci = 0; prev = None; ox, oy = origin
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; P = (x / 10.0 + ox, y / 10.0 + oy)
        if k == pe.STITCH:
            if prev is not None and prev != P: out.append((ci, prev, P))
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k == pe.TRIM: prev = None
        elif k == pe.JUMP: prev = P
        elif k == pe.END: break
    return out


def dst_stop_masks(dst, origin, shape, ppm, thread_d=0.40, to_mm=None, close=2):
    """{stop index: bool mask} of the DST's sewn stitches per colour stop, drawn at the thread's visible diameter
    (thread_d mm, or {stop: d}) on a (H, W) grid at ppm px/mm. to_mm(x, y) maps garment mm -> grid mm (a placement
    frame); needle-gap pin holes (< 0.3 mm2) are closed, so they are not read as counters."""
    from PIL import Image, ImageDraw
    Hh, Ww = shape; ims = {}
    for ci, a, b in dst_stitches(dst, origin):
        if ci not in ims: ims[ci] = Image.new("L", (Ww, Hh), 0)
        d = thread_d.get(ci, 0.40) if isinstance(thread_d, dict) else thread_d
        A, B = (to_mm(*a), to_mm(*b)) if to_mm else (a, b)
        ImageDraw.Draw(ims[ci]).line([(A[0] * ppm, A[1] * ppm), (B[0] * ppm, B[1] * ppm)], fill=255, width=max(1, int(round(d * ppm))))
    out = {}
    for ci, im in ims.items():
        m = ndi.binary_closing(np.array(im) > 0, iterations=close)
        lab, n = ndi.label(~m)
        if n:
            sz = ndi.sum(np.ones_like(lab), lab, range(1, n + 1)) / ppm ** 2
            m |= np.r_[False, sz < 0.3][lab]
        out[ci] = m
    return out


def exposed_stitches(dst, origin, stop_geoms, halo=0.35, min_mm=1.0, min_ex=None):
    """Travel floats on the FILE (konpeito ENGINE_NOTES 9): every sewn stitch of stop i must lie on stop i's own art
    (+ halo) or under art sewn by a LATER stop, measured on the exact geometry (shapely), never on a raster.
    stop_geoms: [geometry per stop, in the file's stop order]. Returns [(stop 1-based, x, y, exposed mm)] for stitches
    longer than min_mm with more than min_ex (default min_mm) outside that cover; [] = no floats. The konpeito Rev A
    gate used (0.35, 1.0); M5 patches gate at halo 0.25 (pull comp 0.15 + the DST 0.1 mm grid),
    min_mm 0.5, min_ex 0.3 (a thread across a 0.7 mm gap between two strokes shows)."""
    import math
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    from shapely.prepared import prep
    later = [None] * len(stop_geoms); acc = None
    for i in range(len(stop_geoms) - 1, -1, -1):
        later[i] = acc; acc = stop_geoms[i] if acc is None else unary_union([acc, stop_geoms[i]])
    cover = [unary_union([g.buffer(halo)] + ([later[i]] if later[i] is not None else [])) for i, g in enumerate(stop_geoms)]
    pc = [prep(c) for c in cover]; out = []
    for ci, A, B in dst_stitches(dst, origin):
        if ci >= len(cover) or math.dist(A, B) < min_mm: continue
        ls = LineString([A, B])
        if pc[ci].contains(ls): continue
        ex = ls.difference(cover[ci]).length
        if ex > (min_mm if min_ex is None else min_ex): out.append((ci + 1, round((A[0] + B[0]) / 2, 1), round((A[1] + B[1]) / 2, 1), round(ex, 2)))
    return out


def uncovered(ref, out, ppm, min_mm2=25.0, open_mm=1.0):
    """Areas the reference says are embroidered but the shipped DST leaves bare (LESSONS A15), largest first.
    ref = design-coverage mask from the mockup AFTER garment details (zip shadow, folds, seams, welts) are masked out;
    out = stitched coverage rendered from the DST. Gaps narrower than open_mm (normal knockouts/rows) are ignored."""
    gap = ndi.binary_opening(ref & ~out, structure=disk(open_mm, ppm)) if open_mm > 0 else ref & ~out
    lab, _ = ndi.label(gap); rows = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        a = (lab[sl] == k).sum() / ppm**2
        if a >= min_mm2:
            rows.append(dict(x_mm=round((sl[1].start + sl[1].stop) / 2 / ppm, 1), y_mm=round((sl[0].start + sl[0].stop) / 2 / ppm, 1),
                             w_mm=round((sl[1].stop - sl[1].start) / ppm, 1), h_mm=round((sl[0].stop - sl[0].start) / ppm, 1), area_mm2=round(float(a), 1)))
    return sorted(rows, key=lambda r: -r["area_mm2"])



CONSTRUCTED = ("WALL", "ROOF", "TMB", "STONE")


def _axial_spread(angles_rad, weights):
    """weighted spread (deg) of axial angles (0 == 180): circular std on the doubled circle -> (spread, R, mean deg)."""
    import math as _m
    w = np.asarray(weights, float); a = np.asarray(angles_rad, float); W = w.sum()
    if W <= 0: return 0.0, 1.0, 0.0
    C = float((w * np.cos(2 * a)).sum()); S = float((w * np.sin(2 * a)).sum())
    R = _m.hypot(C, S) / W
    spread = _m.degrees(_m.sqrt(max(0.0, -2 * _m.log(max(R, 1e-9))))) / 2
    return spread, R, _m.degrees(0.5 * _m.atan2(S, C)) % 180


def angle_coherence(regions, groups=CONSTRUCTED, max_spread_deg=10.0, satin_min_aspect=2.5, key="part", segs=None,
                    min_segs=12, min_len=0.6, seg_parts=None):
    """Stitch-direction discipline for constructed parts (LESSONS A16, DIGITIZING_PRINCIPLES rule 2).
    regions: dicts with geom, stype ('satin'/'tatami'/...), angle (deg), grp, and a PART id under `key` (default "part").
    Constructed = grp in `groups`. Returns rows of failures (empty = pass):
      - every constructed region MUST carry a part id; missing -> ValueError. (Grouping by a missing id pooled
        unrelated walls into one group, or let fragments escape the check; ENGINE_PLAN M0.)
      - a constructed part's angle must be declared: "auto" / None -> `undeclared-angle` (a direction is a design
        decision, never a by-product of the traced blob).
      - satin only on stroke-like shapes (aspect >= satin_min_aspect): `satin-on-blob`.
      - per (part, grp) the fill angles stay within max_spread_deg: `angle-spread`. When `segs` (VISIBLE DST segments,
        qa.visible_segments, same mm frame as the geoms) are given, the spread is measured on the stitches actually seen
        inside the part (source "dst", needs >= min_segs); otherwise on the declared angles (source "declared").
        With `seg_parts` (one part id per seg, e.g. the plan's ids carried through compile; None = travel) a part's
        stitches are the ones ATTRIBUTED to it, not whatever lies inside its outline (a neighbour's 1 mm cut-under
        overlap or a blend no longer counts against it; source "dst-part").
      - with segs given, a constructed fill part that shows fewer than min_segs visible stitches: `no-visible-stitches`
        (it is buried, cut away or never sewn: the direction cannot be checked, so it cannot pass silently)."""
    import math as _m
    from collections import defaultdict
    by = defaultdict(list); geoms = defaultdict(list); bad = []
    missing = [r for r in regions if r.get("grp") in groups and not r["geom"].is_empty and r.get(key) is None]
    if missing:
        raise ValueError(f"angle_coherence: {len(missing)} constructed region(s) {sorted({r['grp'] for r in missing})} have no "
                         f"part id under key {key!r}. Every wall / roof / member is its own part with one deliberate "
                         f"direction (DIGITIZING_PRINCIPLES rule 2): give each region its part id.")
    for r in regions:
        if r.get("grp") not in groups or r["geom"].is_empty: continue
        g = r["geom"]; A = g.area; part = r[key]
        c = list(g.minimum_rotated_rectangle.exterior.coords) if g.minimum_rotated_rectangle.geom_type == "Polygon" else []
        e = sorted(_m.hypot(c[i+1][0]-c[i][0], c[i+1][1]-c[i][1]) for i in range(4)) if len(c) >= 5 else [1.0, 1.0, 1.0, 1.0]
        aspect = e[-1] / max(e[0], 1e-6)
        ang = r.get("angle")
        if ang is None or (isinstance(ang, str) and ang.lower() == "auto"):
            bad.append(dict(kind="undeclared-angle", part=part, unit=r.get("unit"), grp=r["grp"], area_mm2=round(A, 1), stype=r.get("stype")))
        if r.get("stype") == "satin" and aspect < satin_min_aspect and A > 2.0:
            bad.append(dict(kind="satin-on-blob", part=part, unit=r.get("unit"), grp=r["grp"], area_mm2=round(A, 1), aspect=round(aspect, 2)))
        if r.get("stype") != "satin":
            geoms[(part, r["grp"])].append(g)
            if isinstance(ang, (int, float)): by[(part, r["grp"])].append((float(ang) % 180, A))
    measured = {}; src_dst = "dst"
    if segs is not None:
        from shapely import contains_xy
        S = np.asarray(segs, float).reshape(-1, 4); L = np.hypot(S[:, 2] - S[:, 0], S[:, 3] - S[:, 1]); keep = L >= min_len
        if seg_parts is not None:
            if len(seg_parts) != len(S): raise ValueError(f"angle_coherence: {len(seg_parts)} seg_parts for {len(S)} segs")
            P = np.asarray([("" if q is None else str(q)) for q in seg_parts], object)[keep]; src_dst = "dst-part"
        S, L = S[keep], L[keep]
        mx, my = (S[:, 0] + S[:, 2]) / 2, (S[:, 1] + S[:, 3]) / 2; ang = np.arctan2(S[:, 3] - S[:, 1], S[:, 2] - S[:, 0])
        for k, gs in geoms.items():
            if seg_parts is not None:
                inside = np.nonzero(P == str(k[0]))[0]
            else:
                u = unary_union(gs); b = u.bounds
                idx = np.nonzero((mx >= b[0]) & (mx <= b[2]) & (my >= b[1]) & (my <= b[3]))[0]
                inside = idx[contains_xy(u, mx[idx], my[idx])] if len(idx) else idx
            if len(inside) >= min_segs: measured[k] = _axial_spread(ang[inside], L[inside]) + (len(inside),)
            else: bad.append(dict(kind="no-visible-stitches", part=k[0], grp=k[1], n=int(len(inside)), min_segs=min_segs))
    for k in sorted(set(by) | set(measured), key=str):
        part, grp = k
        if k in measured:
            spread, R, mean, n = measured[k]; src = src_dst
        else:
            v = by[k]
            if len(v) < 2: continue
            spread, R, mean = _axial_spread([_m.radians(t) for t, _ in v], [a for _, a in v]); n = len(v); src = "declared"
        if spread > max_spread_deg:
            bad.append(dict(kind="angle-spread", part=part, grp=grp, n=n, spread_deg=round(spread, 1), source=src))
    return bad



def dst_segments(dst, origin=(0.0, 0.0)):
    """stitch segments (x0, y0, x1, y1) in mm from a written DST, origin added (to put them on a garment / ref grid)."""
    import pyembroidery as pe
    p = pe.read(dst); out = []; prev = None; ox, oy = origin
    for x, y, c in p.stitches:
        k = c & pe.COMMAND_MASK
        if k == pe.STITCH:
            q = (x / 10.0 + ox, y / 10.0 + oy)
            if prev is not None and prev != q: out.append((prev[0], prev[1], q[0], q[1]))
            prev = q
        else: prev = None
    return out


def dst_runs(dst, origin=(0.0, 0.0)):
    """The DST as sewn RUNS: continuous needle-down stitching between trims / jumps / colour changes, in sew order.
    Returns [dict(stop=colour stop index (0-based), segs=[(x0, y0, x1, y1), ...])] in mm, origin added. A run is the
    finest object a DST alone can tell apart (underlay + its fill sew as one run; hidden travel joins objects).
    Concatenating every run's segs gives exactly qa.dst_segments."""
    import pyembroidery as pe
    p = pe.read(dst); runs = []; cur = []; prev = None; stop = 0; ox, oy = origin
    for x, y, c in p.stitches:
        k = c & pe.COMMAND_MASK
        if k == pe.STITCH:
            q = (x / 10.0 + ox, y / 10.0 + oy)
            if prev is not None and prev != q: cur.append((prev[0], prev[1], q[0], q[1]))
            prev = q
            continue
        if cur: runs.append(dict(stop=stop, segs=cur))
        cur = []; prev = None
        if k == pe.COLOR_CHANGE: stop += 1
    if cur: runs.append(dict(stop=stop, segs=cur))
    return runs


def clip_segments(segs, bounds):
    """Segments clipped to the box bounds=(x0, y0, x1, y1) (Liang-Barsky), sew order kept, outside ones dropped."""
    x0, y0, x1, y1 = bounds; out = []
    for a, b, c, d in segs:
        dx, dy = c - a, d - b; t0, t1 = 0.0, 1.0; ok = True
        for p_, q_ in ((-dx, a - x0), (dx, x1 - a), (-dy, b - y0), (dy, y1 - b)):
            if p_ == 0:
                if q_ < 0: ok = False; break
            else:
                t = q_ / p_
                if p_ < 0: t0 = max(t0, t)
                else: t1 = min(t1, t)
                if t0 > t1: ok = False; break
        if ok and t1 > t0: out.append((a + t0 * dx, b + t0 * dy, a + t1 * dx, b + t1 * dy))
    return out


def visible_segments(segs, bounds, ppm=12.0, width_mm=0.42, min_vis_mm=0.3, return_index=False):
    """The TOP layer of the sew-out (what the eye and Hatch's live view see), read from the DST alone.
    segs: stitch segments (x0, y0, x1, y1) in mm, in SEW ORDER; bounds: (x0, y0, x1, y1) mm of the area to look at.
    Segments are drawn in sew order at thread width on an index raster (a z-buffer: last writer wins). Each keeps its
    own angle and its VISIBLE length, re-centred on its visible pixels. Underlay (90-degree lattice, edge runs) and
    hidden travel that a later fill covers drop out; a fan or a blob satin on top stays a fan. Promoted from
    projects/castle-falls-jacket/gates_dir.py (ENGINE_NOTES 17). Below 12 ppm a 0.42 mm thread is under 5 px and rows
    merge, which is why direction_match refuses lower resolutions. return_index=True also returns, per visible segment,
    the index of the input segment it came from (to carry part ids through)."""
    import math as _m
    bx0, by0, bx1, by1 = bounds
    W, H = int(_m.ceil((bx1 - bx0) * ppm)) + 2, int(_m.ceil((by1 - by0) * ppm)) + 2
    im = Image.new("I", (W, H), 0); d = ImageDraw.Draw(im); w = max(1, int(round(width_mm * ppm)))
    for i, (x0, y0, x1, y1) in enumerate(segs, 1):
        d.line([((x0 - bx0) * ppm, (y0 - by0) * ppm), ((x1 - bx0) * ppm, (y1 - by0) * ppm)], fill=i, width=w)
    a = np.asarray(im); N = len(segs) + 1
    n = np.zeros(N); sx = np.zeros(N); sy = np.zeros(N); xs = np.arange(W, dtype=float)
    for r0 in range(0, H, 512):                                  # row blocks: bounded memory on a whole back at 12 ppm
        blk = a[r0:r0 + 512]; h = blk.shape[0]; flat_ = blk.ravel()
        n += np.bincount(flat_, minlength=N)
        sx += np.bincount(flat_, np.tile(xs, h), minlength=N)
        sy += np.bincount(flat_, np.repeat(np.arange(r0, r0 + h, dtype=float), W), minlength=N)
    out = []; src = []
    for i in np.nonzero(n[1:])[0] + 1:
        x0, y0, x1, y1 = segs[i - 1]; L = _m.hypot(x1 - x0, y1 - y0)
        if L <= 0: continue
        vis = min(L, n[i] / (w * ppm))                            # visible length in mm
        if vis < min_vis_mm: continue
        cx, cy = sx[i] / n[i] / ppm + bx0, sy[i] / n[i] / ppm + by0
        ux, uy = (x1 - x0) / L / 2 * vis, (y1 - y0) / L / 2 * vis
        out.append((cx - ux, cy - uy, cx + ux, cy + uy)); src.append(int(i - 1))
    return (out, src) if return_index else out


def direction_match(ref, ppm, segs, tile_mm=8.0, min_len=0.6, ref_coh=0.25, max_dev_deg=25.0, chaos_R=0.55, min_stitches=12,
                    visible=True, min_ppm=12.0, width_mm=0.42, weight=None, min_weight=0.6, groups=None):
    """Stitch DIRECTION vs the reference, everywhere (LESSONS A16): every motif, not only buildings.
    ref: grey image (2-D array) of the mockup / close-up mapped to garment mm (ppm px per mm), INPUT PIXELS ONLY, at
    ppm >= min_ppm (12). Below that a thread is under 5 px, the structure tensor reads blur and the visible-layer
    z-buffer merges rows, so a lower ppm raises ValueError (build the reference with digitize.extract.register).
    segs: DST stitch segments in the same mm frame, in SEW ORDER (qa.dst_segments). With visible=True (default) only the
    VISIBLE top layer is judged (qa.visible_segments), so underlay and buried travel no longer drag the score down.
    Per tile:
      - DST direction = axial mean of stitch angles (length-weighted), with coherence R (1 = all parallel, 0 = random)
      - reference direction = thread direction from the structure tensor of the image (the visible thread grain)
    A tile FAILS when (a) the reference shows a clear thread direction and the DST deviates > max_dev_deg, or
    (b) the DST stitches in the tile point every which way (R < chaos_R): fans, blob satins, random fills.
    weight: optional (H, W) array of how much each reference pixel comes from a real close-up (register.reference's
    closeup_weight). 12 ppm is a sampling grid, not a detail guarantee: where the pixels are only the upscaled mockup the
    grain is blur, so tiles whose mean weight is < min_weight are MASKED (not judged, counted in `masked`).
    Returns dict(tiles, ok, ok_tiles=[centres], fail_dev=[...], fail_chaos=[...], pct_ok, pct_chaos, masked) with tile
    centres in mm."""
    import math as _m
    from scipy import ndimage as _ndi
    if ppm < min_ppm:
        raise ValueError(f"direction_match: the reference is {ppm} px/mm, below the {min_ppm} px/mm minimum. At that resolution "
                         f"a 0.42 mm thread is under 5 px, so the thread grain is blur and underlay cannot be told from the top "
                         f"layer (ENGINE_PLAN M0). Rebuild the reference at >= {min_ppm} ppm "
                         f"(engine/digitize/extract/register.py) and pass the DST segments in sew order.")
    g = np.asarray(ref, float)
    if g.ndim == 3: g = g[..., :3] @ np.array([0.299, 0.587, 0.114])
    H, W = g.shape
    if visible and groups is not None:
        segs, _ix = visible_segments(segs, (0.0, 0.0, W / ppm, H / ppm), ppm=ppm, width_mm=width_mm, return_index=True)
        groups = [groups[i] for i in _ix]
    elif visible: segs = visible_segments(segs, (0.0, 0.0, W / ppm, H / ppm), ppm=ppm, width_mm=width_mm)
    gy, gx = np.gradient(_ndi.gaussian_filter(g, 0.6))
    sig = tile_mm * ppm / 3.0
    Jxx = _ndi.gaussian_filter(gx * gx, sig); Jyy = _ndi.gaussian_filter(gy * gy, sig); Jxy = _ndi.gaussian_filter(gx * gy, sig)
    T = int(round(tile_mm * ppm)); acc = {}; masked = 0
    if weight is not None:
        wt = np.asarray(weight, float)
        if wt.shape != g.shape: raise ValueError(f"direction_match: weight {wt.shape} != reference {g.shape}")
    for si, (x0, y0, x1, y1) in enumerate(segs):
        L = _m.hypot(x1 - x0, y1 - y0)
        if L < min_len: continue
        cx, cy = (x0 + x1) / 2 * ppm, (y0 + y1) / 2 * ppm
        if not (0 <= cx < W and 0 <= cy < H): continue
        a = _m.atan2(y1 - y0, x1 - x0); key = (int(cy // T), int(cx // T))
        if groups is not None: key = key + (groups[si],)
        c, s_, n, w = acc.get(key, (0.0, 0.0, 0, 0.0))
        acc[key] = (c + L * _m.cos(2 * a), s_ + L * _m.sin(2 * a), n + 1, w + L)
    if groups is not None:
        # per OBJECT layer (konpeito ENGINE_NOTES 14): on a small patch one 8 mm tile mixes the 0 deg field, the border
        # and lettering, so it reads chaotic by construction. Each tile is judged on the stitches of the group (part /
        # family id per segment) with the most visible thread length in it.
        best = {}
        for (ty, tx, gk), v in acc.items():
            if (ty, tx) not in best or v[3] > best[(ty, tx)][3]: best[(ty, tx)] = v
        acc = best
    dev, chaos, ok_t = [], [], []
    for (ty, tx), (c, s_, n, w) in acc.items():
        if n < min_stitches: continue
        if weight is not None and float(wt[ty * T:(ty + 1) * T, tx * T:(tx + 1) * T].mean()) < min_weight:
            masked += 1; continue
        R = _m.hypot(c, s_) / max(w, 1e-9); a_dst = 0.5 * _m.atan2(s_, c)
        py, px = min(H - 1, int((ty + 0.5) * T)), min(W - 1, int((tx + 0.5) * T))
        jxx, jyy, jxy = Jxx[py, px], Jyy[py, px], Jxy[py, px]
        tr = jxx + jyy; coh = _m.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / max(tr, 1e-9)
        a_grad = 0.5 * _m.atan2(2 * jxy, jxx - jyy); a_thr = a_grad + _m.pi / 2        # threads run across the gradient
        centre = (round((tx + 0.5) * tile_mm, 1), round((ty + 0.5) * tile_mm, 1))
        if R < chaos_R:
            chaos.append(dict(at_mm=centre, R=round(R, 2), stitches=n)); continue
        if coh >= ref_coh:
            d = abs(_m.degrees(a_dst - a_thr)) % 180; d = min(d, 180 - d)
            if d > max_dev_deg:
                dev.append(dict(at_mm=centre, dev_deg=round(d, 1), ref_coh=round(coh, 2))); continue
        ok_t.append(centre)
    ok = len(ok_t); n = ok + len(dev) + len(chaos)
    return dict(tiles=n, ok=ok, ok_tiles=ok_t, fail_dev=dev, fail_chaos=chaos, pct_ok=round(100 * ok / max(n, 1), 1),
                pct_chaos=round(100 * len(chaos) / max(n, 1), 1), visible=bool(visible), tile_mm=tile_mm, masked=masked)


# ---------------------------------------------------------------- file gates (DIGITIZING_PRINCIPLES rules 4, 6, 10; ENGINE_PLAN M0)
def _sample_segments(segs, bounds, cell_mm):
    """Each segment's thread length spread over the cells it crosses: (iy, ix, length, segment index) per sample inside."""
    S = np.asarray(segs, float).reshape(-1, 4)
    if not len(S): return np.zeros(0, int), np.zeros(0, int), np.zeros(0), np.zeros(0, int)
    L = np.hypot(S[:, 2] - S[:, 0], S[:, 3] - S[:, 1]); k = np.maximum(1, np.ceil(L / (cell_mm / 4))).astype(int)
    idx = np.repeat(np.arange(len(S)), k); j = np.arange(len(idx)) - np.repeat(np.cumsum(k) - k, k)
    t = (j + 0.5) / k[idx]
    x = S[idx, 0] + t * (S[idx, 2] - S[idx, 0]); y = S[idx, 1] + t * (S[idx, 3] - S[idx, 1]); w = L[idx] / k[idx]
    x0, y0, x1, y1 = bounds; inb = (x >= x0) & (x < x1) & (y >= y0) & (y < y1)
    ix = ((x[inb] - x0) // cell_mm).astype(int); iy = ((y[inb] - y0) // cell_mm).astype(int)
    return iy, ix, w[inb], idx[inb]


def _grid_shape(bounds, cell_mm):
    import math as _m
    return int(_m.ceil((bounds[3] - bounds[1]) / cell_mm - 1e-9)), int(_m.ceil((bounds[2] - bounds[0]) / cell_mm - 1e-9))


def _flag_regions(mask, bounds, cell_mm, min_mm2, value=None):
    lab, _ = ndi.label(mask); rows = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        m = lab[sl] == k; a = float(m.sum()) * cell_mm ** 2
        if a < min_mm2: continue
        r = dict(at_mm=(round(bounds[0] + (sl[1].start + sl[1].stop) / 2 * cell_mm, 1), round(bounds[1] + (sl[0].start + sl[0].stop) / 2 * cell_mm, 1)),
                 w_mm=round((sl[1].stop - sl[1].start) * cell_mm, 1), h_mm=round((sl[0].stop - sl[0].start) * cell_mm, 1), area_mm2=round(a, 1))
        if value is not None: r["peak"] = round(float(value[sl][m].max()), 2)
        rows.append(r)
    return sorted(rows, key=lambda r: -r["area_mm2"])


def density_map(segs, bounds, cell_mm=1.0, max_mm_per_mm2=7.0, smooth_mm=3.0, covered_min=0.3, min_flag_mm2=4.0):
    """Thread length per mm^2 on a cell_mm grid (DIGITIZING_PRINCIPLES rule 10, the density heat-map), from ALL DST
    stitches: underlay and buried travel included, because that is what the needle and the fabric carry.
    Reference values: one 0.4 mm tatami layer = 2.5 mm/mm^2, + 90-degree underlay ~3.2; two layers ~5-6.4; three 7.5+.
    Flags = connected areas >= min_flag_mm2 where the smooth_mm box mean (removes row aliasing on a 1 mm grid) exceeds
    max_mm_per_mm2 (default 7.0 = more than two stacked layers + underlay: needle breaks, puckering, board-stiff duck).
    Returns dict(grid, smooth, cell_mm, bounds, covered_mm2, mean, p95, max, over_mm2, flags, ok)."""
    H, W = _grid_shape(bounds, cell_mm); iy, ix, w, _ = _sample_segments(segs, bounds, cell_mm)
    grid = np.zeros((H, W)); np.add.at(grid, (iy, ix), w); grid /= cell_mm ** 2
    k = max(1, int(round(smooth_mm / cell_mm))); sm = ndi.uniform_filter(grid, size=k, mode="constant")
    cov = grid > covered_min; over = sm > max_mm_per_mm2
    flags = _flag_regions(over, bounds, cell_mm, min_flag_mm2, value=sm)
    v = grid[cov] if cov.any() else np.zeros(1)
    return dict(grid=grid, smooth=sm, cell_mm=cell_mm, bounds=tuple(bounds), covered_mm2=round(float(cov.sum()) * cell_mm ** 2, 1),
                mean=round(float(v.mean()), 2), p95=round(float(np.percentile(v, 95)), 2), max=round(float(sm.max()) if sm.size else 0.0, 2),
                over_mm2=round(float(over.sum()) * cell_mm ** 2, 1), max_mm_per_mm2=max_mm_per_mm2, flags=flags, ok=not flags)


def trims_per_area(dst, bounds=None, origin=(0.0, 0.0), area_mm2=None, max_per_100cm2=25.0):
    """Trims per 100 cm^2, counted from the DST read-back (readback.trim_points; LESSONS B8: the DST, not the PES). With
    bounds, only trims whose needle position lies inside count. Area = area_mm2 (e.g. density_map covered_mm2), else
    the bounds, else the DST extents."""
    import readback
    pts = [(x + origin[0], y + origin[1]) for x, y in readback.trim_points(dst)]
    if bounds is not None:
        x0, y0, x1, y1 = bounds; pts = [(x, y) for x, y in pts if x0 <= x < x1 and y0 <= y < y1]
    if area_mm2 is None:
        if bounds is None:
            ex = __import__("pyembroidery").read(dst).extents(); area_mm2 = (ex[2] - ex[0]) * (ex[3] - ex[1]) / 100.0
        else: area_mm2 = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])
    per = len(pts) / max(area_mm2 / 1e4, 1e-9)
    return dict(trims=len(pts), area_cm2=round(area_mm2 / 100.0, 1), per_100cm2=round(per, 1), max_per_100cm2=max_per_100cm2,
                ok=per <= max_per_100cm2, points=pts)


def satin_runs(segs, turn_deg=120.0, max_adv_mm=0.8, min_run=6, len_ratio=2.5, tol=1e-6, hub_mm=0.25, fan_ratio=0.4):
    """Satin columns read back from stitch segments in sew order. A column is a chain of ACROSS stitches, each reversing
    the previous one (angle > turn_deg) at a similar length (ratio <= len_ratio), connected either directly
    (a0 -> b0 -> a1, the usual zigzag; the pair advances <= max_adv_mm) or through one short edge step
    (a0 -> b0 -> b1 -> a1: how dst2 writes turning / fixed / radial satin; step < 0.6 x the stitch, column midpoints
    advance <= max_adv_mm). Tatami rows (collinear
    stitches), bean / triple runs (a reversal, then collinear) and zigzag underlay (spacing ~2 mm) break the chain.
    fan=True when one side of the column stays near a hub (that side spans < fan_ratio of the other): radial satin, a
    floret or a fan where a column belonged (a satin turning a very tight curve reads as a fan too).
    Returns [dict(i0, i1, fan, width_mm, length_mm, aspect, at_mm, stitches)] (i0 / i1 = first / last segment index)."""
    import math as _m
    S = np.asarray(segs, float).reshape(-1, 4); n = len(S); out = []
    if n < 2: return out
    d = S[:, 2:] - S[:, :2]; L = np.hypot(d[:, 0], d[:, 1]); u = d / np.maximum(L, 1e-9)[:, None]
    conn = np.r_[np.hypot(S[1:, 0] - S[:-1, 2], S[1:, 1] - S[:-1, 3]) <= tol, False]      # conn[i]: seg i+1 starts where i ends
    cmax = _m.cos(_m.radians(turn_deg))
    def pair(i, j):                                              # across stitches i, j: reversed, similar length
        return (u[i] @ u[j]) < cmax and max(L[i], L[j]) / max(min(L[i], L[j]), 1e-9) <= len_ratio
    def nxt(i):
        if i + 1 < n and conn[i] and pair(i, i + 1) and _m.hypot(*(d[i] + d[i + 1])) <= max_adv_mm: return i + 1
        if i + 2 < n and conn[i] and conn[i + 1] and L[i + 1] <= 0.6 * min(L[i], L[i + 2]) and pair(i, i + 2) and \
                _m.hypot(*((S[i + 2, :2] + S[i + 2, 2:]) - (S[i, :2] + S[i, 2:])) / 2) <= max_adv_mm: return i + 2
        return None
    i = 0
    while i < n - 1:
        chain = [i]; j = nxt(i)
        while j is not None: chain.append(j); j = nxt(j)
        if len(chain) >= min_run:
            c = np.asarray(chain); A = S[c]; mid = (A[:, :2] + A[:, 2:]) / 2
            width = float(np.median(L[c])); length = float(np.hypot(*np.diff(mid, axis=0).T).sum())
            ev, od = A[0::2], A[1::2]                            # alternate directions: side A = even starts + odd ends
            sa = np.r_[ev[:, :2], od[:, 2:]]; sb = np.r_[ev[:, 2:], od[:, :2]]
            span = lambda P: float(np.hypot(*np.ptp(P, axis=0)))
            lo, hi = sorted((span(sa), span(sb)))
            fan = hi > 2 * hub_mm and (lo <= hub_mm or lo < fan_ratio * hi)
            out.append(dict(i0=int(c[0]), i1=int(c[-1]), fan=bool(fan), width_mm=round(width, 2), length_mm=round(length, 2),
                            aspect=round(length / max(width, 1e-9), 2),
                            at_mm=(round(float(mid[:, 0].mean()), 1), round(float(mid[:, 1].mean()), 1)), stitches=int(c[-1] - c[0] + 1)))
            i = chain[-1] + 1
        else:
            i += 1
    return out


def satin_shape(segs, w_min=1.0, w_max=7.0, aspect_min=2.5, blob_min_mm2=2.5, **kw):
    """Type follows shape (DIGITIZING_PRINCIPLES rule 4), read from the DST: every satin column must be 1-7 mm wide
    (narrower = run / bean, wider = split satin) and stroke-like (length / width >= aspect_min; a short, wide satin is a
    blob). Blobs under blob_min_mm2 (studs, the 1-1.5 mm dots of rule 9) are allowed. Radial fans are listed apart
    (`fans`, counts["fan"]): rule 4 allows them on face-on florets only, and a DST alone cannot tell a floret from a fan
    in a window, so whether a fan fails needs the part map (ENGINE_PLAN target "0 radials outside florets").
    segs in SEW ORDER (qa.dst_segments or a run's segs), not the visible layer.
    Returns dict(satins, fans, flags, counts, ok)."""
    runs = satin_runs(segs, **kw); flags = []; fans = [r for r in runs if r["fan"]]
    for r in runs:
        if r["fan"]: continue
        if r["width_mm"] > w_max: flags.append(dict(r, kind="too-wide"))
        elif r["width_mm"] < w_min: flags.append(dict(r, kind="too-narrow"))
        elif r["aspect"] < aspect_min and r["width_mm"] * max(r["length_mm"], 0.4) >= blob_min_mm2: flags.append(dict(r, kind="blob"))
    counts = {k: sum(1 for f in flags if f["kind"] == k) for k in ("blob", "too-wide", "too-narrow")}
    return dict(satins=len(runs) - len(fans), fans=fans, flags=flags, counts=dict(counts, fan=len(fans)), ok=not flags)


def stack_map(runs, bounds, cell_mm=1.0, layer_min=1.5, max_layers=2, min_flag_mm2=4.0):
    """How many sewn layers lie on top of each other (DIGITIZING_PRINCIPLES rule 6: never more than 2 stacked layers).
    runs: qa.dst_runs (or plain lists of segments). A run counts as a LAYER in a cell when its own thread there reaches
    layer_min mm/mm^2 (60 % of a 0.4 mm tatami layer): its own underlay, an edge run or a travel line passing through do
    not count, a fill or a satin does. Limitation: a DST alone cannot split objects joined by hidden travel into separate
    runs, so stacking inside one run is under-counted, never over-counted. Returns dict(grid, max, over_mm2, flags, ok)."""
    H, W = _grid_shape(bounds, cell_mm); segs, rid = [], []
    for k, r in enumerate(runs):
        s = r["segs"] if isinstance(r, dict) else r
        segs += list(s); rid += [k] * len(s)
    rid = np.asarray(rid, int); iy, ix, w, si = _sample_segments(segs, bounds, cell_mm)
    grid = np.zeros((H, W), int)
    if len(w):
        key = rid[si].astype(np.int64) * (H * W) + iy * W + ix
        uk, inv = np.unique(key, return_inverse=True); tot = np.bincount(inv, w) / cell_mm ** 2
        grid = np.bincount(uk[tot >= layer_min] % (H * W), minlength=H * W).reshape(H, W)
    over = grid > max_layers
    flags = _flag_regions(over, bounds, cell_mm, min_flag_mm2, value=grid.astype(float))
    return dict(grid=grid, cell_mm=cell_mm, bounds=tuple(bounds), max=int(grid.max()) if grid.size else 0,
                over_mm2=round(float(over.sum()) * cell_mm ** 2, 1), max_layers=max_layers, flags=flags, ok=not flags)


def split_satin_rows(segs, max_piece=7.0, align_tol=0.3, seam_frac=0.5, min_rows=6, turn_deg=10.0, min_piece=0.3):
    """Split-satin CORDS read from the DST (ENGINE_PLAN M2, M1 review): satin_runs only sees satins whose stitches
    reverse every time, so a split satin (each row sewn as 2+ collinear pieces) is invisible to it. Here a ROW is a
    maximal chain of consecutive segments pointing the same way (within turn_deg); the short hop to the next row ends it.
    segs: ONE cord's segments in sew order (e.g. the DST segments attributed to a part by compile.labelled_dst).
    Measures, per cord: rows, row length (median / max), pieces per row, the longest piece, the column width across the
    rows, and how many interior split points line up (within align_tol mm, along the row axis) with a split of the next
    row: aligned splits are a visible seam (dst2.turning_satin ~1.0; a staggered split satin < 0.1).
    Flags: too-long (a piece > max_piece mm: the machine limit, rule 4), seam (aligned fraction > seam_frac over
    >= min_rows rows), too-narrow (column under 1 mm across: a run, not a cord).
    Returns dict(rows, row_len_med, row_len_max, pieces_med, max_piece, column_w, aligned, flags, ok)."""
    import math as _m
    S = [s for s in segs if _m.hypot(s[2] - s[0], s[3] - s[1]) >= min_piece]
    if not S: return dict(rows=0, row_len_med=0.0, row_len_max=0.0, pieces_med=0, max_piece=0.0, column_w=0.0, aligned=0.0, flags=[], ok=True)
    rows = []; cur = [S[0]]
    def ang(s): return _m.atan2(s[3] - s[1], s[2] - s[0])
    for s in S[1:]:
        p = cur[-1]; d = abs((ang(s) - ang(p) + _m.pi) % (2 * _m.pi) - _m.pi)
        if d <= _m.radians(turn_deg) and abs(s[0] - p[2]) < 0.05 and abs(s[1] - p[3]) < 0.05: cur.append(s)
        else: rows.append(cur); cur = [s]
    rows.append(cur)
    L = np.array([sum(_m.hypot(s[2] - s[0], s[3] - s[1]) for s in r) for r in rows])
    keep = [r for r, l in zip(rows, L) if l >= 1.0]                       # the hops between rows are not rows
    if not keep: return dict(rows=0, row_len_med=0.0, row_len_max=0.0, pieces_med=0, max_piece=0.0, column_w=0.0, aligned=0.0, flags=[], ok=True)
    C = sum(_m.cos(2 * ang(s)) * _m.hypot(s[2] - s[0], s[3] - s[1]) for r in keep for s in r)
    Sn = sum(_m.sin(2 * ang(s)) * _m.hypot(s[2] - s[0], s[3] - s[1]) for r in keep for s in r)
    a = 0.5 * _m.atan2(Sn, C); u = (_m.cos(a), _m.sin(a)); v = (-u[1], u[0])
    splits = [sorted(s[2] * u[0] + s[3] * u[1] for s in r[:-1]) for r in keep]   # interior split points on the row axis
    hit = tot = 0
    for s0, s1 in zip(splits, splits[1:]):
        for t in s0:
            tot += 1; hit += any(abs(t - t2) < align_tol for t2 in s1)
    aligned = hit / tot if tot else 0.0
    mids = [((r[0][0] + r[-1][2]) / 2) * v[0] + ((r[0][1] + r[-1][3]) / 2) * v[1] for r in keep]
    col_w = (max(mids) - min(mids)) if len(mids) > 1 else 0.0
    pieces = [len(r) for r in keep]; mp = max(_m.hypot(s[2] - s[0], s[3] - s[1]) for r in keep for s in r)
    Lk = np.array([sum(_m.hypot(s[2] - s[0], s[3] - s[1]) for s in r) for r in keep])
    flags = []
    if mp > max_piece: flags.append(dict(kind="too-long", max_piece=round(mp, 2)))
    if len(keep) >= min_rows and aligned > seam_frac: flags.append(dict(kind="seam", aligned=round(aligned, 2)))
    if len(keep) >= min_rows and col_w < 1.0: flags.append(dict(kind="too-narrow", column_w=round(col_w, 2)))
    return dict(rows=len(keep), row_len_med=round(float(np.median(Lk)), 2), row_len_max=round(float(Lk.max()), 2),
                pieces_med=int(np.median(pieces)), max_piece=round(mp, 2), column_w=round(col_w, 2), aligned=round(aligned, 3),
                flags=flags, ok=not flags)
