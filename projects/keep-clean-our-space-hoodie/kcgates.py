"""KCOS Rev C gates as pure functions (no project side effects), so tests/test_kcos_gates.py can prove them red-then-green
on synthetic files. Every gate reads the WRITTEN file.

  foam_gates(dst_path, per_stop, puff_geom, origin, keep=1.0, tol=0.25)   LESSONS B31/B34 + house rule 6 on the DST
  straight_chains(dst_path, per_stop, min_len=15, tol_deg=10)            straight lines inside sheer stipple stops
  glyph_check(ref_geom, stitched_mask, bb, ppm)                          stitched character vs the font's own glyph
"""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Point
from shapely.prepared import prep

SHEER = {"GLOW", "HAZE", "REG crosses"}


def foam_gates(dst_path, per_stop, puff_geom, origin, keep=1.0, tol=0.25):
    """per_stop: [{stop, puff, top, codes}] in file order (the build's stop list, readback-checked).
    foam_stop      every puff stop holds only puff codes; no flat stop after the first puff stop except 'top' details sewn
                   after the foam is torn; the first puff stop is not stop 1 (there is a colour change = machine stop to
                   lay the foam before it)
    base_under_puff  needle points of the flat stops sewn BEFORE the foam inside the puff footprint shrunk by keep + tol
                   (house rule 6: flat work under puff keeps only a keep-mm band under the edge). Target 0."""
    import pyembroidery as pe
    first = next((p["stop"] for p in per_stop if p.get("puff")), None)
    if first is None: return dict(puff=False)
    mixed = [p["stop"] for p in per_stop if p.get("puff") and not all(c.startswith("PF-") for c in p.get("codes", []) if c != "REG crosses")]
    late = [p["stop"] for p in per_stop if p["stop"] > first and not p.get("puff") and not p.get("top")]
    core = prep(puff_geom.buffer(-(keep + tol)))
    si = 1; hits = {}
    for x, y, c in pe.read(dst_path).stitches:
        k = c & pe.COMMAND_MASK
        if k == pe.COLOR_CHANGE: si += 1; continue
        if k == pe.END: break
        if k != pe.STITCH or si >= first: continue
        if core.contains(Point(x / 10.0 + origin[0], y / 10.0 + origin[1])): hits[si] = hits.get(si, 0) + 1
    col = {p["stop"]: p.get("col", "") for p in per_stop}
    return dict(puff=True, pause_before_stop=first, mixed_stops=mixed, flat_after_puff=late,
                foam_stop_ok=not mixed and not late and first > 1,
                base_under_puff={f"stop {k} {col.get(k, '')}": v for k, v in hits.items()}, base_under_puff_ok=not hits,
                keep_mm=keep, tol_mm=tol)


def straight_chains(dst_path, per_stop, min_len=15.0, tol_deg=10.0):
    """straight lines inside sheer stipple stops (codes all in SHEER): chains of >= 4 near-collinear stitches, each
    0.5-2 mm (a stipple bridge; router travel is longer and is measured by dst2.exposed_travel), >= min_len mm.
    Rev B FR M had 13, up to 57.5 mm (ENGINE_NOTES 22). Returns [(stop, length mm)]."""
    import pyembroidery as pe
    sheer = {ps["stop"] for ps in per_stop if ps.get("codes") and set(ps["codes"]) <= SHEER}
    out = []; stop = 1; ch = []
    def flush():
        if len(ch) >= 4 and stop in sheer:
            d = math.dist(ch[0], ch[-1])
            if d >= min_len: out.append((stop, round(d, 1)))
    for x, y, c in pe.read(dst_path).stitches:
        k = c & pe.COMMAND_MASK; P = (x / 10, y / 10)
        if k != pe.STITCH:
            flush(); ch = []
            if k == pe.COLOR_CHANGE: stop += 1
            continue
        if len(ch) >= 2:
            a = math.atan2(ch[-1][1] - ch[-2][1], ch[-1][0] - ch[-2][0]); b = math.atan2(P[1] - ch[-1][1], P[0] - ch[-1][0])
            if abs((b - a + math.pi) % (2 * math.pi) - math.pi) > math.radians(tol_deg) or not 0.5 <= math.dist(P, ch[-1]) <= 2.0:
                flush(); ch = [ch[-1]]
        ch.append(P)
    flush(); return out


def raster(geom, bb, ppm):
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = bb; W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)          # same grid as dstview.mask_as_sewn
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    T = lambda cs: [((x - x0) * ppm, (y - y0) * ppm) for x, y in cs]
    for p in (geom.geoms if hasattr(geom, "geoms") else [geom]):
        if p.geom_type != "Polygon" or p.is_empty: continue
        d.polygon(T(p.exterior.coords), fill=255)
        for q in p.interiors: d.polygon(T(q.coords), fill=0)
    return np.array(im) > 127


def holes(mask, ppm, min_mm2):
    lab, n = ndi.label(~mask); edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    return [lab == k for k in range(1, n + 1) if k not in edge and (lab == k).sum() / ppm**2 >= min_mm2]


GLYPH_IOU, GLYPH_MISS = 0.80, 3.0

def glyph_check(ref_geom, stitched, bb, ppm=8.0, near_mm=1.0, close_mm=0.3, tol_mm=0.25):
    """font glyph (ref_geom, garment mm) vs a stitched mask on the same grid. Returns dict(iou, miss_mm2, counters, ok):
    iou       area IoU (stitched counted within near_mm of the glyph, closed close_mm so satin rows read as a surface)
    miss_mm2  largest connected piece of the glyph with no stitch within tol_mm (a dropped stroke)
    counters  (font, matched): every font counter >= 0.6 mm2 needs its OWN stitched counter (田 stitched as 日: 2 for 4)
    ok        iou >= 0.80 and miss_mm2 <= 3.0 and every counter matched. IoU alone passed 界 without its centre vertical (0.81)."""
    ref = raster(ref_geom, bb, ppm)
    near = raster(ref_geom.buffer(near_mm), bb, ppm)
    st = ndi.binary_closing(stitched, iterations=max(1, int(round(close_mm * ppm)))) & near
    u = (ref | st).sum()
    iou = float((ref & st).sum() / u) if u else 0.0
    miss = ref & ~ndi.binary_dilation(st, iterations=max(1, int(round(tol_mm * ppm))))
    lab, n = ndi.label(miss)
    miss_mm2 = float(max(ndi.sum(miss, lab, range(1, n + 1)))) / ppm**2 if n else 0.0
    fh = holes(ref, ppm, 0.6); sh = holes(st, ppm, 0.2); used = set(); matched = 0
    for h in fh:
        best = max(((int((h & s).sum()), j) for j, s in enumerate(sh) if j not in used), default=(0, None))
        if best[1] is not None and best[0] >= 0.3 * h.sum():
            if sum(int((s_ & sh[best[1]]).sum()) >= 0.3 * s_.sum() for s_ in fh) == 1: used.add(best[1]); matched += 1
    ok = iou >= GLYPH_IOU and miss_mm2 <= GLYPH_MISS and matched == len(fh)
    return dict(iou=round(iou, 3), miss_mm2=round(miss_mm2, 2), counters=(len(fh), matched), ok=bool(ok))
