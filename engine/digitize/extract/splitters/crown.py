"""Crown splitter (ENGINE_PLAN M3b; motif playbook: trees = crowns as clumps (dark, then lit); clumps fan from the branch;
every clump touches a branch).

  1. silhouette: the zone's claimed foliage pixels, closed (1 mm), hole-filled, opened (0.4 mm); masses >= min_mass_mm2
     (input pixels only, LESSONS A14).
  2. clumps: each leaf clump in the reference is a LIT top over its shadow, so every lit highlight (lighter foliage
     threads, opened 0.5 mm, >= min_seed_mm2) seeds one clump and the mass is shared out to the nearest seed; clumps
     under min_clump_mm2 merge into the neighbour they share most border with. A mass with no lit highlight is cut
     into lobes (cloud.lobes on its distance transform).
  3. support (every clump touches a branch): the attachment point is the nearest BARK pixel (support_tones) within
     support_mm of the clump; a clump with no bark that close hangs from the crown itself, attached on the side
     facing the crown's base (the bottom of the mass, where the crown grows from). The extract log counts both.
  4. direction: a clump FANS out from its attachment along its own elongation: rows run along the clump's long axis
     (the mid-line of its minimum rotated rectangle), from the axis end nearer the attachment to the axis middle
     (construct rule "fan", rebuilt by digitize.audit). Lit pieces fan the same way along their own long axis, from the
     end nearer the clump's attachment. The angle is built from the traced OUTLINE, so its direction tiles are
     reported in the "outline" bucket, not as independent evidence (A24; BENCH_m3b.md: this rule was picked over a
     base-to-centre fan after comparing both against the reference grain).
  5. dark and lit: `crown_clump_lit` = each lighter thread's pixels in the clump (closed lit_close_mm, >= min_lit_mm2);
     `crown_clump_dark` = the rest of the clump in the darkest foliage thread covering >= dark_share of it. The lit
     pieces sew FIRST and are knocked out of the dark (LESSONS B2 / B14: the darkest connected tone last hides the travel
     between the lit pieces; M3b run r8: lit on top cost 34 trims in its stop). Visually the same "dark, then lit" layers
     (the playbook order) without the trims. Higher clumps sew first, so lower, front clumps overlap them.
meta: splitter "crown", mass, clump, attach ("bark" | "base"), construct."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Point
from shapely.ops import unary_union, nearest_points
from digitize.schema import Part, DirSpec
from digitize.extract.splitters.cloud import lobes
from digitize.extract.splitters.blossom import lum_of
from digitize.extract.splitters.construct import basis as cbasis

DEFAULTS = dict(seed_lit=True, min_seed_mm2=3.0, min_mass_mm2=20.0, clump_sep_mm=6.0, clump_min_r_mm=1.5, min_clump_mm2=20.0,
                dark_share=0.15, lit_close_mm=0.6, min_lit_mm2=6.0, support_tones=["cf_brown"], support_mm=3.0, lit_z=-0.3)


def _cfg(ctx):
    d = dict(DEFAULTS); d.update(ctx.cfg.get("crown", {}) or {}); return d


def clumps(ctx, M, tones, sc):
    """clumps seeded by the LIT highlights: label image (0 = none), or None when the mass has no lit seed"""
    ppm = ctx.ev.ppm
    v = ctx.thread_lab[M]; v = v[v >= 0]
    if not len(v) or len(tones) < 2: return None
    cnt = np.bincount(v, minlength=len(ctx.threads)) / len(v)
    present = [t for t in tones if cnt[ctx.threads.index(t)] > 0]
    dark = next((t for t in present if cnt[ctx.threads.index(t)] >= sc["dark_share"]), None)
    if dark is None: return None
    lit_i = [ctx.threads.index(t) for t in tones if lum_of(ctx, t) > lum_of(ctx, dark)]
    lit = M & np.isin(ctx.thread_lab, lit_i)
    lit = ndi.binary_opening(ndi.binary_closing(lit, ctx.disk(sc["lit_close_mm"])), ctx.disk(0.5)) & M
    seeds, n = ndi.label(lit)
    if n == 0: return None
    sz = np.bincount(seeds.ravel(), minlength=n + 1) / ppm ** 2
    keep = np.zeros(n + 1, np.int32); k = 0
    for i in range(1, n + 1):
        if sz[i] >= sc["min_seed_mm2"]: k += 1; keep[i] = k
    if k == 0: return None
    seeds = keep[seeds]
    _, (iy, ix) = ndi.distance_transform_edt(seeds == 0, return_indices=True)
    lab = seeds[iy, ix] * M
    st = np.ones((3, 3), bool); min_px = sc["min_clump_mm2"] * ppm ** 2
    while True:
        ids, c = np.unique(lab[lab > 0], return_counts=True)
        small = [(cc, i) for i, cc in zip(ids, c) if cc < min_px]
        if not small or len(ids) < 2: break
        _, i = min(small); me = lab == i; ring = ndi.binary_dilation(me, st) & ~me & (lab > 0)
        if not ring.any(): break
        lab[me] = np.bincount(lab[ring]).argmax()
    return lab


def fan(g, attach):
    """(from, to, angle) for a clump g attached at `attach`: along g's long axis, from the axis end nearer the attachment
    to the axis middle; None when the construction does not rebuild (digitize.audit would reject it)"""
    from digitize.techniques.turning import long_axis
    gp = g if g.geom_type == "Polygon" else max(g.geoms, key=lambda q: q.area)
    a, b = long_axis(gp)
    if math.dist(a, attach) > math.dist(b, attach): a, b = b, a
    to = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    probe = Part(id="_", kind="crown_clump_dark", geom=g, thread="", z=0, dir=DirSpec(0.0),
                 meta=dict(construct=dict(rule="fan", **{"from": list(a), "to": list(to)})))
    ang, why = cbasis(probe)
    if ang is None: return None
    return [float(a[0]), float(a[1])], [float(to[0]), float(to[1])], ang


def split(ctx, zone, z, claim):
    ev = ctx.ev; sc = _cfg(ctx); ppm = ev.ppm; parts = []
    sil = ndi.binary_fill_holes(ndi.binary_closing(claim, ctx.disk(1.0)) | claim)
    sil = ndi.binary_opening(sil, ctx.disk(0.4))
    lab, n = ndi.label(sil); used = np.zeros_like(sil)
    sizes = np.bincount(lab.ravel(), minlength=n + 1) / ppm ** 2
    bark = np.isin(ev.tone, [ev.keys.index(k) for k in sc["support_tones"] if k in ev.keys])
    if bark.any():
        bark_d, (by, bx) = ndi.distance_transform_edt(~bark, return_indices=True)
    tones = sorted({t for t in (zone.get("tones") or []) if t in ctx.threads}, key=lambda t: lum_of(ctx, t))
    lsc = dict(lobe_sep_mm=sc["clump_sep_mm"], lobe_min_r_mm=sc["clump_min_r_mm"], min_lobe_mm2=sc["min_clump_mm2"])
    stats = dict(masses=0, clumps=0, attach_bark=0, attach_base=0, lit=0, no_construct=0)
    for mi in range(1, n + 1):
        if sizes[mi] < sc["min_mass_mm2"]: continue
        M = lab == mi; used |= M; stats["masses"] += 1
        ys, xs = np.nonzero(M); yb = ys.max()
        base = ev.to_mm(float(xs[ys >= yb - ppm].mean()) + 0.5, float(yb) + 0.5)
        L = clumps(ctx, M, tones, sc) if sc["seed_lit"] else None
        if L is None: L = lobes(ctx, M, lsc)
        ids = [i for i in np.unique(L) if i > 0]
        low = {i: np.nonzero(L == i)[0].max() for i in ids}
        for rank, i in enumerate(sorted(ids, key=lambda i: low[i])):        # back (higher on the garment) first
            cm = L == i
            v = ctx.thread_lab[cm]; v = v[v >= 0]
            if not len(v): continue
            gs = ev.polys(cm, min_mm2=1.0)
            if not gs: continue
            g = gs[0] if len(gs) == 1 else unary_union(gs)
            cnt = np.bincount(v, minlength=len(ctx.threads)) / len(v)
            present = sorted([ctx.threads[k] for k in range(len(ctx.threads)) if cnt[k] > 0], key=lambda t: lum_of(ctx, t))
            dark = next((t for t in present if cnt[ctx.threads.index(t)] >= sc["dark_share"]), present[-1])
            att, attach = "base", None
            if bark.any():
                yy, xx = np.nonzero(cm); k = int(np.argmin(bark_d[yy, xx]))
                if bark_d[yy[k], xx[k]] / ppm <= sc["support_mm"]:
                    attach = ev.to_mm(bx[yy[k], xx[k]] + 0.5, by[yy[k], xx[k]] + 0.5); att = "bark"
            if attach is None: attach = nearest_points(g.boundary, Point(base))[0].coords[0]
            f = fan(g, attach)
            if f is None: stats["no_construct"] += 1; continue
            frm, to, ang = f
            stats["clumps"] += 1; stats["attach_" + att] += 1
            zc = z + 0.001 * rank; cid = ctx.new_id(zone["id"]); lits = []
            for t in tones:
                if lum_of(ctx, t) <= lum_of(ctx, dark): continue
                lm = ndi.binary_closing(cm & (ctx.thread_lab == ctx.threads.index(t)), ctx.disk(sc["lit_close_mm"])) & cm
                for lg in ev.polys(lm, min_mm2=sc["min_lit_mm2"]):
                    lf = fan(lg, attach)
                    if lf is None: stats["no_construct"] += 1; continue
                    stats["lit"] += 1; lits.append(lg)
                    parts.append(Part(id=ctx.new_id(zone["id"]), kind="crown_clump_lit", geom=lg, thread=t, z=zc + sc["lit_z"],
                                      dir=DirSpec(lf[2], source="splitter", note=f"lit side of clump {cid}, fans from the same attachment"),
                                      zone=zone["id"], rgb=None,
                                      meta=dict(splitter="crown", mass=int(mi), clump=int(rank), lit_of=cid, attach=att,
                                                construct=dict(rule="fan", **{"from": lf[0], "to": lf[1]}))))
            gd = g.difference(unary_union(lits)).buffer(0) if lits else g          # the shadow around the lit pieces
            if gd.is_empty: continue
            parts.append(Part(id=cid, kind="crown_clump_dark", geom=gd, thread=dark, z=zc,
                              dir=DirSpec(ang, source="splitter", note=f"fans along the clump from its {att} attachment"), zone=zone["id"],
                              rgb=ev.mean_rgb(cm), meta=dict(splitter="crown", mass=int(mi), clump=int(rank), attach=att,
                                                             attach_pt=[float(attach[0]), float(attach[1])],
                                                             construct=dict(rule="fan", **{"from": frm, "to": to}))))
    ctx.stats = getattr(ctx, "stats", {}); ctx.stats[zone["id"]] = stats
    return parts, used
