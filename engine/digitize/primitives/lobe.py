"""lobe: clouds, leaves, petals, crowns, bodies - one part per rounded lobe (+ optional shade / lit layers).

  1. silhouette (close close_mm, holes filled, open open_mm); masses >= min_mass_mm2 (input pixels only, A14).
  2. lobes: watershed of the mass's distance transform from its peaks (>= lobe_min_r_mm deep, >= lobe_sep_mm apart),
     lobes under min_lobe_mm2 merged into the neighbour they share most border with (cloud.lobes).
  3. tone: the lobe's thread = colour (forced) or, by params.tone: "lit" (the lightest thread covering >= 25 % of the
     most common, a cloud's lit face) or "dominant" (the most common thread, default).
  4. layers (params.layers): "shade" = darker threads inside the lobe (>= min_layer_mm2) as an OPEN layer on top
     (`lobe_shade`: blend, no underlay, rules 7 / 8), at the lobe's own angle + 20 deg (rule 3); "lit" = lighter threads inside the lobe as their
     own `lobe` parts sewn FIRST and knocked out of the lobe (LESSONS B2 / B37: details first, the dark last hides the
     travel), at the lobe's angle; "none" (default) = one part per lobe.
  5. direction per intent: outline (default) = the lobe's own long axis (construct rule long_axis, "outline" bucket);
     grain = guided fill along the reference grain (`lobe_grain`, self-derived); angle = the labelled angle (source label).
Lobes higher up the garment sew first (back to front, rule 5): z rises 0.01 per lobe from the top.
params: close_mm 1.0, open_mm 0.4, min_mass_mm2 12, lobe_min_r_mm 1.5, lobe_sep_mm 4, min_lobe_mm2 25, tone "dominant",
layers "none", min_layer_mm2 8, layer_close_mm 0.6."""
import numpy as np
from scipy import ndimage as ndi
from digitize.primitives import register, part, forced_thread, label_dir, union, lum, silhouette, long_axis_dir, threads_in
from digitize.schema import DirSpec

D = dict(close_mm=1.0, open_mm=0.4, min_mass_mm2=12.0, lobe_min_r_mm=1.5, lobe_sep_mm=4.0, min_lobe_mm2=25.0, tone="dominant",
         layers="none", min_layer_mm2=8.0, layer_close_mm=0.6, shade_turn_deg=20.0)


def _dir(ctx, lp, g):
    """(DirSpec, meta, kind) for one lobe by intent"""
    it = lp["intent"]
    if it == "angle":
        d, extra = label_dir(lp); return d, extra, "lobe"
    if it == "grain":
        from digitize import direction as DR
        grid = ctx.field().grid(g, step=1.0); fm = DR.grid_mean(grid, g)
        if fm is None: raise ValueError(f"label {lp['pid']}: lobe without evidence pixels (no field)")
        return DirSpec(fm, mode="field", source="field", note="guided fill along the reference grain"), dict(field=grid, field_mean=round(fm, 2)), "lobe_grain"
    d, extra = long_axis_dir(g, "along the lobe's own long axis")
    if d is None: raise ValueError(f"label {lp['pid']}: lobe long axis does not rebuild ({extra})")
    return d, extra, "lobe"


