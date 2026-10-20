"""Trunk splitter (ENGINE_PLAN M3b; motif playbook: trees = trunk as split-satin strips along the axis; blossoms: branches
sewn after the florets).

  1. candidates: the zone's claimed bark pixels, closed (0.5 mm); components >= min_mm2 (input pixels only, LESSONS A14).
  2. support: a trunk or branch HOLDS a crown, so a component is kept only when >= support_frac of the ring around it
     (support_ring_mm) is crown pixels (blossom / foliage tones, evidence). Bark-coloured rock facets and timber in walls
     have no crown around them and go back to the zones below.
  3. shape: the medial axis (dst2.centreline); mean width = area / axis length. A stroke (length >= min_aspect x width,
     width >= min_w_mm) is kept; blobs go back.
  4. segments: the axis is cut where it turns more than max_turn_deg, so every part has ONE straight axis (a curved branch
     becomes several parts); cross-sections every 1 mm carry the outline with it (fall.sections).
  5. a limb no wider than strip_split_mm is a BRANCH: one `branch` part, a satin column ACROSS the stroke along the
     limb's centreline (split satin, column mode; DirSpec mode "contour", construct rule "column"), judged on the file by
     column_adherence (every visible stitch within 15 deg of across the centreline). A wider limb is a TRUNK: each
     segment is cut into n = ceil(width / strip_mm) strips along the axis (fall.cords) -> `trunk_strip` parts, split
     satin with the stitches ALONG the axis (construct rule "axis": the segment's chord). Two touching strips in the
     same thread alternate +-band_offset deg (rule 3, audited like strata bands).
meta: splitter "trunk", tree (component), segment, strip, construct."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
import dst2
from digitize.schema import Part, DirSpec
from digitize.extract.splitters import dominant
from digitize.extract.splitters.fall import sections, cords
from digitize.extract.splitters.construct import basis as cbasis, line_angle, polyline_angle
from shapely.geometry import Point
from shapely.ops import substring

DEFAULTS = dict(min_mm2=6.0, support_tones=["cf_pinklt", "cf_pink", "cf_rose"],
                support_ring_mm=2.0, support_frac=0.35, min_w_mm=1.0, max_w_mm=14.0, min_aspect=2.5, max_turn_deg=25.0,
                min_seg_mm=3.0, min_limb_mm=2.0, strip_split_mm=4.0, strip_mm=3.0, band_offset=10.0)


def _cfg(ctx):
    d = dict(DEFAULTS); d.update(ctx.cfg.get("trunk", {}) or {}); return d


def tangent_deg(line, s):
    return math.degrees(dst2.tangent_at(line, s)) % 360.0


def segments(P, line, max_turn=25.0, min_len=3.0, tol=0.8):
    """cut P along its axis where the axis BENDS > max_turn deg (at the vertices of the axis simplified to tol mm, so
    pixel wiggle is not a bend; pieces >= min_len): [(piece, (s0, s1) arc range along the axis)]"""
    L = line.length
    if L < 1.0: return [(P, (0.0, L))]
    sl = line.simplify(tol); cs = list(sl.coords); cuts = [0.0]
    for k in range(1, len(cs) - 1):
        t1 = math.degrees(math.atan2(cs[k][1] - cs[k - 1][1], cs[k][0] - cs[k - 1][0]))
        t2 = math.degrees(math.atan2(cs[k + 1][1] - cs[k][1], cs[k + 1][0] - cs[k][0]))
        s = line.project(Point(cs[k]))
        if abs(((t2 - t1) + 180) % 360 - 180) > max_turn and s - cuts[-1] >= min_len and L - s >= min_len: cuts.append(s)
    cuts.append(L)
    if len(cuts) == 2: return [(P, (0.0, L))]
    secs = sections(P, line, step=0.5)
    out = []
    for s0, s1 in zip(cuts, cuts[1:]):
        ss = [q for q in secs if s0 - 1e-6 <= q[0] <= s1 + 1e-6]
        quads = [Polygon([ss[k][1], ss[k][2], ss[k + 1][2], ss[k + 1][1]]).buffer(0) for k in range(len(ss) - 1)]
        g = unary_union([q for q in quads if not q.is_empty]).buffer(0.01).intersection(P) if quads else Polygon()
        out.append([g, (s0, s1)])
    taken = Polygon(); clean = []
    for g, ch in out:
        g = g.difference(taken).buffer(0); clean.append([g, ch]); taken = taken.union(g)
    rest = P.difference(taken).buffer(0)
    for piece in ([rest] if rest.geom_type == "Polygon" else list(getattr(rest, "geoms", []))):
        if piece.is_empty or piece.area < 0.05: continue
        j = min(range(len(clean)), key=lambda i: clean[i][0].distance(piece.representative_point()) if not clean[i][0].is_empty else 1e9)
        clean[j][0] = clean[j][0].union(piece).buffer(0)
    return [(g, ch) for g, ch in clean if not g.is_empty]


def limbs(ctx, C, min_limb_mm=2.0):
    """a branching bark component -> one mask per LIMB: the skeleton is cut at its junctions; SPURS are dropped (a
    branch shorter than min_limb_mm, or a free-ended branch shorter than 2.5 x the stroke's half-width where it leaves
    the junction: the medial axis forks into the corners at a stroke's square end); every pixel goes to the nearest
    remaining skeleton branch"""
    from skimage.morphology import skeletonize
    sk = skeletonize(C)
    if sk.sum() < 2: return [C]
    nb = ndi.convolve(sk.astype(int), np.ones((3, 3), int), mode="constant") - 1
    br = sk & ~((nb >= 3) & sk)
    lab, n = ndi.label(br, np.ones((3, 3), bool))
    if n <= 1: return [C]
    sz = np.bincount(lab.ravel(), minlength=n + 1)
    dt = ndi.distance_transform_edt(C)
    ends = sk & (nb == 1)
    free = np.bincount(lab[ends & (lab > 0)].ravel(), minlength=n + 1)
    dmax = ndi.maximum(dt, lab, index=np.arange(n + 1))
    keep = [i for i in range(1, n + 1) if sz[i] >= min_limb_mm * ctx.ev.ppm and not (free[i] and sz[i] < 2.5 * dmax[i])]
    if len(keep) <= 1: return [C]
    seed = np.where(np.isin(lab, keep), lab, 0)
    _, (iy, ix) = ndi.distance_transform_edt(seed == 0, return_indices=True)
    own = seed[iy, ix] * C
    return [own == i for i in keep if (own == i).any()]


def seg_axis(g, sub):
    """a segment's axis angle: the long side of its minimum rotated rectangle when it is a stroke (aspect >= 1.5; the
    traced medial axis of a square-ended stroke runs into its corners), else the axis polyline's mean direction"""
    from digitize.techniques import aspect_of
    gp = g if g.geom_type == "Polygon" else max(g.geoms, key=lambda q: q.area)
    if aspect_of(gp) >= 1.5:
        cs = list(gp.minimum_rotated_rectangle.exterior.coords)
        e = max(((cs[k], cs[k + 1]) for k in range(4)), key=lambda ab: math.dist(*ab))
        return line_angle(*e)
    return polyline_angle(list(sub.coords))


