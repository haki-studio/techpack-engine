"""dot: eyes, studs, stars, beads - one bead (dot technique) per small round component, at its own centre and size.

Components of the claim (closed close_mm) between min_mm2 and max_mm2; each is one `bead` part: needle diameter =
the component's equal-area diameter, clamped to [min_d, max_d] (rule 9: studs 1-1.5 mm; a smaller art dot sews at the
minimum and is REPORTED, house_min). Bead rows at 0 deg (a rule: a round bead has no grain). Larger components are not
dots: they are given back to the zones below.
params: close_mm 0.3, min_mm2 0.3, max_mm2 12, min_d 1.0, max_d 3.0."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Point
from digitize.primitives import register, part, forced_thread
from digitize.schema import DirSpec

D = dict(close_mm=0.3, min_mm2=0.3, max_mm2=12.0, min_d=1.0, max_d=3.0)


@register("dot")
def recognise(ctx, lp, z, claim):
    from digitize.extract.splitters import dominant
    P = dict(D); P.update(lp.get("params") or {})
    ev = ctx.ev; parts = []; used = np.zeros_like(claim); ft = forced_thread(ctx, lp)
    m = ndi.binary_closing(claim, ctx.disk(P["close_mm"])) | claim
    lab, n = ndi.label(m)
    for ci, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is None: continue
        C = lab == ci; a = C.sum() / ev.ppm ** 2
        if a < P["min_mm2"] or a > P["max_mm2"]: continue
        yy, xx = np.nonzero(C); cx, cy = ev.to_mm(xx.mean() + 0.5, yy.mean() + 0.5)
        art = 2 * math.sqrt(a / math.pi); d = min(P["max_d"], max(P["min_d"], art))
        t = ft or dominant(ctx, C)
        if t is None: continue
        used |= C
        parts.append(part(ctx, lp, "bead", Point(cx, cy).buffer(d / 2, 16), t, z, DirSpec(0.0, source="rule", note="a bead: one row angle by rule"),
                          C, knots=[(float(cx), float(cy), round(d, 3), 0.0)], art_d=round(art, 3), house_min=art < P["min_d"]))
    return parts, used
