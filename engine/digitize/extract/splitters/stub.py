"""zone_stub + pool partition: one part per connected tone component of the zone (>= min_part_mm2; protected accents
>= min_protected_mm2), tatami. Direction: zone_stub = the reference grain's mean over the part (structure tensor,
coherence-weighted, so it is a measured, declared number: source "field-mean"); pool = the rulebook's fixed angle.
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
        if kind == "zone_stub":
            ang, coh = ev.field_angle(mask=m); d = ctx.rb.direction(kind, field=ang if ang is not None else 0.0)
            d.note = f"field-mean over the part, coherence {coh:.2f}"
        else:
            d = ctx.rb.direction(kind); coh = None
        pid = ctx.new_id(f"{zone['id']}")
        parts.append(Part(id=pid, kind=kind, geom=g, thread=thread, z=z, dir=d, zone=zone["id"], rgb=ev.mean_rgb(m),
                          meta=dict(coherence=round(coh, 3) if coh is not None else None, splitter="stub" if kind == "zone_stub" else kind)))
    return parts, used


def split_pool(ctx, zone, z, claim):
    from scipy import ndimage as ndi
    m = claim | ndi.binary_closing(claim, ctx.disk(1.0))         # foam is one surface: close the speckle
    parts, _ = split(ctx, zone, z, m, kind="pool")
    return parts, m