def chord_of(g, ang, L):
    """the axis chord of a strip: through its representative point, at the segment's axis angle, L mm long; None when
    it does not rebuild (construct rule "axis": on the part, a stroke)"""
    rp = g.representative_point(); ux, uy = math.cos(math.radians(ang)) * L / 2, math.sin(math.radians(ang)) * L / 2
    c = ((rp.x - ux, rp.y - uy), (rp.x + ux, rp.y + uy))
    probe = Part(id="_", kind="trunk_strip", geom=g, thread="", z=0, dir=DirSpec(0.0),
                 meta=dict(construct=dict(rule="axis", line=[list(c[0]), list(c[1])])))
    return c if cbasis(probe)[0] is not None else None


def split(ctx, zone, z, claim):
    ev = ctx.ev; sc = _cfg(ctx); rb = ctx.rb; ppm = ev.ppm; parts = []
    used = np.zeros_like(claim)
    if not claim.any(): return parts, used
    sup_idx = [ev.keys.index(k) for k in sc["support_tones"] if k in ev.keys]
    support = np.isin(ev.tone, sup_idx)
    m = ndi.binary_closing(claim, ctx.disk(0.5)) & (claim | ndi.binary_dilation(claim))
    lab, n = ndi.label(m)
    sizes = np.bincount(lab.ravel(), minlength=n + 1) / ppm ** 2
    ring_r = ctx.disk(2 * sc["support_ring_mm"])
    zb = rb.rule("branch").get("z_offset", 1.2)
    stats = dict(components=0, kept=0, limbs=0, no_support=0, blob=0, segments=0, strips=0, branches=0, no_chord=0)
    for ci in range(1, n + 1):
        if sizes[ci] < sc["min_mm2"]: continue
        C = lab == ci; stats["components"] += 1
        ring = ndi.binary_dilation(C, ring_r) & ~C
        if not ring.any() or support[ring].mean() < sc["support_frac"]: stats["no_support"] += 1; continue
        stats["kept"] += 1
        for li, Lm in enumerate(limbs(ctx, C, sc["min_limb_mm"])):
            gs = ev.polys(Lm, min_mm2=1.0, simplify=0.2)
            if not gs: continue
            P = max(gs, key=lambda q: q.area)
            if P.geom_type != "Polygon": P = max(P.geoms, key=lambda q: q.area)
            line = dst2.centreline(P)
            if line is None or line.length < 1.0: stats["blob"] += 1; continue
            line = LineString(line.simplify(0.8).coords)
            w = P.area / line.length
            if w < sc["min_w_mm"] or w > sc["max_w_mm"] or line.length < sc["min_aspect"] * w: stats["blob"] += 1; continue
            stats["limbs"] += 1; used |= Lm
            if line.length > 3 * w:                         # the axis' last half-width turns into the end's corners: trim it
                line = substring(line, w / 2, line.length - w / 2)
            if w <= sc["strip_split_mm"]:                     # a branch: ONE satin column across the stroke, along the limb
                cl = [list(map(float, q)) for q in line.coords]
                con = dict(rule="column", cl=cl)
                probe = Part(id="_", kind="branch", geom=P, thread="", z=0, dir=DirSpec(0.0, mode="contour", source="splitter"), meta=dict(construct=con))
                ang, why = cbasis(probe)
                if ang is None: stats["no_chord"] += 1; continue
                t = dominant(ctx, Lm) or dominant(ctx, C)
                parts.append(Part(id=ctx.new_id(zone["id"]), kind="branch", geom=P, thread=t, z=z + zb,
                                  dir=DirSpec(ang, mode="contour", source="splitter", note="satin column across the branch, along its centreline"),
                                  zone=zone["id"], rgb=ev.mean_rgb(Lm),
                                  meta=dict(splitter="trunk", tree=int(ci), limb=li, cl=cl, w=round(w, 2), construct=con)))
                stats["branches"] += 1
                continue
            for si, (g, (s0, s1)) in enumerate(segments(P, line, sc["max_turn_deg"], max(sc["min_seg_mm"], 1.5 * w))):
                stats["segments"] += 1; kind = "trunk_strip"
                sub = substring(line, s0, s1); L = max(sub.length, 1e-6); ws = g.area / L
                axis = seg_axis(g, sub)                                 # the segment's run (its long axis)
                k = int(math.ceil(ws / sc["strip_mm"])) if ws > sc["strip_split_mm"] else 1
                strips = cords(g, k, sub) if k > 1 else [g]
                got = []
                for j, sg in enumerate(strips):
                    if sg.is_empty or sg.area < 1.5: continue
                    c = chord_of(sg, axis, L)
                    if c is None: stats["no_chord"] += 1; continue
                    sm = ev.mask(sg); t = dominant(ctx, sm) or dominant(ctx, C)
                    if t is not None: got.append((j, sg, c, sm, t))
                alt = kind == "trunk_strip" and any(a[4] == b[4] for a, b in zip(got, got[1:]))
                for j, sg, c, sm, t in got:
                    con = dict(rule="axis", line=[list(map(float, c[0])), list(map(float, c[1]))])
                    meta = dict(splitter="trunk", tree=int(ci), limb=li, segment=si, strip=j, construct=con)
                    ang = line_angle(*c)
                    if alt:                                             # same-thread strips side by side: alternate +-10 (rule 3)
                        meta["band_offset_deg"] = sc["band_offset"] * (1 if j % 2 == 0 else -1); ang += meta["band_offset_deg"]
                    parts.append(Part(id=ctx.new_id(zone["id"]), kind=kind, geom=sg, thread=t, z=z + (zb if kind == "branch" else 0.0),
                                      dir=DirSpec(ang, source="splitter", note="split satin along the traced axis"),
                                      zone=zone["id"], rgb=ev.mean_rgb(sm), meta=meta))
                    stats["strips" if kind == "trunk_strip" else "branches"] += 1
    ctx.stats = getattr(ctx, "stats", {}); ctx.stats[zone["id"]] = stats
    return parts, used


