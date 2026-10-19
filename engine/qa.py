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
    generated stand-in of the right size but the wrong silhouette fails here, a flattened one fails on height)."""
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
