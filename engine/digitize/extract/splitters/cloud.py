"""Cloud splitter (ENGINE_PLAN M2; motif playbook: clouds = one object per LOBE, contour / turning fill or near-vertical
split satin, shade as an open layer, wisps at the sky angle at half density).

  1. silhouette: the zone's claimed cloud pixels, closed (1 mm) and hole-filled, opened (0.4 mm); masses >= min_mass_mm2
     (input pixels only, LESSONS A14).
  2. wisps: what an opening of wisp_mm removes (the thin trails) -> cloud_wisp parts (tatami at the sky angle, half
     density); the rest is the body.
  3. lobes: watershed of the body's distance transform from its peaks (>= lobe_min_r_mm deep, >= lobe_sep_mm apart),
     lobes under min_lobe_mm2 merged into the neighbour they share most border with. Each lobe = one cloud_lobe part
     in its dominant LIT thread: a turning fill (guided_fill along the lobe's reference grain) or a contour fill
     (rows follow the outline), whichever the run enables first (rulebook dir_by_technique). Lobes higher up the garment are further
     back: they sew first (z rises with the lobe's lowest point), so the lower, front lobes overlap them.
  4. shade: inside each lobe, the pixels of a darker cloud thread (>= min_shade_mm2 after a 0.6 mm closing) -> a
     cloud_shade part: an OPEN layer (blend, mode open, no underlay; rules 7, 8) on top of the lobe, at the measured grain.
"""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.ops import unary_union
from digitize.schema import Part


def _cfg(ctx):
    d = dict(min_mass_mm2=12.0, wisp_mm=3.0, lobe_min_r_mm=1.5, lobe_sep_mm=4.0, min_lobe_mm2=25.0, min_shade_mm2=8.0, min_wisp_mm2=10.0)
    d.update(ctx.cfg.get("cloud", {}) or {}); return d


def _lum(ctx, t):
    ev = ctx.ev; h = ev.hex[ev.keys.index(t)].lstrip("#") if t in ev.keys else "808080"
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4)); return 0.299 * r + 0.587 * g + 0.114 * b


def lobes(ctx, body, sc):
    """watershed of the distance transform -> label image of lobes (0 = none)"""
    from skimage.segmentation import watershed
    from skimage.feature import peak_local_max
    ppm = ctx.ev.ppm; dt = ndi.distance_transform_edt(body) / ppm
    pk = peak_local_max(dt, min_distance=max(1, int(round(sc["lobe_sep_mm"] / 2 * ppm))), threshold_abs=sc["lobe_min_r_mm"],
                        labels=ndi.label(body)[0], exclude_border=False)
    mk = np.zeros(body.shape, np.int32)
    for i, (y, x) in enumerate(pk, 1): mk[y, x] = i
    if not len(pk): return ndi.label(body)[0]
    lab = watershed(-dt, mk, mask=body)
    # merge small lobes into the neighbour sharing the longest border, smallest first
    st = np.ones((3, 3), bool); min_px = sc["min_lobe_mm2"] * ppm ** 2
    while True:
        ids, cnt = np.unique(lab[lab > 0], return_counts=True)
        small = [(c, i) for i, c in zip(ids, cnt) if c < min_px]
        if not small or len(ids) < 2: break
        c, i = min(small); me = lab == i; ring = ndi.binary_dilation(me, st) & ~me & (lab > 0)
        if not ring.any(): break
        lab[me] = np.bincount(lab[ring]).argmax()
    return lab


