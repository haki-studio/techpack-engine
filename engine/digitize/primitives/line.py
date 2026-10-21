"""line: outlines, cracks, tile lines - a run / bean along the traced centreline of a thin mark.

The claim (closed close_mm) is skeletonised; each skeleton component >= min_len_mm becomes a polyline (dst2.centreline
of the component dilated by 0.6 mm, as stratum.cracks), one `line` part each: bean / run along it (DirSpec mode
contour, construct rule "column"-free: source "outline" with meta outline_angle = the chord's angle, line = the points;
the file is judged by the line's own technique). params.thin_mm (default 1.6): only marks an opening of this width
removes (thin) are lines; params.max_lines caps the count (longest first).
params: close_mm 0.3, thin_mm 1.6, min_len_mm 4, max_lines 200, width_mm 0.6."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import LineString
import dst2
from digitize.primitives import register, part, forced_thread
from digitize.schema import DirSpec

D = dict(close_mm=0.3, thin_mm=1.6, min_len_mm=4.0, max_lines=200, width_mm=0.6)


@register("line")
def recognise(ctx, lp, z, claim):
    from skimage.morphology import skeletonize
    from digitize.extract.splitters import dominant
    P = dict(D); P.update(lp.get("params") or {})
    ev = ctx.ev; parts = []; used = np.zeros_like(claim); ft = forced_thread(ctx, lp)
    m = ndi.binary_closing(claim, ctx.disk(P["close_mm"])) | claim
    if P["thin_mm"]: m = m & ~ndi.binary_opening(m, ctx.disk(P["thin_mm"]))
    sk = skeletonize(m); lab, n = ndi.label(sk, np.ones((3, 3), bool))
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    for i in (np.argsort(-sizes[1:])[: P["max_lines"]] + 1):
        if sizes[i] / ev.ppm < P["min_len_mm"]: break
        comp = ndi.binary_dilation(lab == i, ctx.disk(0.6))
        gs = ev.polys(comp, min_mm2=0.3, simplify=0.1)
        if not gs: continue
        g = max(gs, key=lambda q: q.area)
        c = dst2.centreline(g) if g.geom_type == "Polygon" else None
        if c is None or c.length < P["min_len_mm"]: continue
        c = LineString(c.simplify(0.3).coords)
        t = ft or dominant(ctx, lab == i) or dominant(ctx, comp)
        if t is None: continue
        used |= comp & claim
        a = math.degrees(math.atan2(c.coords[-1][1] - c.coords[0][1], c.coords[-1][0] - c.coords[0][0])) % 180
        parts.append(part(ctx, lp, "line", c.buffer(P["width_mm"] / 2), t, z, DirSpec(a, mode="contour", source="outline", note="along the traced line"),
                          None, line=[list(q) for q in c.coords], outline_angle=round(a, 2)))
    return parts, used
