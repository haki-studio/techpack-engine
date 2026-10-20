"""Blossom splitter (ENGINE_PLAN M3b; motif playbook: blossoms = canopy random tatami -> florets (5 notched satin petals +
knot) -> branches; direction: radial florets; match motif counts, LESSONS A2 / A14).

  1. silhouette: the zone's claimed blossom pixels, closed (1 mm), hole-filled, opened (0.4 mm); masses >= min_mass_mm2
     (input pixels only, LESSONS A14).
  2. canopy: one `canopy` part per mass (sewn LAST of the blossom parts, florets and knots knocked out of it) in the DARKEST blossom thread that covers >= canopy_share of it (the shadow
     between florets), tatami at the mean reference grain over the mass (field-mean, SELF-DERIVED like the stubs; a rule
     angle of 45 deg was tried first and matched 0 % of the canopy area: BENCH_m3b.md); rule 3 neighbours are separated
     by digitize.direction.separate.
  3. florets: every floret in the reference is a domed blob with a lit centre, so floret CENTRES are the local maxima of
     the mass's lightness (smoothed peak_sigma_mm, top-hat over tophat_mm >= prominence, >= floret_sep_mm / 2 apart).
     Each floret owns its centre's Voronoi cell inside the mass; its radius is fit x the distance from the centre to
     the cell's edge (capped at floret_r_max), so every floret is WHOLE (a clipped radial reads back as a satin blob, not
     a fan) and the canopy shows between them, as the deep tone does in the reference.
  4. floret part: the cell cut to a 5-PETAL outline (polar profile: each petal rounded, NOTCHED at its tip, notch_mm
     deep), minus the knot hole: one `floret` part, radial satin (DirSpec mode "radial": every stitch on a ray from the
     centre; rule 4 allows radial for face-on florets; construct rule "radial"). The 5-petal phase points the first
     petal away from the mass centre (florets open outward). Thread = the most common blossom thread LIGHTER than the
     canopy inside the cell. A floret under floret_r_min / floret_min_mm2 is too small for petals (rule 9): only its knot.
  5. knot: one `knot` bead (dot technique) at the centre, sewn BEFORE the canopy and knocked out of it (B2) in the palest blossom thread that is neither the floret's nor
     the canopy's (else the deepest), its bead rows between two petal axes (construct rule between_petals).
Branches are not drawn here: the trunk splitter (trunk.py) takes the bark pixels between the blossoms (kind branch,
sewn after the florets).

radial_adherence(plan, segs, labels, crop) judges the WRITTEN file: the share of each floret's visible stitches that lie
within 15 deg of the ray from its centre (the radial counterpart of the guided parts' field adherence).
The extract log (plan meta splitter_stats) gets: masses, florets (centres found), florets_petalled, knots_only."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from digitize.schema import Part, DirSpec
from digitize.extract.splitters.construct import basis as cbasis
from digitize import direction as DR

DEFAULTS = dict(min_mass_mm2=15.0, canopy_share=0.15, peak_sigma_mm=0.6, tophat_mm=3.0, prominence=4.0, floret_sep_mm=4.0,
                floret_min_mm2=5.0, floret_r_max=3.2, floret_r_min=1.5, fit=1.35, knot_d=1.5, notch_mm=0.6, notch_deg=8.0, petal_waist=0.7)


def _cfg(ctx):
    d = dict(DEFAULTS); d.update(ctx.cfg.get("blossom", {}) or {}); return d


def lum_of(ctx, t):
    ev = ctx.ev; h = ev.hex[ev.keys.index(t)].lstrip("#") if t in ev.keys else "808080"
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4)); return 0.299 * r + 0.587 * g + 0.114 * b


def centres(ctx, mass, sc):
    """floret centres: local maxima of the smoothed lightness inside the mass, prominent over its surroundings"""
    from skimage.feature import peak_local_max
    ev = ctx.ev; ppm = ev.ppm
    L = ev.rgb @ np.array([0.299, 0.587, 0.114])
    Ls = ndi.gaussian_filter(L, sc["peak_sigma_mm"] * ppm)
    top = Ls - ndi.gaussian_filter(L, sc["tophat_mm"] * ppm)
    inner = ndi.binary_erosion(mass, iterations=max(1, int(round(0.5 * ppm))))
    if not inner.any(): return []
    pk = peak_local_max(np.where(inner, Ls, Ls.min()), min_distance=max(1, int(round(sc["floret_sep_mm"] * ppm / 2))),
                        labels=inner.astype(int), exclude_border=False)
    return [ev.to_mm(x + 0.5, y + 0.5) for y, x in pk if top[y, x] >= sc["prominence"]]


def five_petals(c, r, phase, notch=0.6, notch_deg=8.0, waist=0.7, n=180):
    """a face-on 5-petal floret outline: each petal's radius rises from waist * r between petals to r at its middle,
    with a V notch notch_mm deep, notch_deg wide, at the tip (cherry petal)"""
    pts = []
    for i in range(n):
        t = 360.0 * i / n; psi = ((t - phase + 36.0) % 72.0) - 36.0             # angle from the petal's middle
        rho = r * (waist + (1 - waist) * math.cos(math.radians(psi * 2.5)) ** 0.5 if abs(psi) < 36 else waist * r)
        if abs(psi) < notch_deg / 2: rho -= notch * (1 - abs(psi) / (notch_deg / 2))
        pts.append((c[0] + rho * math.cos(math.radians(t)), c[1] + rho * math.sin(math.radians(t))))
    return Polygon(pts).buffer(0)


def split(ctx, zone, z, claim):
    ev = ctx.ev; sc = _cfg(ctx); rb = ctx.rb; parts = []; ppm = ev.ppm
    sil = ndi.binary_fill_holes(ndi.binary_closing(claim, ctx.disk(1.0)) | claim)
    sil = ndi.binary_opening(sil, ctx.disk(0.4))
    lab, n = ndi.label(sil); used = np.zeros_like(sil)
    sizes = np.bincount(lab.ravel(), minlength=n + 1) / ppm ** 2
    zf, zk = -0.1, -0.2         # knots, then florets, then the canopy (the deep tone in the gaps) LAST, with the florets and
                                # beads knocked out of it (LESSONS B2 / B14: details first, the darkest connected tone last,
                                # so the travel between florets hides under the canopy; M3b run r8: florets sewn on top cost
                                # 54 trims in their stop)
    tones = sorted({t for t in (zone.get("tones") or []) if t in ctx.threads}, key=lambda t: lum_of(ctx, t))
    stats = dict(masses=0, florets=0, florets_petalled=0, knots_only=0)
    for mi in range(1, n + 1):
        if sizes[mi] < sc["min_mass_mm2"]: continue
        M = lab == mi; used |= M; stats["masses"] += 1
        v = ctx.thread_lab[M]; v = v[v >= 0]
        if not len(v): continue
        cnt = np.bincount(v, minlength=len(ctx.threads)) / len(v)
        present = sorted([ctx.threads[k] for k in range(len(ctx.threads)) if cnt[k] > 0], key=lambda t: lum_of(ctx, t))
        canopy_t = next((t for t in present if cnt[ctx.threads.index(t)] >= sc["canopy_share"]), present[-1])
        gs = ev.polys(M, min_mm2=1.0)
        if not gs: continue
        G = gs[0] if len(gs) == 1 else unary_union(gs)
        grid = ctx.field().grid(G, step=1.0); fa = DR.grid_mean(grid, G)
        if fa is None: raise ValueError(f"zone {zone['id']}: canopy mass {mi} has no field: a direction is never defaulted (rule 2)")
        d = rb.direction("canopy", field=fa)
        canopy = Part(id=ctx.new_id(zone["id"]), kind="canopy", geom=G, thread=canopy_t, z=z, dir=d,
                          zone=zone["id"], rgb=ev.mean_rgb(M), meta=dict(splitter="blossom", mass=int(mi), field_angle=d.angle, field=grid))
        parts.append(canopy); beads = []
        cs = centres(ctx, M, sc)
        if not cs: continue
        mk = np.zeros(M.shape, np.int32)                       # Voronoi cells of the centres inside the mass
        for i, (x, y) in enumerate(cs, 1):
            px, py = ev.to_px(x, y); mk[min(M.shape[0] - 1, int(py)), min(M.shape[1] - 1, int(px))] = i
        _, (iy, ix) = ndi.distance_transform_edt(mk == 0, return_indices=True)
        cell = mk[iy, ix] * M
        bnd = np.zeros_like(cell); bnd[:, 1:] |= cell[:, 1:] != cell[:, :-1]; bnd[1:, :] |= cell[1:, :] != cell[:-1, :]
        cdist = ndi.distance_transform_edt(~(bnd.astype(bool) | ~M))        # distance to the cell's edge (other cell / mass)
        gc = G.centroid
        lighter = [t for t in tones if lum_of(ctx, t) > lum_of(ctx, canopy_t)] or [t for t in present if t != canopy_t] or [canopy_t]
        for i in sorted(range(len(cs)), key=lambda i: (cs[i][1], cs[i][0])):
            c = cs[i]; stats["florets"] += 1; kd = sc["knot_d"]
            cm = cell == i + 1
            px, py = ev.to_px(*c); px, py = min(M.shape[1] - 1, int(px)), min(M.shape[0] - 1, int(py))
            r = min(sc["floret_r_max"], sc["fit"] * float(cdist[py, px]) / ppm)      # a WHOLE floret that fits its cell
            cg = ev.polys(cm, min_mm2=0.2) if cm.any() else []
            if not cg: continue
            reg = (cg[0] if len(cg) == 1 else unary_union(cg)).intersection(G).intersection(Point(c).buffer(r))
            vv = ctx.thread_lab[cm]; vv = vv[vv >= 0]
            cc = {t: int((vv == ctx.threads.index(t)).sum()) for t in lighter}
            fl_t = max(cc, key=lambda t: (cc[t], lum_of(ctx, t))) if cc else lighter[-1]
            knot_c = [t for t in tones if t not in (fl_t, canopy_t)]
            knot_t = (knot_c[-1] if knot_c and lum_of(ctx, knot_c[-1]) > lum_of(ctx, fl_t) else (knot_c[0] if knot_c else fl_t))
            fid = f"{zone['id']}.f{stats['florets']:03d}"
            ph = math.degrees(math.atan2(c[1] - gc.y, c[0] - gc.x)) % 72.0     # first petal points away from the mass centre
            fg = five_petals(c, r, ph, sc["notch_mm"], sc["notch_deg"], sc["petal_waist"]).intersection(reg).difference(Point(c).buffer(kd / 2)).buffer(0)
            if r >= sc["floret_r_min"] and not fg.is_empty and fg.area >= sc["floret_min_mm2"]:
                con = dict(rule="radial", centre=[float(c[0]), float(c[1])])
                parts.append(Part(id=f"{fid}", kind="floret", geom=fg, thread=fl_t, z=z + zf,
                                  dir=DirSpec(0.0, mode="radial", source="splitter", note="radial from the floret centre"),
                                  zone=zone["id"], meta=dict(splitter="blossom", mass=int(mi), phase=round(ph, 2), centre=[float(c[0]), float(c[1])],
                                                             construct=con)))
                stats["florets_petalled"] += 1
            else:
                stats["knots_only"] += 1
            con = dict(rule="between_petals", phase=round(ph, 2))
            ang = cbasis(Part(id="_", kind="knot", geom=Point(c).buffer(kd / 2), thread=knot_t, z=0, dir=DirSpec(0.0), meta=dict(construct=con)))[0]
            beads.append(Point(c).buffer(kd / 2, 16))
            if parts[-1].kind == "floret" and parts[-1].id == fid: beads.append(parts[-1].geom)
            parts.append(Part(id=f"{fid}.k", kind="knot", geom=Point(c).buffer(kd / 2, 16), thread=knot_t, z=z + zk,
                              dir=DirSpec(ang, source="splitter", note="bead rows between two petal axes"), zone=zone["id"],
                              meta=dict(splitter="blossom", mass=int(mi), floret=fid, knots=[(c[0], c[1], kd, ang)],
                                        art_d=kd, house_min=False, construct=con)))
        if beads: canopy.geom = G.difference(unary_union(beads)).buffer(0)           # knock florets + beads out of the canopy
    ctx.stats = getattr(ctx, "stats", {}); ctx.stats[zone["id"]] = stats
    return parts, used


def radial_adherence(plan, segs, labels, crop, ppm=12.0, max_dev=15.0, min_len=0.6, centre_mm=0.9):
    """radial parts on the WRITTEN file: each visible stitch (>= min_len, midpoint >= centre_mm from the centre) vs the ray
    from its part's centre through the stitch midpoint. -> dict(parts, stitches, within, pct_within)"""
    import qa
    vis, idx = qa.visible_segments(segs, crop, ppm=ppm, return_index=True)
    cen = {p.id: p.meta.get("centre") for p in plan.parts if p.dir.mode == "radial" and p.meta.get("centre")}
    n = w = 0; seen = set()
    for s, i in zip(vis, idx):
        pid = labels[i]
        if pid not in cen: continue
        L = math.hypot(s[2] - s[0], s[3] - s[1])
        if L < min_len: continue
        cx, cy = cen[pid]; mx, my = (s[0] + s[2]) / 2, (s[1] + s[3]) / 2
        if math.hypot(mx - cx, my - cy) < centre_mm: continue
        a = math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])) % 180; ray = math.degrees(math.atan2(my - cy, mx - cx)) % 180
        d = abs(a - ray) % 180; d = min(d, 180 - d)
        n += 1; w += d <= max_dev; seen.add(pid)
    return dict(parts=len(seen), stitches=n, within=int(w), pct_within=round(100.0 * w / max(1, n), 1))
