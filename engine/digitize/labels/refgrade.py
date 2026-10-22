"""motif_match per labelled motif, against the reference the LABELS name (ENGINE_PLAN G3, LESSONS A14).

  rows = refgrade.grade(labels, labels_dir, ev, out)

A grading UNIT is a motif, or one part that names its own `reference` (that part leaves its motif's unit). Its
reference silhouette is, by default, the MOCKUP: the gate reference's evidence pixels inside the unit's windows (minus
`except` windows) whose tone is one of the unit's tones and not bare. With `reference: {image, box}` it is that
picture instead: opaque pixels of an RGBA image (else: pixels away from the corner colour), stretched into `box`
(garment mm). Either way the reference comes from input pixels only (A14), never from the engine's own parts.
The silhouette is closed 1 mm, holes filled, and its largest piece is graded with qa.motif_match (near_mm 1.5)
against `out`: the written DST's stitches on the same grid. Grading only: a reference never changes extraction.

  ev       evidence on the GATE reference (bench.json's registration: the mockup), grid = ev.to_px
  out      bool mask of the sewn stitches on ev's grid
  bare     tones that are the bare shell (never part of a reference)
Rows: unit, motif, reference ("mockup" | the image path as written), area_mm2, iou, w_ratio, h_ratio, ok."""
import os
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Polygon
from shapely.ops import unary_union
from digitize.labels import schema as LS

NEAR_MM = 1.5
CLOSE_MM = 1.0
CORNER_DIST = 40.0


def units(labels):
    """[(unit id, motif id, [(part, windows)], reference | None)]: a part with its own reference is its own unit"""
    win = {LS.part_id(m, p): [Polygon(w).buffer(0) for w in (p.get("hint") or {}).get("polygons", [])] for m, p in LS.iter_parts(labels)}
    def windows(m, p):
        gs = list(win[LS.part_id(m, p)])
        for o in (p.get("hint") or {}).get("except", []) or []:
            cut = unary_union(win[o]); gs = [g.difference(cut) for g in gs]
        return [g for g in gs if not g.is_empty]
    out = []
    for m in labels.get("motifs", []):
        own = [(p, windows(m, p)) for p in m.get("parts", []) if not p.get("rest") and "reference" not in p]
        if own: out.append((m["id"], m["id"], own, m.get("reference")))
        for p in m.get("parts", []):
            if "reference" in p and not p.get("rest"): out.append((LS.part_id(m, p), m["id"], [(p, windows(m, p))], p["reference"]))
    return out


def mockup_mask(ev, parts, bare=()):
    """the unit's pixels in the gate reference: inside its windows AND one of its tones (bare tones never count)"""
    keep = np.zeros((ev.H, ev.W), bool)
    for p, gs in parts:
        if not gs: continue
        t = p.get("tones", "all"); keys = ev.keys if t == "all" else [k for k in t if k in ev.keys]
        idx = [ev.keys.index(k) for k in keys if k not in bare]
        keep |= ev.mask(unary_union(gs)) & np.isin(ev.tone, idx)
    return keep


def image_mask(ev, ref, base_dir):
    """the picture's motif pixels, stretched into ref["box"] (garment mm), on ev's grid"""
    from PIL import Image
    path = os.path.join(base_dir, ref["image"])
    if not os.path.exists(path): raise FileNotFoundError(f"labels reference image {ref['image']} not found (looked in {base_dir})")
    im = Image.open(path)
    x0, y0, x1, y1 = ref["box"]
    (px0, px1), (py0, py1) = ev.to_px([x0, x1], [y0, y1])
    c0, c1, r0, r1 = int(round(px0)), int(round(px1)), int(round(py0)), int(round(py1))
    w, h = max(1, c1 - c0), max(1, r1 - r0)
    if im.mode in ("RGBA", "LA") or "transparency" in im.info:
        m = np.asarray(im.convert("RGBA").resize((w, h), Image.NEAREST))[..., 3] > 127
    else:
        a = np.asarray(im.convert("RGB").resize((w, h), Image.NEAREST)).astype(float)
        m = np.sqrt(((a - a[0, 0]) ** 2).sum(-1)) > CORNER_DIST
    out = np.zeros((ev.H, ev.W), bool)
    R0, R1, C0, C1 = max(0, r0), min(ev.H, r0 + h), max(0, c0), min(ev.W, c0 + w)
    if R1 > R0 and C1 > C0: out[R0:R1, C0:C1] = m[R0 - r0:R1 - r0, C0 - c0:C1 - c0]
    return out


def _silhouette(ev, m):
    if not m.any(): return m
    r = max(1, int(round(CLOSE_MM * ev.ppm))); yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    m = ndi.binary_fill_holes(ndi.binary_closing(m, xx * xx + yy * yy <= r * r) | m)
    lab, n = ndi.label(m)
    if n <= 1: return m
    return lab == (1 + int(np.argmax(np.bincount(lab.ravel())[1:])))


def grade(labels, labels_dir, ev, out, bare=()):
    import qa
    rows = []
    for uid, mid, parts, ref in units(labels):
        m = image_mask(ev, ref, labels_dir) if ref else mockup_mask(ev, parts, bare)
        sil = _silhouette(ev, m)
        r = qa.motif_match(sil, out, ev.ppm, min_mm2=0.0, near_mm=NEAR_MM) if sil.any() else []
        best = max(r, key=lambda q: q["area_mm2"]) if r else dict(area_mm2=0.0, iou=0.0, w_ratio=0.0, h_ratio=0.0, ok=False)
        rows.append(dict(unit=uid, motif=mid, reference=ref["image"] if ref else "mockup",
                         **{k: best[k] for k in ("area_mm2", "iou", "w_ratio", "h_ratio", "ok")}))
    return rows


def summary(rows):
    by = {}
    for r in rows:
        b = by.setdefault(r["reference"] if r["reference"] == "mockup" else "image", dict(n=0, ok=0, iou=[]))
        b["n"] += 1; b["ok"] += int(r["ok"]); b["iou"].append(r["iou"])
    return {k: dict(n=v["n"], ok=v["ok"], mean_iou=round(float(np.mean(v["iou"])), 2)) for k, v in by.items()}
