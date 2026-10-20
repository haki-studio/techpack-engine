"""Lily splitter (engine trial on Koi Blossom, tag KOI, 2026-10-20). A face-on lily-like flower = a FAN of long petals
around a heart. Koi Rev B sewed them as radial streak fans and pale templates (REVIEW_OPEN items 2-3); here every petal is
traced from the input pixels and sewn as long rows ALONG that petal.

  1. mass: the zone's claimed flower pixels (blues + the pale petal tones + stamens), closed close_mm, hole-filled; the
     largest component (>= min_mass_mm2). Input pixels only (LESSONS A14).
  2. heart: the zone's `heart` window (hand-drawn, like every zone window: it says WHERE the heart is, never its shape);
     the centre = the centroid of the heart-tone pixels (stamens: heart_tones) of the mass inside it, else of the mass
     inside it. A heart window with no mass raises (a direction is never defaulted, rule 2).
  3. petals: the mass in polar coordinates about the centre. R(theta) = the reach of the mass per bin_deg bin (the
     reach_q quantile of the radii), circularly smoothed (smooth_deg); each local maximum >= min_prom x max(R) apart
     from its neighbouring minima by min_sep_deg is a petal TIP; the sector between two consecutive minima is that petal.
  4. tones: each petal's pixels are partitioned by thread (splitters.partition: pieces under min_piece_mm2 absorbed into
     the neighbour with the longest border). Every piece of a petal gets ONE angle, the petal's ray heart -> tip
     (construct rule "ray", rebuilt by digitize.audit; a piece more than 3 mm off its petal's ray fails the rule and
     merges into the petal's largest piece; pieces of one thread in one petal are one part). Darker pieces sew first (lower z), lighter on top: the long-and-short shading
     of the close-up as abutting tone pieces, no streaks.
  5. kind `lily_petal`, tatami along the petal (house.yaml). Rule 3 between petals: neighbouring petals of one flower
     differ by their own fan angle; same-thread neighbours closer than 15 deg are turned by DR.separate (separate_kinds).
meta: splitter "lily", flower, petal, heart, tip, construct; M4g hint group = the flower."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Polygon
from shapely.ops import unary_union
from digitize.schema import Part, DirSpec
from digitize.extract.splitters import partition
from digitize.extract.splitters.construct import basis as cbasis, line_angle

DEFAULTS = dict(heart_tones=["kb_white", "kb_lav", "kb_ice"], min_mass_mm2=30.0, close_mm=1.0, bin_deg=2.0, smooth_deg=8.0,
                reach_q=0.97, min_prom=0.18, min_sep_deg=18.0, min_piece_mm2=4.0, tone_z=0.01)


def _cfg(ctx):
    d = dict(DEFAULTS); d.update(ctx.cfg.get("lily", {}) or {}); return d


def lum_hex(h):
    h = h.lstrip("#"); r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4)); return 0.299 * r + 0.587 * g + 0.114 * b


def petal_sectors(theta, r, bin_deg=2.0, smooth_deg=8.0, reach_q=0.97, min_prom=0.18, min_sep_deg=18.0):
    """the petal fan of a mass seen from its heart: theta (deg, 0..360) and r (mm) of its pixels -> (sector index per
    pixel (-1 = none), [tip angle deg per petal], R profile). Tips = local maxima of the smoothed reach R(theta) that rise
    >= min_prom x max(R) above the minima on both sides; sectors run from minimum to minimum."""
    nb = int(round(360.0 / bin_deg)); b = (theta / bin_deg).astype(int) % nb
    R = np.zeros(nb)
    for k in range(nb):
        rk = r[b == k]
        if len(rk): R[k] = np.quantile(rk, reach_q)
    s = max(1.0, smooth_deg / bin_deg)
    Rs = ndi.gaussian_filter1d(R, s, mode="wrap")
    if Rs.max() <= 0: return np.full(len(theta), -1), [], Rs
    peaks = [k for k in range(nb) if Rs[k] >= Rs[k - 1] and Rs[k] > Rs[(k + 1) % nb]]
    mins = [k for k in range(nb) if Rs[k] <= Rs[k - 1] and Rs[k] < Rs[(k + 1) % nb]]
    if not mins:                                            # one round blob: a single "petal" all the way round
        return np.zeros(len(theta), int), [float(np.argmax(Rs) * bin_deg)], Rs
    sep = int(round(min_sep_deg / bin_deg)); thr = min_prom * Rs.max()
    changed = True
    while changed and len(mins) > 1:                        # merge sectors whose peak does not stand out (or is too narrow)
        changed = False
        for i in range(len(mins)):
            a, c = mins[i], mins[(i + 1) % len(mins)]
            span = (c - a) % nb or nb
            idx = [(a + j) % nb for j in range(span + 1)]
            top = max(Rs[j] for j in idx)
            if top - max(Rs[a], Rs[c]) < thr or span < sep:
                drop = a if Rs[a] > Rs[c] else c          # remove the HIGHER of the two bounding minima: the sector joins its neighbour
                mins.remove(drop); changed = True; break
    mins = sorted(mins); tips = []; sec = np.full(nb, -1)
    for i in range(len(mins)):
        a, c = mins[i], mins[(i + 1) % len(mins)] if len(mins) > 1 else mins[i] + nb
        span = (c - a) % nb or nb
        idx = [(a + j) % nb for j in range(span)]
        for j in idx: sec[j] = i
        tips.append(float(max(idx, key=lambda j: Rs[j]) * bin_deg))
    return sec[b], tips, Rs


def split(ctx, zone, z, claim):
    ev = ctx.ev; sc = _cfg(ctx); ppm = ev.ppm; parts = []
    used = np.zeros_like(claim)
    if not claim.any(): return parts, used
    if not zone.get("heart"): raise ValueError(f"zone {zone['id']}: a lily zone needs a `heart` window (where the flower's heart is)")
    m = ndi.binary_fill_holes(ndi.binary_closing(claim, ctx.disk(sc["close_mm"])) | claim)
    lab, n = ndi.label(m)
    if n == 0: return parts, used
    sizes = np.bincount(lab.ravel(), minlength=n + 1); sizes[0] = 0
    M = lab == int(sizes.argmax())
    if sizes.max() / ppm ** 2 < sc["min_mass_mm2"]: return parts, used
    used |= M
    hw = ev.mask(Polygon(zone["heart"])) & M
    if not hw.any(): raise ValueError(f"zone {zone['id']}: the heart window holds no flower pixels, so the petal fan has no centre")
    ht = np.isin(ev.tone, [ev.keys.index(k) for k in sc["heart_tones"] if k in ev.keys]) & hw
    src = ht if ht.sum() >= 2 * ppm ** 2 else hw
    yy, xx = np.nonzero(src); cx, cy = ev.to_mm(xx.mean() + 0.5, yy.mean() + 0.5)
    ys, xs = np.nonzero(M); px, py = ev.to_mm(xs + 0.5, ys + 0.5)
    th = np.degrees(np.arctan2(py - cy, px - cx)) % 360.0; r = np.hypot(px - cx, py - cy)
    sec, tips, _ = petal_sectors(th, r, sc["bin_deg"], sc["smooth_deg"], sc["reach_q"], sc["min_prom"], sc["min_sep_deg"])
    stats = dict(petals=len(tips), pieces=0, merged_off_ray=0, heart_from=("stamens" if src is ht else "window"), centre=[round(cx, 2), round(cy, 2)])
    lums = {t: lum_hex(ctx.cfg["threads"]["palette"][t]) if t in ctx.cfg["threads"]["palette"] else 0.0 for t in ctx.threads}
    for i, ta in enumerate(tips):
        P = np.zeros_like(M); sel = sec == i; P[ys[sel], xs[sel]] = True
        if P.sum() < sc["min_piece_mm2"] * ppm ** 2: continue
        pr = r[sel]; pt = np.argmax(pr); tip = (float(px[sel][pt]), float(py[sel][pt]))
        heart = (float(cx), float(cy)); ang = line_angle(heart, tip)
        con = dict(rule="ray", **{"from": [heart[0], heart[1]], "to": [tip[0], tip[1]]})
        pieces = []
        for thread, pm in partition(ctx, P, sc["min_piece_mm2"], sc["min_piece_mm2"]):
            gs = ev.polys(pm, min_mm2=0.5)
            if not gs: continue
            g = gs[0] if len(gs) == 1 else unary_union(gs)
            pieces.append([thread, g, pm])
        if not pieces: continue
        pieces.sort(key=lambda q: -q[1].area)
        keep = []
        for q in pieces:                                   # a piece off its petal's ray belongs to the petal's largest piece
            probe = Part(id="_", kind="lily_petal", geom=q[1], thread="", z=0, dir=DirSpec(0.0, source="splitter"), meta=dict(construct=con))
            if keep and cbasis(probe)[0] is None:
                keep[0][1] = keep[0][1].union(q[1]).buffer(0); keep[0][2] = keep[0][2] | q[2]; stats["merged_off_ray"] += 1
            else: keep.append(q)
        byt = {}                                           # one part per thread per petal (rule 3: no same-thread twins at one angle)
        for thread, g, pm in keep:
            if thread in byt: byt[thread] = [thread, byt[thread][1].union(g).buffer(0), byt[thread][2] | pm]
            else: byt[thread] = [thread, g, pm]
        keep = list(byt.values())
        for thread, g, pm in sorted(keep, key=lambda q: lums.get(q[0], 0.0)):    # dark first, light on top
            rank = sorted(lums.get(q[0], 0.0) for q in keep).index(lums.get(thread, 0.0))
            parts.append(Part(id=ctx.new_id(zone["id"]), kind="lily_petal", geom=g, thread=thread, z=z + sc["tone_z"] * rank,
                              dir=DirSpec(ang, source="splitter", note="along the petal, heart -> tip (one angle per petal)"),
                              zone=zone["id"], rgb=ev.mean_rgb(pm),
                              meta=dict(splitter="lily", flower=zone["id"], petal=i, heart=list(heart), tip=list(tip), construct=con,
                                        group=f"{zone['id']}.flower")))
            stats["pieces"] += 1
    ctx.stats = getattr(ctx, "stats", {}); ctx.stats[zone["id"]] = stats
    return parts, used
