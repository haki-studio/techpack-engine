"""plane: walls, roofs, flat graphic areas - tatami at ONE deliberate angle (the labeller's), per tone piece.

The claim is cut into tone pieces (splitters.partition: connected components per thread, pieces under min_part_mm2
absorbed into the neighbour they share most border with); colour: <key> sews the whole claim in one thread. Every piece
is one `plane` part at the labelled angle (DirSpec source "label", meta label_angle: independent of the reference grain,
like an answer; ENGINE_PLAN RE-PLAN table "plane: constructed (independent)"). Touching same-thread planes are turned by
digitize.direction.separate (rule 3) when the run lists `plane` in separate_kinds.
params: min_part_mm2 20, close_mm 0 (close specks of other tones into the plane)."""
import numpy as np
from scipy import ndimage as ndi
from digitize.primitives import register, part, forced_thread, label_dir, union

D = dict(min_part_mm2=20.0, close_mm=0.0)


@register("plane")
def recognise(ctx, lp, z, claim):
    from digitize.extract.splitters import partition
    P = dict(D); P.update(lp.get("params") or {})
    ev = ctx.ev; parts = []
    if not claim.any(): return parts, claim.copy()
    ft = forced_thread(ctx, lp)
    comps = [(ft, claim)] if ft else partition(ctx, claim, P["min_part_mm2"], ctx.cfg["stub"]["min_protected_mm2"])
    for thr, m in comps:
        gs = ev.polys(m, min_mm2=0.5)
        if not gs: continue
        d, extra = label_dir(lp)
        parts.append(part(ctx, lp, "plane", union(gs), thr, z, d, m, **extra))
    return parts, claim.copy()
