"""zone_stub + pool partition: one part per connected tone component of the zone (>= min_part_mm2; protected accents
>= min_protected_mm2), tatami. Direction: zone_stub = the mean of the reference-grain field over the part (the field
grid is stored in meta["field"], so digitize.audit recomputes the angle instead of trusting it: source "field-mean");
pool = the rulebook's fixed angle.
A stand-in, honestly labelled: M2/M3 replace stubs with real splitters (clouds, strata, crowns, buildings)."""
from shapely.ops import unary_union
from digitize.schema import Part
from digitize.extract.splitters import partition


def split(ctx, zone, z, claim, kind="zone_stub"):
    sc = ctx.cfg["stub"]; ev = ctx.ev; parts = []; used = claim.copy()
    if not claim.any(): return parts, used
    for thread, m in partition(ctx, claim, sc["min_part_mm2"], sc["min_protected_mm2"]):
        geoms = ev.polys(m, min_mm2=0.5)
        if not geoms: continue
        g = geoms[0] if len(geoms) == 1 else unary_union(geoms)
        grid = None
        if kind == "zone_stub":
            _, coh = ev.field_angle(mask=m)
            from digitize import direction as DR
            grid = ctx.field().grid(g, step=1.0); ang = DR.grid_mean(grid, g)   # PR #6 review: recomputable from meta["field"]
            if ang is None:                                       # never a silent 0 deg (M1 review)
                raise ValueError(f"zone {zone['id']}: stub part ({thread}) has no evidence pixels, so it has no field-mean "
                                 f"angle; a direction is never defaulted (DIGITIZING_PRINCIPLES rule 2)")
            d = ctx.rb.direction(kind, field=ang)
            d.note = f"field-mean over the part, coherence {coh:.2f}"
        else:
            d = ctx.rb.direction(kind); coh = None
        pid = ctx.new_id(f"{zone['id']}")
        parts.append(Part(id=pid, kind=kind, geom=g, thread=thread, z=z, dir=d, zone=zone["id"], rgb=ev.mean_rgb(m),
                          meta=dict(coherence=round(coh, 3) if coh is not None else None, splitter="stub" if kind == "zone_stub" else kind,
                                         **({"field_angle": d.angle, "field": grid} if kind == "zone_stub" else {}))))
    return parts, used


def split_pool(ctx, zone, z, claim):
    from scipy import ndimage as ndi
    m = claim | ndi.binary_closing(claim, ctx.disk(1.0))         # foam is one surface: close the speckle
    parts, _ = split(ctx, zone, z, m, kind="pool")
    return parts, m