def split(ctx, zone, z, claim):
    ev = ctx.ev; sc = _cfg(ctx); rb = ctx.rb; parts = []
    sil = ndi.binary_fill_holes(ndi.binary_closing(claim, ctx.disk(1.0)) | claim)
    sil = ndi.binary_opening(sil, ctx.disk(0.4))
    lab, n = ndi.label(sil); used = np.zeros_like(sil)
    sizes = np.bincount(lab.ravel(), minlength=n + 1) / ev.ppm ** 2
    zs = rb.rule("cloud_shade").get("z_offset", 0.3)
    tech = rb.technique_for("cloud_lobe")
    for mi in range(1, n + 1):
        if sizes[mi] < sc["min_mass_mm2"]: continue
        S = lab == mi; used |= S
        body = ndi.binary_opening(S, ctx.disk(sc["wisp_mm"]))
        wisp = S & ~body
        L = lobes(ctx, body, sc) if body.any() else np.zeros(S.shape, int)
        ids = [i for i in np.unique(L) if i > 0]
        ys = {i: np.nonzero(L == i)[0].max() for i in ids}                      # lowest point of each lobe (px row)
        for rank, i in enumerate(sorted(ids, key=lambda i: ys[i])):              # back (higher on the garment) first
            lm = L == i
            v = ctx.thread_lab[lm]; v = v[v >= 0]
            if not len(v): continue
            cnt = np.bincount(v, minlength=len(ctx.threads))
            cands = [k for k in np.argsort(-cnt) if cnt[k] >= 0.25 * cnt.max()]
            lit = max(cands, key=lambda k: _lum(ctx, ctx.threads[k]))            # the lobe's lit tone
            thread = ctx.threads[lit]
            gs = ev.polys(lm, min_mm2=1.0)
            if not gs: continue
            g = gs[0] if len(gs) == 1 else unary_union(gs)
            r = g.minimum_rotated_rectangle; cs = list(r.exterior.coords)
            e = max(((cs[k], cs[k + 1]) for k in range(4)), key=lambda ab: math.dist(*ab))
            axis = math.degrees(math.atan2(e[1][1] - e[0][1], e[1][0] - e[0][0])) % 180
            F = ctx.field(); grid = F.grid(g, step=1.0)
            from digitize import direction as DR
            fm = DR.grid_mean(grid, g)
            d = rb.direction("cloud_lobe", field=fm, outline=axis, technique=tech)
            zl = z + 0.01 * rank
            meta = dict(splitter="cloud", lobe=int(rank), mass=int(mi))
            if d.source == "outline": meta["outline_angle"] = d.angle
            if d.mode == "field": meta.update(field=grid, field_mean=round(fm, 2))
            lobe_id = ctx.new_id(zone["id"])
            parts.append(Part(id=lobe_id, kind="cloud_lobe", geom=g, thread=thread, z=zl, dir=d, zone=zone["id"],
                              rgb=ev.mean_rgb(lm), meta=meta))
            # shade: darker cloud threads inside the lobe -> one open layer per shade thread
            for k in cands + [k for k in np.argsort(-cnt) if cnt[k] > 0 and k not in cands]:
                if k == lit or _lum(ctx, ctx.threads[k]) >= _lum(ctx, thread): continue
                sm = lm & (ctx.thread_lab == k)
                sm = ndi.binary_closing(sm, ctx.disk(0.6)) & lm
                if sm.sum() / ev.ppm ** 2 < sc["min_shade_mm2"]: continue
                sg = ev.polys(sm, min_mm2=sc["min_shade_mm2"] / 2)
                if not sg: continue
                fa, coh = ev.field_angle(mask=sm)
                if fa is None: continue
                ds = rb.direction("cloud_shade", field=fa)
                parts.append(Part(id=ctx.new_id(zone["id"]), kind="cloud_shade", geom=sg[0] if len(sg) == 1 else unary_union(sg),
                                  thread=ctx.threads[k], z=zl + zs, dir=ds, zone=zone["id"], rgb=ev.mean_rgb(sm),
                                  meta=dict(splitter="cloud", lobe=int(rank), mass=int(mi), field_angle=ds.angle, coherence=round(coh, 3),
                                            shade_of=lobe_id)))
        wl, wn = ndi.label(wisp)
        for wi in range(1, wn + 1):
            wm = wl == wi
            if wm.sum() / ev.ppm ** 2 < sc["min_wisp_mm2"]: continue
            v = ctx.thread_lab[wm]; v = v[v >= 0]
            if not len(v): continue
            gs = ev.polys(wm, min_mm2=1.0)
            if not gs: continue
            parts.append(Part(id=ctx.new_id(zone["id"]), kind="cloud_wisp", geom=gs[0] if len(gs) == 1 else unary_union(gs),
                              thread=ctx.threads[int(np.bincount(v).argmax())], z=z - 0.05, dir=rb.direction("cloud_wisp"),
                              zone=zone["id"], rgb=ev.mean_rgb(wm), meta=dict(splitter="cloud", mass=int(mi))))
    return parts, used
