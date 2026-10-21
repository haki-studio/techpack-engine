"""radial: florets, fins, tails, rays - a cluster of radial satins, each from its own centre (rule 4: face-on florets).

  1. silhouette (close 1 mm, holes filled, open 0.4 mm); masses >= min_mass_mm2.
  2. centres: local maxima of the smoothed lightness, prominent over a wider blur (blossom.centres: every face-on floret
     reads as a lit dome), >= sep_mm / 2 apart. params.centres = "seeds" uses the label's hint seeds instead.
  3. each centre owns its Voronoi cell inside the mass; radius = fit x the distance to the cell edge, capped at r_max
     (a WHOLE floret that fits: a clipped radial reads as a satin blob, not a fan).
  4. outline: params.lobes >= 3 -> an n-petal notched outline (petal axes every 360/n deg, the first pointing away from
     the mass centre); 0 -> a disc. Minus the knot hole. One `radial` part (radial satin; DirSpec mode radial, construct
     rule radial, meta centre). Under r_min / min_mm2: no petals, only the knot (rule 9).
  5. bead (params.bead, default true): a `bead` at the centre (dot technique) in the palest other thread of the label's
     tones, else a thread different from what surrounds it (never an invisible bead); sewn first.
  6. ground (params.ground: "angle" | "grain" | null): the mass minus the florets and knots as ONE `plane` part (angle:
     params.ground_angle, source label) or `band_grain`-like guided part (grain), in the darkest thread covering
     >= ground_share, sewn LAST with the florets and knots knocked out of it (B2 / B37: details first, the darkest
     connected tone last hides the travel between them).
params: min_mass_mm2 15, sep_mm 4, r_max 3.2, r_min 1.5, fit 1.35, min_mm2 5, lobes 5, notch_mm 0.6, bead true, bead_d 1.5,
peak_sigma_mm 0.6, tophat_mm 3, prominence 4, ground null, ground_angle null, ground_share 0.15, centres "lightness"."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Point, Polygon
from digitize.primitives import register, part, forced_thread, label_dir, union, lum, silhouette, threads_in
from digitize.schema import DirSpec

D = dict(min_mass_mm2=15.0, sep_mm=4.0, r_max=3.2, r_min=1.5, fit=1.35, min_mm2=5.0, lobes=5, notch_mm=0.6, notch_deg=8.0,
         waist=0.7, bead=True, bead_d=1.5, peak_sigma_mm=0.6, tophat_mm=3.0, prominence=4.0, ground=None, ground_angle=None,
         ground_share=0.15, centres="lightness")


def lobed_outline(c, r, phase, n=5, notch=0.6, notch_deg=8.0, waist=0.7, pts=180):
    """a face-on n-lobed outline (blossom.five_petals for any n; n < 3 = a disc)"""
    if n < 3: return Point(c).buffer(r, 32)
    per = 360.0 / n; out = []
    for i in range(pts):
        t = 360.0 * i / pts; psi = ((t - phase + per / 2) % per) - per / 2
        rho = r * (waist + (1 - waist) * max(0.0, math.cos(math.radians(psi * 180.0 / per))) ** 0.5)
        if abs(psi) < notch_deg / 2: rho -= notch * (1 - abs(psi) / (notch_deg / 2))
        out.append((c[0] + rho * math.cos(math.radians(t)), c[1] + rho * math.sin(math.radians(t))))
    return Polygon(out).buffer(0)


@register("radial")
def recognise(ctx, lp, z, claim):
    from digitize.extract.splitters.blossom import centres as light_centres
    from digitize.extract.splitters.construct import basis as cbasis
    from digitize.schema import Part
    P = dict(D); P.update(lp.get("params") or {})
    ev = ctx.ev; ppm = ev.ppm; parts = []; used = np.zeros_like(claim)
    if not claim.any(): return parts, used
    sil = silhouette(ctx, claim, 1.0, 0.4)
    lab, n = ndi.label(sil); sizes = np.bincount(lab.ravel(), minlength=n + 1) / ppm ** 2
    tones = [ctx.tone_thread[t] for t in (lp["tones"] if lp["tones"] != "all" else ev.keys) if ctx.tone_thread.get(t)]
    tones = sorted(set(tones), key=lambda t: lum(ctx, t))
    ft = forced_thread(ctx, lp); k_member = 0
    bc = dict(peak_sigma_mm=P["peak_sigma_mm"], tophat_mm=P["tophat_mm"], prominence=P["prominence"], sep_mm=P["sep_mm"])
    for mi in range(1, n + 1):
        if sizes[mi] < P["min_mass_mm2"]: continue
        M = lab == mi; used |= M
        tin = threads_in(ctx, M)
        if not tin: continue
        present = sorted([t for t, _ in tin], key=lambda t: lum(ctx, t))
        share = dict(tin)
        ground_t = next((t for t in present if share[t] >= P["ground_share"]), present[-1])
        gs = ev.polys(M, min_mm2=1.0)
        if not gs: continue
        G = union(gs); gc = G.centroid
        if P["centres"] == "seeds": cs = [tuple(s) for s in lp.get("seeds", []) if G.distance(Point(s)) < 1.0]
        else: cs = light_centres(ctx, M, bc)
        beads = []
        if cs:
            mk = np.zeros(M.shape, np.int32)
            for i, (x, y) in enumerate(cs, 1):
                px, py = ev.to_px(x, y); mk[min(M.shape[0] - 1, int(py)), min(M.shape[1] - 1, int(px))] = i
            _, (iy, ix) = ndi.distance_transform_edt(mk == 0, return_indices=True)
            cell = mk[iy, ix] * M
            bnd = np.zeros_like(cell, bool); bnd[:, 1:] |= cell[:, 1:] != cell[:, :-1]; bnd[1:, :] |= cell[1:, :] != cell[:-1, :]
            cdist = ndi.distance_transform_edt(~(bnd | ~M))
            lighter = [t for t in tones if lum(ctx, t) > lum(ctx, ground_t)] or [t for t in present if t != ground_t] or [ground_t]
            for i in sorted(range(len(cs)), key=lambda i: (cs[i][1], cs[i][0])):
                c = cs[i]; cm = cell == i + 1
                px, py = ev.to_px(*c); px, py = min(M.shape[1] - 1, int(px)), min(M.shape[0] - 1, int(py))
                r = min(P["r_max"], P["fit"] * float(cdist[py, px]) / ppm)
                cg = ev.polys(cm, min_mm2=0.2) if cm.any() else []
                if not cg: continue
                reg = union(cg).intersection(G).intersection(Point(c).buffer(r))
                vv = ctx.thread_lab[cm]; vv = vv[vv >= 0]
                cc = {t: int((vv == ctx.threads.index(t)).sum()) for t in lighter}
                fl_t = ft or (max(cc, key=lambda t: (cc[t], lum(ctx, t))) if cc else lighter[-1])
                ph = math.degrees(math.atan2(c[1] - gc.y, c[0] - gc.x)) % (360.0 / max(P["lobes"], 1))
                kd = P["bead_d"] if P["bead"] else 0.0
                fg = lobed_outline(c, r, ph, int(P["lobes"]), P["notch_mm"], P["notch_deg"], P["waist"]).intersection(reg)
                if kd: fg = fg.difference(Point(c).buffer(kd / 2))
                fg = fg.buffer(0); k_member += 1
                fl = None
                if r >= P["r_min"] and not fg.is_empty and fg.area >= P["min_mm2"]:
                    fl = part(ctx, lp, "radial", fg, fl_t, z - 0.1, DirSpec(0.0, mode="radial", source="splitter", note="radial from its centre"),
                              ev.mask(fg), centre=[float(c[0]), float(c[1])], construct=dict(rule="radial"), phase=round(ph, 2),
                              group=f"{lp['pid']}.m{mi}")
                    parts.append(fl); beads.append(fg)
                if kd:
                    around = fl_t if fl is not None else ground_t
                    others = [t for t in tones if t not in (fl_t, ground_t)]
                    bead_t = (others[-1] if others and lum(ctx, others[-1]) > lum(ctx, fl_t) else (others[0] if others else (ground_t if around == fl_t else fl_t)))
                    ang = 0.0                                               # a bead: one row angle by rule (house kind bead)
                    kg = Point(c).buffer(kd / 2, 16); beads.append(kg)
                    parts.append(part(ctx, lp, "bead", kg, bead_t, z - 0.2, DirSpec(ang, source="rule", note="a bead: rows at the rule angle"),
                                      None, knots=[(float(c[0]), float(c[1]), kd, ang)], art_d=kd, house_min=False,
                                      member_of=fl.id if fl is not None else None, group=f"{lp['pid']}.m{mi}"))
        if P["ground"]:
            gg = G.difference(union(beads)).buffer(0) if beads else G
            if gg.is_empty: continue
            gm = ev.mask(gg) & M
            if P["ground"] == "grain":
                from digitize import direction as DR
                grid = ctx.field().grid(gg, step=1.0); fm = DR.grid_mean(grid, gg)
                if fm is None: continue
                gd, ge, gk = DirSpec(fm, source="field-mean", note="ground: the grain's mean"), dict(field=grid, field_angle=round(fm, 2)), "plane_grain"
            else:
                if P["ground_angle"] is None: raise ValueError(f"label {lp['pid']}: ground 'angle' needs params.ground_angle")
                gd, ge = label_dir(lp, P["ground_angle"]); gk = "plane"
            gp = part(ctx, lp, gk, gg, ground_t, z, gd, gm, ground=True, mass=int(mi), group=f"{lp['pid']}.m{mi}", **ge)
            parts.append(gp)
            for q in parts:
                if q.meta.get("group") == f"{lp['pid']}.m{mi}" and q is not gp: q.meta["knockout_of"] = gp.id
    return parts, used
