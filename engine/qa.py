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
def motif_match(ref, out, ppm, min_mm2=4.0, iou_min=0.70, ratio_min=0.80, pad_mm=3.0):
    """Every motif in the reference vs what was stitched, one row per motif (LESSONS A14).
    ref, out: bool masks on the SAME garment-mm grid (ppm px per mm). ref = the motif family traced from the mockup /
    close-up (e.g. the cream islet pixels); out = the same family rendered from the shipped DST. A motif passes when the
    stitched shape overlapping it has IoU >= iou_min and keeps >= ratio_min of the reference width AND height (a
    generated stand-in of the right size but the wrong silhouette fails here, a flattened one fails on height).
    ref MUST be derived from input pixels only (mockup / close-up / reference image) - never from the art, scene
    data or a template, or the gate only proves DST == art (circular; Koi Rev B review)."""
    lab, n = ndi.label(ref); rows = []; pad = int(round(pad_mm * ppm))
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        y0, y1 = max(0, sl[0].start - pad), min(ref.shape[0], sl[0].stop + pad)
        x0, x1 = max(0, sl[1].start - pad), min(ref.shape[1], sl[1].stop + pad)
        r = lab[y0:y1, x0:x1] == k; area = r.sum() / ppm**2
        if area < min_mm2: continue
        ol, _ = ndi.label(out[y0:y1, x0:x1]); keep = np.unique(ol[r & (ol > 0)])
        o = np.isin(ol, keep) & (ol > 0)
        iou = (r & o).sum() / max((r | o).sum(), 1)
        def ext(m, ax):
            idx = np.nonzero(m.any(axis=ax))[0]; return (idx[-1] - idx[0] + 1) / ppm if len(idx) else 0.0
        wr, hr = ext(o, 0) / max(ext(r, 0), 1e-9), ext(o, 1) / max(ext(r, 1), 1e-9)
        ok = iou >= iou_min and min(wr, 1/max(wr, 1e-9)) >= ratio_min and min(hr, 1/max(hr, 1e-9)) >= ratio_min
        rows.append(dict(motif=k, x_mm=round((x0 + x1) / 2 / ppm, 1), y_mm=round((y0 + y1) / 2 / ppm, 1),
                         area_mm2=round(float(area), 1), iou=round(float(iou), 2), w_ratio=round(float(wr), 2), h_ratio=round(float(hr), 2), ok=bool(ok)))
    return rows


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



def angle_coherence(regions, groups=("WALL", "ROOF", "TMB", "STONE"), max_spread_deg=10.0, satin_min_aspect=2.5):
    """Stitch-direction discipline for constructed motifs (LESSONS A16), read from the art regions (a digitising
    decision, not a fidelity trace). regions: dicts with geom, stype ('satin'/'tatami'/...), angle (deg or 'auto'),
    grp, unit. Per (unit, grp) of a constructed group: the area-weighted spread of fill angles must stay within
    max_spread_deg (one wall = one direction), and satin is only allowed on stroke-like shapes (aspect >= satin_min_aspect;
    satin on a blob = a fan). Returns rows of failures (empty = pass)."""
    import math as _m
    from collections import defaultdict
    by = defaultdict(list); bad = []
    for r in regions:
        if r.get("grp") not in groups or r["geom"].is_empty: continue
        g = r["geom"]; A = g.area
        mr = g.minimum_rotated_rectangle; c = list(mr.exterior.coords)
        e = sorted(_m.hypot(c[i+1][0]-c[i][0], c[i+1][1]-c[i][1]) for i in range(4))
        aspect = e[-1] / max(e[0], 1e-6)
        if r.get("stype") == "satin" and aspect < satin_min_aspect and A > 2.0:
            bad.append(dict(kind="satin-on-blob", unit=r.get("unit"), grp=r["grp"], area_mm2=round(A, 1), aspect=round(aspect, 2)))
        ang = r.get("angle")
        if r.get("stype") != "satin" and isinstance(ang, (int, float)):
            by[(r.get("unit"), r["grp"])].append((float(ang) % 180, A))
    for (unit, grp), v in by.items():
        if len(v) < 2: continue
        # spread on the doubled circle (axial angles)
        C = sum(a*_m.cos(_m.radians(2*t)) for t, a in v); S = sum(a*_m.sin(_m.radians(2*t)) for t, a in v); W = sum(a for _, a in v)
        R = _m.hypot(C, S) / max(W, 1e-9)
        spread = _m.degrees(_m.sqrt(max(0.0, -2*_m.log(max(R, 1e-9))))) / 2
        if spread > max_spread_deg:
            bad.append(dict(kind="angle-spread", unit=unit, grp=grp, n=len(v), spread_deg=round(spread, 1)))
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


def direction_match(ref, ppm, segs, tile_mm=8.0, min_len=0.6, ref_coh=0.25, max_dev_deg=25.0, chaos_R=0.55, min_stitches=12):
    """Stitch DIRECTION vs the reference, everywhere (LESSONS A16): every motif, not only buildings.
    ref: grey image (2-D array) of the mockup / close-up mapped to garment mm (ppm px per mm), INPUT PIXELS ONLY.
    segs: DST stitch segments in the same mm frame (qa.dst_segments). Per tile:
      - DST direction = axial mean of stitch angles (length-weighted), with coherence R (1 = all parallel, 0 = random)
      - reference direction = thread direction from the structure tensor of the image (the visible thread grain)
    A tile FAILS when (a) the reference shows a clear thread direction and the DST deviates > max_dev_deg, or
    (b) the DST stitches in the tile point every which way (R < chaos_R): fans, blob satins, random fills.
    Returns dict(tiles=n, fail_dev=[...], fail_chaos=[...], pct_ok=...) with tile centres in mm."""
    import math as _m
    from scipy import ndimage as _ndi
    g = np.asarray(ref, float)
    if g.ndim == 3: g = g[..., :3] @ np.array([0.299, 0.587, 0.114])
    gy, gx = np.gradient(_ndi.gaussian_filter(g, 0.6))
    sig = tile_mm * ppm / 3.0
    Jxx = _ndi.gaussian_filter(gx * gx, sig); Jyy = _ndi.gaussian_filter(gy * gy, sig); Jxy = _ndi.gaussian_filter(gx * gy, sig)
    T = int(round(tile_mm * ppm)); H, W = g.shape; acc = {}
    for x0, y0, x1, y1 in segs:
        L = _m.hypot(x1 - x0, y1 - y0)
        if L < min_len: continue
        cx, cy = (x0 + x1) / 2 * ppm, (y0 + y1) / 2 * ppm
        if not (0 <= cx < W and 0 <= cy < H): continue
        a = _m.atan2(y1 - y0, x1 - x0); key = (int(cy // T), int(cx // T))
        c, s_, n, w = acc.get(key, (0.0, 0.0, 0, 0.0))
        acc[key] = (c + L * _m.cos(2 * a), s_ + L * _m.sin(2 * a), n + 1, w + L)
    dev, chaos, ok = [], [], 0
    for (ty, tx), (c, s_, n, w) in acc.items():
        if n < min_stitches: continue
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
        ok += 1
    n = ok + len(dev) + len(chaos)
    return dict(tiles=n, ok=ok, fail_dev=dev, fail_chaos=chaos, pct_ok=round(100 * ok / max(n, 1), 1))