@register("lobe")
def recognise(ctx, lp, z, claim):
    from digitize.extract.splitters.cloud import lobes
    P = dict(D); P.update(lp.get("params") or {})
    ev = ctx.ev; parts = []; used = np.zeros_like(claim); ft = forced_thread(ctx, lp)
    if not claim.any(): return parts, used
    sil = silhouette(ctx, claim, P["close_mm"], P["open_mm"])
    lab, n = ndi.label(sil); sizes = np.bincount(lab.ravel(), minlength=n + 1) / ev.ppm ** 2
    for mi in range(1, n + 1):
        if sizes[mi] < P["min_mass_mm2"]: continue
        S = lab == mi; used |= S
        L = lobes(ctx, S, P)
        ids = [i for i in np.unique(L) if i > 0]
        low = {i: np.nonzero(L == i)[0].max() for i in ids}
        for rank, i in enumerate(sorted(ids, key=lambda i: low[i])):              # back (higher on the garment) first
            lm = L == i; tin = threads_in(ctx, lm)
            if not tin and not ft: continue
            if ft: thr = ft
            elif P["tone"] == "lit":
                top = tin[0][1]; thr = max([t for t, s in tin if s >= 0.25 * top], key=lambda t: lum(ctx, t))
            else: thr = tin[0][0]
            gs = ev.polys(lm, min_mm2=1.0)
            if not gs: continue
            g = union(gs); zl = z + 0.01 * rank
            lit_geoms = []
            if P["layers"] == "lit" and not ft:                                    # lighter pieces first, knocked out
                for t, s in tin:
                    if lum(ctx, t) <= lum(ctx, thr): continue
                    sm = ndi.binary_closing(lm & (ctx.thread_lab == ctx.threads.index(t)), ctx.disk(P["layer_close_mm"])) & lm
                    for q in ev.polys(sm, min_mm2=P["min_layer_mm2"]):
                        lit_geoms.append((q, t, sm))
            d, extra, kind = _dir(ctx, lp, g)
            lobe_part = part(ctx, lp, kind, g, thr, zl, d, lm, lobe=int(rank), mass=int(mi), group=f"{lp['pid']}.m{mi}", **extra)
            for q, t, sm in lit_geoms:                     # one deliberate angle per lobe: its lit pieces take the LOBE's
                dq, eq = _layer_dir(ctx, lp, g, q, d, 0.0)
                parts.append(part(ctx, lp, "lobe" if kind == "lobe_grain" and dq.mode == "fixed" else kind, q, t, zl - 0.005, dq, ev.mask(q),
                                  lobe=int(rank), mass=int(mi), lit_of=lobe_part.id, knockout_of=lobe_part.id, group=f"{lp['pid']}.m{mi}", **eq))
            if lit_geoms:
                lobe_part.geom = g.difference(union([q for q, _, _ in lit_geoms])).buffer(0)
            parts.append(lobe_part)
            if P["layers"] == "shade" and not ft:                                  # darker pieces as an open layer on top
                for t, s in tin:
                    if lum(ctx, t) >= lum(ctx, thr): continue
                    sm = ndi.binary_closing(lm & (ctx.thread_lab == ctx.threads.index(t)), ctx.disk(P["layer_close_mm"])) & lm
                    if sm.sum() / ev.ppm ** 2 < P["min_layer_mm2"]: continue
                    sg = ev.polys(sm, min_mm2=P["min_layer_mm2"] / 2)
                    if not sg: continue
                    sgeom = union(sg)
                    ds, es = _layer_dir(ctx, lp, g, sgeom, d, P["shade_turn_deg"], fixed=True)
                    parts.append(part(ctx, lp, "lobe_shade", sgeom, t, zl + 0.3, ds, sm, lobe=int(rank), mass=int(mi), shade_of=lobe_part.id, **es))
    return parts, used


def _layer_dir(ctx, lp, lobe_g, g, d, turn, fixed=False):
    """a lit / shade layer's direction = its LOBE's, rebuilt by the audit (+ a rule 3 turn recorded as sep_deg <= 25):
    outline -> construct long_axis of the lobe outline (stored as `of`, the layer must lie inside it); angle -> the label
    angle; grain -> the layer's own field (guided), or for a fixed open layer its field mean (field-mean)"""
    it = lp["intent"]; sep = {"sep_deg": float(turn)} if turn else {}
    if it == "angle":
        dd, extra = label_dir(lp, (lp["angle"] + turn) % 180.0); extra["label_angle"] = round(float(lp["angle"]) % 180.0, 2); extra.update(sep)
        return dd, extra
    if it == "grain":
        from digitize import direction as DR
        grid = ctx.field().grid(g, step=1.0); fm = DR.grid_mean(grid, g)
        if fm is None: raise ValueError(f"label {lp['pid']}: layer without evidence pixels (no field)")
        if fixed: return DirSpec((fm + turn) % 180.0, source="field-mean", note="layer: grain mean + turn"), dict(field=grid, field_angle=round(fm, 2), **sep)
        return DirSpec((fm + turn) % 180.0, mode="field", source="field", note="layer: guided"), dict(field=grid, field_mean=round(fm, 2), **sep)
    lg = lobe_g if lobe_g.geom_type == "Polygon" else max(lobe_g.geoms, key=lambda r: r.area)
    con = dict(rule="long_axis", of=[[round(x, 3), round(y, 3)] for x, y in lg.exterior.coords])
    from digitize.extract.splitters.construct import basis as cbasis
    from digitize.schema import Part
    a, why = cbasis(Part(id="_", kind="lobe", geom=g, thread="", z=0, dir=DirSpec(0.0, source="splitter"), meta=dict(construct=con)))
    if a is None: raise ValueError(f"label {lp['pid']}: layer long axis does not rebuild ({why})")
    return DirSpec((a + turn) % 180.0, source="splitter", note="layer: its lobe's long axis"), dict(construct=con, **sep)
