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
meta: splitter "crown", mass, clump, attach ("bark" | "base"), construct; M4g sequencing hints: lit pieces carry
knockout_of = their dark clump, every part group = its mass (ignored by the M1 sequencer)."""
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
                dark_share=0.15, lit_close_mm=0.6, min_lit_mm2=6.0, support_tones=["cf_brown"], support_mm=3.0, lit_z=-0.3,
                # --- M4c --- visible lit pieces, dark slivers to the lit, a smooth fan across the crown
                lit_vis_mm2=20.0, lit_vis_w_mm=2.5, lit_grow_max_mm=1.5, sliver_mm=0.5, smooth=True, smooth_nb_w=0.5, touch_mm=0.3)


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


def smooth_angle(axes):
    """the weighted AXIAL mean of the axes [{from, to, w}] (deg): a clump's own fan axis and its touching neighbours'
    (rule 2: one deliberate angle per clump, a smooth fan across the crown; construct rule "fan_smooth")"""
    C = S = 0.0
    for a in axes:
        t = math.atan2(a["to"][1] - a["from"][1], a["to"][0] - a["from"][0]); C += a["w"] * math.cos(2 * t); S += a["w"] * math.sin(2 * t)
    return math.degrees(0.5 * math.atan2(S, C)) % 180.0


def _width_ok(g, w):
    return not g.buffer(-w / 2.0).is_empty


def visible_lit(pieces, clump, sc, stats):
    """M4c: lit highlights sized to stay visible (>= lit_vis_mm2 and lit_vis_w_mm wide after the knockout and the seam;
    27 of 77 lit pieces showed < 12 visible stitches on the M3b crop). Fidelity first (A11): a small highlight is never
    dropped, it is GROWN inside its clump (buffer steps of 0.25 mm, at most lit_grow_max_mm) until it holds a visible
    tatami; pieces that touch after growing become one piece. stats counts grown / still small / added area."""
    out = []
    for lg in pieces:
        a0 = lg.area; g2 = lg
        if a0 < sc["lit_vis_mm2"] or not _width_ok(lg, sc["lit_vis_w_mm"]):
            k = 0.25
            while k <= sc["lit_grow_max_mm"] + 1e-9:
                g2 = lg.buffer(k).intersection(clump).buffer(0)
                if g2.area >= sc["lit_vis_mm2"] and _width_ok(g2, sc["lit_vis_w_mm"]): break
                k += 0.25
            stats["lit_grown"] += 1; stats["lit_grown_mm2"] += g2.area - a0
            if g2.area < sc["lit_vis_mm2"] or not _width_ok(g2, sc["lit_vis_w_mm"]): stats["lit_still_small"] += 1
        out.append(g2)
    if len(out) < 2: return [q for q in out if not q.is_empty]
    u = unary_union(out)
    return [u] if u.geom_type == "Polygon" else [q for q in getattr(u, "geoms", []) if q.geom_type == "Polygon" and q.area > 0.05]


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
    stats = dict(masses=0, clumps=0, attach_bark=0, attach_base=0, lit=0, no_construct=0, lit_grown=0, lit_grown_mm2=0.0,
                 lit_still_small=0, slivers_to_lit_mm2=0.0, smoothed=0, unsmoothed_rule3=0)
    clumps_ = []                                                     # pass 1: clumps, their own fan axis, their lit pieces
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
            lits = []
            for t in tones:
                if lum_of(ctx, t) <= lum_of(ctx, dark): continue
                lm = ndi.binary_closing(cm & (ctx.thread_lab == ctx.threads.index(t)), ctx.disk(sc["lit_close_mm"])) & cm
                lits += [(t, lg) for lg in visible_lit(ev.polys(lm, min_mm2=sc["min_lit_mm2"]), g, sc, stats)]
            clumps_.append(dict(cid=ctx.new_id(zone["id"]), g=g, cm=cm, dark=dark, att=att, attach=attach, frm=frm, to=to, ang=ang,
                                zc=z + 0.001 * rank, mi=int(mi), rank=rank, lits=lits))
    # pass 2: a SMOOTH fan across the crown (rule 2). Each clump's angle is the axial mean of its own fan axis and the axes
    # of the clumps it touches (half weight): neighbouring clumps at 60-90 deg to each other made the crown tiles chaotic
    # (M3b crop: 34 of 80 touching pairs > 45 deg apart; smoothed 9; the reference grain itself 7) while the clump keeps
    # its own elongation (59 % of clump area within 25 deg of the reference grain vs 62 % unsmoothed; a fan from the mass
    # base: 9 %). Rule 3 (direction.separate, run.yaml separate_kinds) then turns same-thread neighbours <= 25 deg apart.
    from shapely.strtree import STRtree
    tree = STRtree([c["g"] for c in clumps_]) if clumps_ else None
    for i, c in enumerate(clumps_):
        axes = [{"from": c["frm"], "to": c["to"], "w": round(float(c["g"].area), 3)}]
        if sc["smooth"]:
            for j in tree.query(c["g"].buffer(sc["touch_mm"]), predicate="intersects"):
                j = int(j)
                if j == i: continue
                o = clumps_[j]; axes.append({"from": o["frm"], "to": o["to"], "w": round(float(sc["smooth_nb_w"] * o["g"].area), 3)})
        c["axes"] = axes; c["ang_s"] = smooth_angle(axes)
    if sc["smooth"] and clumps_:
        # rule 3 first: smoothing pulls touching clumps together, and a clump with several same-thread neighbours can then
        # be left with no angle >= 15 deg from all of them within 25 deg of its own (direction.separate leaves it
        # unresolved; M4c crop r1: crown close pairs 4 -> 10). Such a clump keeps its OWN fan axis (no smoothing).
        from digitize import direction as DR
        sep = tuple(float(v) for v in ctx.rb.principles.get("neighbour_sep_deg", [15, 25]))
        for _ in range(3):
            probes = [Part(id=c["cid"], kind="crown_clump_dark", geom=c["g"], thread=c["dark"], z=0, meta={},
                           dir=DirSpec(c["ang_s"], source="splitter")) for c in clumps_]
            DR.separate(probes, sep, touch=sc["touch_mm"])
            bad = [i for i, q in enumerate(probes) if q.meta.get("sep_unresolved") and len(clumps_[i]["axes"]) > 1]
            if not bad: break
            for i in bad:
                c = clumps_[i]; c["axes"] = c["axes"][:1]; c["ang_s"] = smooth_angle(c["axes"]); stats["unsmoothed_rule3"] += 1
    stats["smoothed"] = sum(1 for c in clumps_ if len(c["axes"]) > 1)
    for c in clumps_:                                                # pass 3: parts (lit first, knocked out of the dark)
        g, cid = c["g"], c["cid"]; zc = c["zc"]; lits = []
        lgeoms = [lg for _, lg in c["lits"]]
        gd = g.difference(unary_union(lgeoms)).buffer(0) if lgeoms else g     # the shadow around the lit pieces
        if lgeoms and not gd.is_empty and sc["sliver_mm"] > 0:
            # dark slivers between lit pieces and the clump edge (< sliver_mm wide) sew as short edge stitches at every
            # angle (part of the M3b dark clumps' angle spread): each joins the lit piece it touches
            clean = gd.buffer(-sc["sliver_mm"] / 2).buffer(sc["sliver_mm"] / 2).intersection(gd).buffer(0)
            sl = gd.difference(clean).buffer(0)
            for q in ([sl] if sl.geom_type == "Polygon" else list(getattr(sl, "geoms", []))):
                if q.is_empty or q.geom_type != "Polygon" or q.area < 0.01: continue
                k = max(range(len(lgeoms)), key=lambda k: lgeoms[k].buffer(0.05).intersection(q).area)
                if lgeoms[k].buffer(0.05).intersects(q):
                    lgeoms[k] = lgeoms[k].union(q).buffer(0); stats["slivers_to_lit_mm2"] += q.area
            gd = g.difference(unary_union(lgeoms)).buffer(0)
        for (t, _), lg in zip(c["lits"], lgeoms):
            stats["lit"] += 1; lits.append(len(parts))
            at = lg.representative_point()
            parts.append(Part(id=ctx.new_id(zone["id"]), kind="crown_clump_lit", geom=lg, thread=t, z=zc + sc["lit_z"],
                              dir=DirSpec(c["ang_s"], source="splitter", note=f"lit side of clump {cid}: the clump's own smoothed fan angle"),
                              zone=zone["id"], rgb=None,
                              meta=dict(splitter="crown", mass=c["mi"], clump=c["rank"], lit_of=cid, attach=c["att"], group=f"{zone['id']}.mass{c['mi']}",
                                        construct=dict(rule="fan_smooth", axes=c["axes"], at=[float(at.x), float(at.y)]))))
        if gd.is_empty: continue
        for k in lits: parts[k].meta["knockout_of"] = cid                  # M4g hint: lit knocked out of its dark clump
        parts.append(Part(id=cid, kind="crown_clump_dark", geom=gd, thread=c["dark"], z=zc,
                          dir=DirSpec(c["ang_s"], source="splitter", note=f"fans along the clump from its {c['att']} attachment, smoothed with its neighbours"),
                          zone=zone["id"], rgb=ev.mean_rgb(c["cm"]),
                          meta=dict(splitter="crown", mass=c["mi"], clump=c["rank"], attach=c["att"], group=f"{zone['id']}.mass{c['mi']}",
                                    attach_pt=[float(c["attach"][0]), float(c["attach"][1])],
                                    construct=dict(rule="fan_smooth", axes=c["axes"]))))
    stats["lit_grown_mm2"] = round(stats["lit_grown_mm2"], 1); stats["slivers_to_lit_mm2"] = round(stats["slivers_to_lit_mm2"], 1)
    ctx.stats = getattr(ctx, "stats", {}); ctx.stats[zone["id"]] = stats
    return parts, used
