"""motif_match per labelled motif, against the reference the LABELS name (ENGINE_PLAN G3, LESSONS A14).

  rows = refgrade.grade(labels, labels_dir, ev, out)

A grading UNIT is a motif, or one part that names its own `reference` (that part leaves its motif's unit). Its
reference silhouette is, by default, the MOCKUP: the gate reference's evidence pixels inside the unit's windows (minus
`except` windows) whose tone is one of the unit's tones and not bare. With `reference: {image, box}` it is that
picture instead: opaque pixels of an RGBA image (else: pixels away from the corner colour), stretched into `box`
(garment mm). Either way the reference comes from input pixels only (A14), never from the engine's own parts.
The silhouette is closed 1 mm, holes filled, and its largest piece is graded with qa.motif_match (near_mm 1.5)
against `out`: the written DST's stitches on the same grid. A reference changes extraction only when it names `governs` (G4, digitize.labels.refsource).

  ev       evidence on the GATE reference (bench.json's registration: the mockup), grid = ev.to_px
  out      bool mask of the sewn stitches on ev's grid
  bare     tones that are the bare shell (never part of a reference)
Rows: unit, motif, reference ("mockup" | the image path as written), governs, area_mm2, iou, w_ratio, h_ratio, ok.
G4: a reference that governs "colour" is also graded on the sewn COLOURS (colour_grade: colour_match,
colour_ok, groups; shape_ok keeps the silhouette result and ok = both), so a fish sewn in the wrong colours fails its reference."""
import os
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Polygon
from shapely.ops import unary_union
from digitize.labels import schema as LS

NEAR_MM = 1.5
CLOSE_MM = 1.0
CORNER_DIST = 40.0
COLOUR_DE = 12.0      # G4: palette tones within this CIEDE2000 are one colour group (Koi: blues + whites one group; cyan 14 from sky, red, black apart)
EDGE_MM = 0.5         # G4: the picture's colours are read this far in from its edge (edge pixels blend with the background)
COLOUR_MIN = 0.70     # G4: share of the picture's motif pixels whose tone shows within NEAR_MM
CLASS_SHARE = 0.03    # G4: a colour group holding >= 3 % of the picture is a colour the sewing must show ...
CLASS_RECALL = 0.50   # ... on at least half of its pixels


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


def place(ref, base_dir, to_px, shape):
    """the picture stretched into ref["box"] (garment mm) on a (H, W) grid whose to_px maps garment mm -> px:
    (bool motif mask, (H, W, 3) float RGB of the picture, 0 outside the box). Opaque pixels of an RGBA image are the
    motif (alpha > 127); else pixels away from the corner colour (> CORNER_DIST)."""
    from PIL import Image
    path = os.path.join(base_dir, ref["image"])
    if not os.path.exists(path): raise FileNotFoundError(f"labels reference image {ref['image']} not found (looked in {base_dir})")
    im = Image.open(path); H, W = shape
    x0, y0, x1, y1 = ref["box"]
    (px0, px1), (py0, py1) = to_px([x0, x1], [y0, y1])
    c0, c1, r0, r1 = int(round(px0)), int(round(px1)), int(round(py0)), int(round(py1))
    w, h = max(1, c1 - c0), max(1, r1 - r0)
    rgba = np.asarray(im.convert("RGBA").resize((w, h), Image.NEAREST)).astype(float)
    if im.mode in ("RGBA", "LA") or "transparency" in im.info: m = rgba[..., 3] > 127
    else: m = np.sqrt(((rgba[..., :3] - rgba[0, 0, :3]) ** 2).sum(-1)) > CORNER_DIST
    out, rgb = np.zeros((H, W), bool), np.zeros((H, W, 3))
    R0, R1, C0, C1 = max(0, r0), min(H, r0 + h), max(0, c0), min(W, c0 + w)
    if R1 > R0 and C1 > C0:
        out[R0:R1, C0:C1] = m[R0 - r0:R1 - r0, C0 - c0:C1 - c0]
        rgb[R0:R1, C0:C1] = rgba[R0 - r0:R1 - r0, C0 - c0:C1 - c0, :3]
    return out, rgb


def image_mask(ev, ref, base_dir):
    """the picture's motif pixels, stretched into ref["box"] (garment mm), on ev's grid"""
    return place(ref, base_dir, ev.to_px, (ev.H, ev.W))[0]


def _silhouette(ev, m):
    if not m.any(): return m
    r = max(1, int(round(CLOSE_MM * ev.ppm))); yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    m = ndi.binary_fill_holes(ndi.binary_closing(m, xx * xx + yy * yy <= r * r) | m)
    lab, n = ndi.label(m)
    if n <= 1: return m
    return lab == (1 + int(np.argmax(np.bincount(lab.ravel())[1:])))


def top_colour(ev, stop_masks, stop_hex):
    """(H, W) int: index into stop_hex of the LAST stop sewn at each pixel (what shows), -1 where nothing is sewn"""
    top = np.full((ev.H, ev.W), -1, int)
    for ci in sorted(stop_masks):
        if ci >= len(stop_hex): raise ValueError(f"stop {ci} has no thread colour ({len(stop_hex)} given)")
        top[stop_masks[ci]] = ci
    return top


