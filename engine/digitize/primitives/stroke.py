"""stroke: 1-7 mm strokes (lettering from pixels, stems, fins, rails, branches) - a satin column ACROSS the stroke.

  1. components of the claim (closed close_mm) >= min_mm2; each is cut into LIMBS at its skeleton junctions (trunk.limbs:
     spurs dropped, every pixel to the nearest kept limb).
  2. per limb: the medial axis (dst2.centreline); mean width w = area / axis length. A stroke needs min_w_mm <= w and
     axis >= min_aspect x (w + sewn_extra_mm) (LESSONS B36: a column sews ~0.25-0.5 mm wider than its art); the axis' last half-width (it runs into a square end's corners) is trimmed.
  3. w <= max_w_mm: ONE `stroke` part, split satin in column mode along the centreline (construct rule "column": across
     the centreline's mean direction; judged on the file per stitch by trunk.column_adherence). Wider: the limb is a
     cord (its own primitive), so it goes back to the zones below unless params.wide = "cord" (then sewn as cords).
Blobs (not a stroke) are given back (not used), so a lower part claims them.
params: min_mm2 3, close_mm 0.5, min_w_mm 1.0, max_w_mm 7.0 (rule 4), min_aspect 2.5, min_limb_mm 2.0, wide "give_back"."""
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import LineString
from shapely.ops import substring
import dst2
from digitize.primitives import register, part, forced_thread
from digitize.schema import DirSpec, Part

D = dict(min_mm2=3.0, close_mm=0.5, min_w_mm=1.0, max_w_mm=7.0, min_aspect=2.5, min_limb_mm=2.0, wide="give_back", sewn_extra_mm=0.5)


@register("stroke")
def recognise(ctx, lp, z, claim):
    from digitize.extract.splitters import dominant
    from digitize.extract.splitters.trunk import limbs
    from digitize.extract.splitters.construct import basis as cbasis
    P = dict(D); P.update(lp.get("params") or {})
    ev = ctx.ev; parts = []; used = np.zeros_like(claim); ft = forced_thread(ctx, lp)
    if not claim.any(): return parts, used
    m = ndi.binary_closing(claim, ctx.disk(P["close_mm"])) & (claim | ndi.binary_dilation(claim))
    lab, n = ndi.label(m); sizes = np.bincount(lab.ravel(), minlength=n + 1) / ev.ppm ** 2
    wide = []
    for ci in range(1, n + 1):
        if sizes[ci] < P["min_mm2"]: continue
        C = lab == ci
        for li, Lm in enumerate(limbs(ctx, C, P["min_limb_mm"])):
            gs = ev.polys(Lm, min_mm2=0.5, simplify=0.2)
            if not gs: continue
            G = max(gs, key=lambda q: q.area)
            if G.geom_type != "Polygon": G = max(G.geoms, key=lambda q: q.area)
            line = dst2.centreline(G)
            if line is None or line.length < 1.0: continue
            line = LineString(line.simplify(0.8).coords); w = G.area / line.length
            if w < P["min_w_mm"] or line.length < P["min_aspect"] * (w + P["sewn_extra_mm"]): continue   # B36: it sews wider
            if w > P["max_w_mm"]: wide.append(Lm); continue
            if line.length > 3 * w: line = substring(line, w / 2, line.length - w / 2)
            cl = [list(map(float, q)) for q in line.coords]; con = dict(rule="column", cl=cl)
            probe = Part(id="_", kind="stroke", geom=G, thread="", z=0, dir=DirSpec(0.0, mode="contour", source="splitter"), meta=dict(construct=con))
            ang, why = cbasis(probe)
            if ang is None: continue
            used |= Lm
            t = ft or dominant(ctx, Lm) or dominant(ctx, C)
            parts.append(part(ctx, lp, "stroke", G, t, z, DirSpec(ang, mode="contour", source="splitter", note="satin column across the stroke"),
                              Lm, limb=li, cl=cl, w=round(w, 2), construct=con, group=lp["pid"]))
    if wide and P["wide"] == "cord":
        from digitize.primitives import cord
        wm = np.zeros_like(claim)
        for Lm in wide: wm |= Lm
        ps, u = cord.recognise(ctx, lp, z, wm); parts += ps; used |= u
    return parts, used