def column_adherence(plan, segs, labels, crop, ppm=12.0, max_dev=15.0, min_len=0.6):
    """branch columns on the WRITTEN file: each visible stitch (>= min_len) of a part with a centreline (meta cl, mode
    contour) vs across the centreline at the stitch's nearest centreline point. -> dict(parts, stitches, within, pct_within)"""
    import qa
    from shapely.geometry import Point
    vis, idx = qa.visible_segments(segs, crop, ppm=ppm, return_index=True)
    cls = {p.id: LineString(p.meta["cl"]) for p in plan.parts if p.dir.mode == "contour" and p.meta.get("cl") and p.kind == "branch"}
    n = w = 0; seen = set()
    for s, i in zip(vis, idx):
        pid = labels[i]
        if pid not in cls: continue
        L = math.hypot(s[2] - s[0], s[3] - s[1])
        if L < min_len: continue
        ln = cls[pid]; t = ln.project(Point((s[0] + s[2]) / 2, (s[1] + s[3]) / 2))
        tan = math.degrees(dst2.tangent_at(ln, min(max(t, 0.05), max(ln.length - 0.05, 0.05))))
        a = math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])); d = abs((a - (tan + 90)) % 180); d = min(d, 180 - d)
        n += 1; w += d <= max_dev; seen.add(pid)
    return dict(parts=len(seen), stitches=n, within=int(w), pct_within=round(100.0 * w / max(1, n), 1))
