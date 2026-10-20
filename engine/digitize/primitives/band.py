"""band: sky, strata, far roof rows, stripes - an area sewn as strips ALONG one direction (tatami / guided fill).

intent "along" (default): the mass's own run (the long side of its minimum rotated rectangle, or params.axis_deg is NOT
   read - the run is geometry). The mass is cut into strips parallel to that run: every evidence row across the run votes
   for its dominant thread, runs of rows with one vote form a strip (thinner than min_band_mm merge into a neighbour,
   wider than max_band_mm split evenly; sky.bands_of generalised to any run direction). Each strip = one `band` part,
   tatami along the run: construct rule "axis" on the strip's own long mid-line (independent: a position, not the grain).
intent "angle": the labelled angle. Tone pieces (splitters.partition) -> one `band` part each at that angle (source
   "label"). Same-thread neighbours are turned by digitize.direction.separate when the run lists `band` in separate_kinds.
intent "grain": strips that follow the reference grain where it turns (stratum.mass_phase + bands_of): `band_grain`
   parts, guided fill along the field (SELF-DERIVED, A24), alternating +-band_offset_deg (rule 3).
params: min_band_mm 3, max_band_mm 16, min_part_mm2 20, close_mm 0.6, band_offset_deg 10 (grain), min_mass_mm2 12."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Polygon
from digitize.primitives import register, part, forced_thread, label_dir, union, axis_chord
from digitize.schema import DirSpec

D = dict(min_band_mm=3.0, max_band_mm=16.0, min_part_mm2=20.0, close_mm=0.6, band_offset_deg=10.0, min_mass_mm2=12.0, bin_mm=1.0)


def _p(lp): d = dict(D); d.update(lp.get("params") or {}); return d


def run_bands(votes, min_rows, max_rows):
    """votes per row (thread or None) -> [(r0, r1, thread)]: sky.bands_of, then runs wider than max_rows split evenly"""
    from digitize.extract.splitters.sky import bands_of
    out = []
    for r0, r1, t in bands_of(votes, min_rows):
        n = max(1, int(math.ceil((r1 - r0) / max(1, max_rows))))
        for i in range(n): out.append((r0 + (r1 - r0) * i // n, r0 + (r1 - r0) * (i + 1) // n, t))
    return out


def _along(ctx, lp, z, claim, P):
    ev = ctx.ev; parts = []; used = np.zeros_like(claim); ft = forced_thread(ctx, lp)
    lab, n = ndi.label(ndi.binary_closing(claim, ctx.disk(P["close_mm"])) & claim | claim)
    for mi in range(1, n + 1):
        M = lab == mi
        if M.sum() / ev.ppm ** 2 < P["min_mass_mm2"]: continue
        gs = ev.polys(M, min_mm2=0.5)
        if not gs: continue
        G = union(gs); used |= M
        from digitize.techniques.turning import long_axis
        gp = G if G.geom_type == "Polygon" else max(G.geoms, key=lambda q: q.area)
        a, b = long_axis(gp); th = math.atan2(b[1] - a[1], b[0] - a[0])
        ux, uy = math.cos(th), math.sin(th); vx, vy = -uy, ux                 # u along the run, v across it
        yy, xx = np.nonzero(M); X, Y = ev.to_mm(xx + 0.5, yy + 0.5)
        V = X * vx + Y * vy; U = X * ux + Y * uy
        step = 1.0 / ev.ppm; v0 = V.min(); nb = int(math.ceil((V.max() - v0) / step)) + 1
        rows = np.clip(((V - v0) / step).astype(int), 0, nb - 1)
        t = ctx.thread_lab[yy, xx]
        votes = []
        for r in range(nb):
            sel = (rows == r) & (t >= 0)
            votes.append(None if sel.sum() < 2 else (ft or ctx.threads[int(np.bincount(t[sel]).argmax())]))
        bands = run_bands(votes, max(1, int(round(P["min_band_mm"] / step))), max(1, int(round(P["max_band_mm"] / step))))
        u0, u1 = U.min() - 2, U.max() + 2
        strips = []
        for k, (r0, r1, thr) in enumerate(bands):
            va = v0 + r0 * step - (2.0 if k == 0 else 0.0); vb = v0 + r1 * step + (2.0 if k == len(bands) - 1 else 0.0)
            strip = Polygon([(u0 * ux + va * vx, u0 * uy + va * vy), (u1 * ux + va * vx, u1 * uy + va * vy),
                             (u1 * ux + vb * vx, u1 * uy + vb * vy), (u0 * ux + vb * vx, u0 * uy + vb * vy)])
            g = G.intersection(strip).buffer(0)
            if not g.is_empty and g.area >= 1.0: strips.append([g, thr])
        # a strip that is not elongated (a blob the outline cut off) cannot be sewn "along its run": it joins the
        # neighbouring strip (the thinner neighbour first), and the joined strip is checked again
        while len(strips) > 1:
            bad = next((i for i, (g, _) in enumerate(strips) if axis_chord(g)[0] is None), None)
            if bad is None: break
            j = bad - 1 if bad > 0 else 1
            if 0 < bad < len(strips) - 1 and strips[bad + 1][0].area < strips[bad - 1][0].area: j = bad + 1
            a_, b_ = sorted((bad, j)); keep_t = strips[j][1]
            strips[a_] = [union([strips[a_][0], strips[b_][0]]).buffer(0), keep_t]; del strips[b_]
        for k, (g, thr) in enumerate(strips):
            line, why = axis_chord(g)
            if line is None:
                raise ValueError(f"label {lp['pid']}: band mass {mi} is not elongated ({why}): label it a plane (intent angle) or a lobe")
            sm = ev.mask(g) & M
            d = DirSpec(why, source="splitter", note=f"band {k} along its own run")
            parts.append(part(ctx, lp, "band", g, thr, z, d, sm, band=k, mass=int(mi), construct=dict(rule="axis", line=line)))
    return parts, used


def _angle(ctx, lp, z, claim, P):
    from digitize.extract.splitters import partition
    ev = ctx.ev; parts = []; ft = forced_thread(ctx, lp)
    if ft is not None:
        comps = [(ft, claim)]
    else:
        comps = partition(ctx, claim, P["min_part_mm2"], ctx.cfg["stub"]["min_protected_mm2"])
    for thr, m in comps:
        gs = ev.polys(m, min_mm2=0.5)
        if not gs: continue
        d, extra = label_dir(lp)
        parts.append(part(ctx, lp, "band", union(gs), thr, z, d, m, **extra))
    return parts, claim.copy()


def _grain(ctx, lp, z, claim, P):
    from digitize.extract.splitters import partition
    from digitize.extract.splitters.stratum import mass_phase, bands_of
    from digitize import direction as DR
    ev = ctx.ev; parts = []; used = np.zeros_like(claim); F = ctx.field(); off = float(P["band_offset_deg"])
    lab, n = ndi.label(ndi.binary_closing(claim, ctx.disk(P["close_mm"])) | claim)
    lab = np.where(claim, lab, 0)
    for mi in range(1, n + 1):
        mass = lab == mi
        if mass.sum() / ev.ppm ** 2 < P["min_mass_mm2"]: continue
        used |= mass
        phi, _ = mass_phase(F, mass, ev.ppm)
        bands = bands_of(phi, ctx.thread_lab, mass, P["bin_mm"], P["min_band_mm"], P["max_band_mm"], len(ctx.threads))
        for k, (a, b) in enumerate(bands):
            bm = mass & (phi >= a) & (phi < b)
            if not bm.any(): continue
            sign = 1.0 if k % 2 == 0 else -1.0
            for thr, pm in partition(ctx, bm, P["min_part_mm2"], ctx.cfg["stub"]["min_protected_mm2"]):
                gs = ev.polys(pm, min_mm2=0.5)
                if not gs: continue
                g = union(gs); grid = F.grid(g, step=1.0); fm = DR.grid_mean(grid, g)
                if fm is None: raise ValueError(f"label {lp['pid']}: band piece without evidence pixels (no field)")
                d = DirSpec((fm + sign * off) % 180.0, mode="field", source="field", note=f"grain {fm:.1f} {'+' if sign > 0 else '-'}{off:g}")
                parts.append(part(ctx, lp, "band_grain", g, forced_thread(ctx, lp) or thr, z, d, pm, band=k, mass=int(mi), field=grid,
                                  field_mean=round(fm, 2), band_offset_deg=sign * off))
    return parts, used


@register("band")
def recognise(ctx, lp, z, claim):
    P = _p(lp)
    if not claim.any(): return [], claim.copy()
    return {"along": _along, "angle": _angle, "grain": _grain}[lp["intent"]](ctx, lp, z, claim, P)
