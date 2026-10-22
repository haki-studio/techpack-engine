"""A labels reference that GOVERNS the sewing (ENGINE_PLAN G4, LESSONS A39): composite it into the extraction source.

  ref, report = refsource.composite(ref, labels, labels_dir, palette, bare)

ref = register.reference(...) (rgb, grey, closeup_weight on its own grid, bounds, ppm). For every grading unit
(refgrade.units: a motif, or a part with its own reference) whose reference names `governs`:
  "colour"      inside the picture's motif pixels, the picture's RGB replaces the source's (so the evidence tones, and
                with them every claim, colour and thread of the unit, come from the picture);
  "silhouette"  inside the unit's windows but outside the picture's motif pixels, the source reads as the bare shell
                (the first `bare` palette tone), so no part of the unit claims what the picture does not show.
Position, heading, size and count stay the labeller's: the picture sits in its `box`, which the labeller placed on the
mockup motif (A30). Close-up weight is 0 where a picture governs (the picture, not a close-up, informs there). Input
pixels only (A14): the picture is an input; nothing is drawn. A unit with governs [] is untouched (grading only).
The GATE reference is never composited: refgrade grades each unit against its picture, other gates against the mockup."""
import numpy as np
from shapely.ops import unary_union
from digitize.labels import schema as LS, refgrade as RG


def governing(labels):
    """[(unit id, [(part, windows)], reference)] of the units whose reference governs anything"""
    return [(uid, parts, ref) for uid, _, parts, ref in RG.units(labels) if ref and LS.governs(ref)]


def _hint_mask(ref, parts, to_px):
    from PIL import Image, ImageDraw
    H, W = ref["rgb"].shape[:2]; im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    g = unary_union([w for _, ws in parts for w in ws])
    for p in ([g] if g.geom_type == "Polygon" else [q for q in getattr(g, "geoms", []) if q.geom_type == "Polygon"]):
        T = lambda cs: [tuple(v) for v in np.stack(to_px(*np.asarray(cs).T), -1)]
        d.polygon(T(p.exterior.coords), fill=255)
        for r in p.interiors: d.polygon(T(r.coords), fill=0)
    return np.asarray(im) > 127


def composite(ref, labels, labels_dir, palette, bare=()):
    """-> (new ref dict, report rows). ref is not modified."""
    from digitize.extract.evidence import hex_rgb
    G = governing(labels)
    if not G: return ref, []
    x0, y0 = ref["bounds"][:2]; ppm = float(ref["ppm"])
    to_px = lambda x, y: ((np.asarray(x) - x0) * ppm, (np.asarray(y) - y0) * ppm)
    rgb = np.array(ref["rgb"], float, copy=True); cw = ref.get("closeup_weight")
    cw = None if cw is None else np.array(cw, float, copy=True)
    shape = rgb.shape[:2]; rows = []
    for uid, parts, r in G:
        gv = LS.governs(r)
        m, pic = RG.place(r, labels_dir, to_px, shape)
        win = _hint_mask(ref, parts, to_px)
        n_col = n_sil = 0
        if "silhouette" in gv:
            if not bare: raise ValueError(f"labels reference of {uid} governs the silhouette, but the run declares no bare tone (threads.bare)")
            off = win & ~m; rgb[off] = hex_rgb(palette[bare[0]]); n_sil = int(off.sum())
        if "colour" in gv:
            rgb[m] = pic[m]; n_col = int(m.sum())
        if cw is not None: cw[m | (win if "silhouette" in gv else False)] = 0.0
        rows.append(dict(unit=uid, image=r["image"], governs=gv, picture_mm2=round(m.sum() / ppm ** 2, 1),
                         recoloured_mm2=round(n_col / ppm ** 2, 1), bared_mm2=round(n_sil / ppm ** 2, 1)))
    out = dict(ref, rgb=rgb, grey=rgb @ np.array([0.299, 0.587, 0.114]))
    if cw is not None: out["closeup_weight"] = cw
    return out, rows