def tone_groups(palette, bare=()):
    """{tone: group id}: palette tones joined when within COLOUR_DE of each other (transitively), bare tones left out.
    A group is a colour a viewer tells apart from the others; shades inside one group are the same colour on a picture."""
    from digitize.extract.evidence import to_lab, hex_rgb, delta_e
    keys = [k for k in palette if k not in bare]
    lab = to_lab(np.array([[hex_rgb(palette[k]) for k in keys]], float))[0]
    g = list(range(len(keys)))
    def root(i):
        while g[i] != i: i = g[i]
        return i
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if delta_e(lab[i], lab[j]) <= COLOUR_DE: g[root(j)] = root(i)
    return {k: root(i) for i, k in enumerate(keys)}


def colour_grade(ev, ref, base_dir, sil, top, stop_hex, palette, bare=()):
    """G4: does the sewing show the picture's colours? Picture pixels (its motif pixels, EDGE_MM in from its edge, where
    the picture blends with its background) and threads are each read as their nearest palette tone, then as that tone's
    GROUP (tone_groups). A pixel matches when a thread of its group is the top colour within NEAR_MM.
    -> dict(colour_match, groups {"tone+tone": dict(share, recall)}, colour_ok): colour_match >= COLOUR_MIN and every
    group holding >= CLASS_SHARE of the picture recalled >= CLASS_RECALL (a missing accent stripe fails even when the
    body colour carries the average)."""
    from digitize.extract.evidence import to_lab, hex_rgb, delta_e
    m, pic = place(ref, base_dir, ev.to_px, (ev.H, ev.W))
    e = int(round(EDGE_MM * ev.ppm))
    m = (ndi.binary_erosion(m, iterations=e) if e else m) & sil
    grp = tone_groups(palette, bare); keys = list(grp)
    lab_p = to_lab(np.array([[hex_rgb(palette[k]) for k in keys]], float))[0]
    def nearest(lab): return np.stack([delta_e(lab, np.broadcast_to(lab_p[i], lab.shape)) for i in range(len(keys))], -1).argmin(-1)
    if not m.any(): return dict(colour_match=0.0, groups={}, colour_ok=False)
    cls = np.array([grp[keys[i]] for i in nearest(to_lab(pic[m][None, :, :])[0])])
    sg = [grp[keys[i]] for i in nearest(to_lab(np.array([[hex_rgb(h) for h in stop_hex]], float))[0])] if len(stop_hex) else []
    r = max(1, int(round(NEAR_MM * ev.ppm))); yy, xx = np.ogrid[-r:r + 1, -r:r + 1]; disk = xx * xx + yy * yy <= r * r
    hit = np.zeros(int(m.sum()), bool); groups = {}
    for c in np.unique(cls):
        ok_stops = [i for i, gi in enumerate(sg) if gi == c]
        near = ndi.binary_dilation(np.isin(top, ok_stops), disk) if ok_stops else np.zeros_like(m)
        sel = cls == c; got = near[m][sel]; hit[sel] = got
        groups["+".join(k for k in keys if grp[k] == c)] = dict(share=round(float(sel.mean()), 3), recall=round(float(got.mean()), 3))
    cm = float(hit.mean())
    ok = cm >= COLOUR_MIN and all(v["recall"] >= CLASS_RECALL for v in groups.values() if v["share"] >= CLASS_SHARE)
    return dict(colour_match=round(cm, 3), groups=groups, colour_ok=bool(ok))


def grade(labels, labels_dir, ev, out, bare=(), stops=None, palette=None):
    """stops = (stop_masks {stop: mask on ev's grid}, [thread hex per stop]) + palette: units whose reference governs
    "colour" are also graded on colour (colour_grade); their ok = shape ok AND colour ok"""
    import qa
    rows = []
    top = top_colour(ev, *stops) if stops is not None else None
    for uid, mid, parts, ref in units(labels):
        m = image_mask(ev, ref, labels_dir) if ref else mockup_mask(ev, parts, bare)
        sil = _silhouette(ev, m)
        r = qa.motif_match(sil, out, ev.ppm, min_mm2=0.0, near_mm=NEAR_MM) if sil.any() else []
        best = max(r, key=lambda q: q["area_mm2"]) if r else dict(area_mm2=0.0, iou=0.0, w_ratio=0.0, h_ratio=0.0, ok=False)
        row = dict(unit=uid, motif=mid, reference=ref["image"] if ref else "mockup", governs=LS.governs(ref),
                   **{k: best[k] for k in ("area_mm2", "iou", "w_ratio", "h_ratio", "ok")})
        if ref and "colour" in LS.governs(ref):
            if top is None or palette is None: raise ValueError(f"{uid}: its reference governs colour, so grade() needs stops + palette")
            row.update(shape_ok=row["ok"], **colour_grade(ev, ref, labels_dir, sil, top, stops[1], palette, bare))
            row["ok"] = bool(row["shape_ok"] and row["colour_ok"])
        rows.append(row)
    return rows


def summary(rows):
    by = {}
    for r in rows:
        b = by.setdefault(r["reference"] if r["reference"] == "mockup" else "image", dict(n=0, ok=0, iou=[]))
        b["n"] += 1; b["ok"] += int(r["ok"]); b["iou"].append(r["iou"])
    return {k: dict(n=v["n"], ok=v["ok"], mean_iou=round(float(np.mean(v["iou"])), 2)) for k, v in by.items()}
