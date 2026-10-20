"""Stratum splitter (ENGINE_PLAN M2; motif playbook: cliffs / strata = one object per BEDDING BAND, guided tatami along
the bedding plane, +-15-25 deg between bands, cracks as run on top).

Per connected rock mass of the zone's claim (>= min_mass_mm2; smaller specks go back to the zones below):
  1. field: the reference grain over the mass (digitize.direction.Field from the evidence: structure tensor of the input
     pixels, smoothed, weak grain filled from a wider scale). The bedding plane = the grain.
  2. phase: phi over the mass with grad phi = the grain's normal (least squares), so phi measures distance ACROSS the
     bedding; a band is a phi interval, i.e. a strip that runs along the grain and follows it where it turns.
  3. bands: the dominant thread per 1 mm phi bin, mode-filtered; a band boundary sits where the dominant tone changes,
     bands thinner than min_band_mm merge into a neighbour, bands wider than max_band_mm split evenly.
  4. parts: each band x thread (tone components >= min_part_mm2 inside the band, smaller ones absorbed, protected
     accents kept from min_protected_mm2) is one stratum_band part: guided fill along the field, offset +band_offset_deg
     on even bands and -band_offset_deg on odd ones, so neighbouring bands differ by 2 x offset (20 deg) at the same grain.
  5. cracks: dark thin lines inside the mass (black top-hat of the evidence luminance over crack_mm, thin, >= crack_len_mm
     long) -> stratum_crack parts (a run along the traced line, sewn on top).
Geometry and tones come from the input pixels only (LESSONS A14); directions from the reference grain (evidence)."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import LineString
from shapely.ops import unary_union
import dst2
from digitize.schema import Part
from digitize.extract.splitters import partition
from digitize import direction as DR


def _cfg(ctx):
    d = dict(min_mass_mm2=40.0, min_band_mm=4.0, max_band_mm=16.0, bin_mm=1.0, min_part_mm2=30.0, crack_mm=1.6, crack_len_mm=8.0,
             crack_depth=35.0, max_cracks=4)
    d.update(ctx.cfg.get("stratum", {}) or {}); return d


def mass_phase(F, mask, ppm):
    """phi (mm across the bedding) on the evidence grid over mask, from the field's normals oriented to the mass mean"""
    a, _ = F.mean(mask)
    th = 0.5 * np.arctan2(F.s2, F.c2)
    nx_, ny_ = -np.sin(th), np.cos(th)
    m0 = math.radians(a); flip = (nx_ * -math.sin(m0) + ny_ * math.cos(m0)) < 0
    nx_ = np.where(flip, -nx_, nx_); ny_ = np.where(flip, -ny_, ny_)
    sl = ndi.find_objects(mask.astype(int))[0]
    sub = DR.solve_phase(nx_[sl], ny_[sl], mask[sl], 1.0 / ppm)
    phi = np.full(mask.shape, np.nan); phi[sl] = sub
    return phi, a


def bands_of(phi, lab, mask, bin_mm, min_band, max_band, n_threads):
    """[(lo, hi)] phi intervals: dominant thread per bin, mode-filtered over 3 bins, short runs merged, long runs split"""
    v = phi[mask]; t = lab[mask]; lo, hi = float(np.nanmin(v)), float(np.nanmax(v))
    nb = max(1, int(math.ceil((hi - lo) / bin_mm))); b = np.clip(((v - lo) / bin_mm).astype(int), 0, nb - 1)
    ok = t >= 0
    H = np.zeros((nb, n_threads)); np.add.at(H, (b[ok], t[ok]), 1)
    Hs = ndi.uniform_filter1d(H, 3, axis=0, mode="nearest")
    dom = Hs.argmax(1); dom[H.sum(1) == 0] = -1
    runs = []
    for i, d in enumerate(dom):
        if runs and runs[-1][2] == d: runs[-1][1] = i + 1
        else: runs.append([i, i + 1, d])
    mb = max(1, int(round(min_band / bin_mm)))
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for k, r in enumerate(runs):
            if r[1] - r[0] < mb:
                j = k - 1 if k > 0 else k + 1
                if k > 0 and k + 1 < len(runs) and (runs[k + 1][1] - runs[k + 1][0]) < (runs[k - 1][1] - runs[k - 1][0]): j = k + 1
                a, c = sorted((k, j)); runs[a] = [runs[a][0], runs[c][1], runs[j][2]]; del runs[c]; changed = True; break
    out = []
    for r0, r1, _ in runs:
        w = (r1 - r0) * bin_mm; n = max(1, int(math.ceil(w / max_band)))
        for i in range(n):
            out.append((lo + (r0 + (r1 - r0) * i / n) * bin_mm, lo + (r0 + (r1 - r0) * (i + 1) / n) * bin_mm))
    out[0] = (lo - 1.0, out[0][1]); out[-1] = (out[-1][0], hi + 1.0)
    return out


def cracks(ctx, mass, sc):
    """dark thin lines in the mass -> [(LineString, thread)]"""
    from skimage.morphology import skeletonize
    ev = ctx.ev; grey = ev.rgb @ np.array([0.299, 0.587, 0.114])
    th = ndi.black_tophat(grey, footprint=ctx.disk(sc["crack_mm"] * 2))          # darker than its surroundings
    m = (th > sc["crack_depth"]) & ndi.binary_erosion(mass, ctx.disk(1.0))
    m = m & ~ndi.binary_opening(m, ctx.disk(sc["crack_mm"]))                       # thin: what an opening removes
    sk = skeletonize(m); lab, n = ndi.label(sk, np.ones((3, 3), bool)); out = []
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    for i in np.argsort(-sizes[1:])[: sc["max_cracks"]] + 1:
        if sizes[i] / ev.ppm < sc["crack_len_mm"]: break
        comp = ndi.binary_dilation(lab == i, ctx.disk(0.6))
        gs = ev.polys(comp, min_mm2=0.5, simplify=0.1)
        if not gs: continue
        g = max(gs, key=lambda q: q.area)
        c = dst2.centreline(g) if g.geom_type == "Polygon" else None
        if c is None or c.length < sc["crack_len_mm"]: continue
        v = ctx.thread_lab[lab == i]; v = v[v >= 0]
        t = ctx.threads[int(np.bincount(v).argmax())] if len(v) else None
        out.append((LineString(c.simplify(0.3).coords), t))
    return out


def split(ctx, zone, z, claim):
    ev = ctx.ev; sc = _cfg(ctx); parts = []; used = np.zeros_like(claim)
    if not claim.any(): return parts, used
    F = ctx.field(); rb = ctx.rb; off = float(rb.rule("stratum_band").get("band_offset_deg", 10.0))
    zc = z + float(rb.rule("stratum_crack").get("z_offset", 0.6))
    lab, n = ndi.label(ndi.binary_closing(claim, ctx.disk(0.6)) | claim)       # a 0.6 mm gap does not split a mass
    lab = np.where(claim, lab, 0)
    sizes = np.bincount(lab.ravel(), minlength=n + 1) / ev.ppm ** 2
    lum = np.array([sum(c * w for c, w in zip(_rgb(ev.hex[ev.keys.index(t)]) if t in ev.keys else (128, 128, 128), (0.299, 0.587, 0.114)))
                    for t in ctx.threads])
    for mi in np.argsort(-sizes[1:]) + 1:
        if sizes[mi] < sc["min_mass_mm2"]: break
        mass = lab == mi; used |= mass
        phi, mean_a = mass_phase(F, mass, ev.ppm)
        bands = bands_of(phi, ctx.thread_lab, mass, sc["bin_mm"], sc["min_band_mm"], sc["max_band_mm"], len(ctx.threads))
        for k, (a, b) in enumerate(bands):
            bm = mass & (phi >= a) & (phi < b)
            if not bm.any(): continue
            sign = 1.0 if k % 2 == 0 else -1.0
            for thread, pm in partition(ctx, bm, sc["min_part_mm2"], ctx.cfg["stub"]["min_protected_mm2"]):
                gs = ev.polys(pm, min_mm2=0.5)
                if not gs: continue
                g = gs[0] if len(gs) == 1 else unary_union(gs)
                grid = F.grid(g, step=1.0); fm = DR.grid_mean(grid, g)
                if fm is None: raise ValueError(f"zone {zone['id']}: stratum part has no field (no evidence pixels)")
                d = rb.direction("stratum_band", field=fm)
                ang = (d.angle + sign * off) % 180.0
                from digitize.schema import DirSpec
                d = DirSpec(ang, mode=d.mode, source=d.source, note=f"grain mean {fm:.1f} {'+' if sign > 0 else '-'}{off:g} (band {k})")
                parts.append(Part(id=ctx.new_id(zone["id"]), kind="stratum_band", geom=g, thread=thread, z=z, dir=d, zone=zone["id"],
                                  rgb=ev.mean_rgb(pm), meta=dict(splitter="stratum", band=k, bands=len(bands), mass=int(mi), field=grid,
                                                                 field_mean=round(fm, 2), band_offset_deg=sign * off,
                                                                 coherence=round(F.mean(pm)[1], 3))))
        for line, t in cracks(ctx, mass, sc):
            if t is None: continue
            under = [p.thread for p in parts if p.meta.get("mass") == mi and p.geom.distance(line.interpolate(0.5, normalized=True)) < 0.5]
            if under and t == under[0]:                                         # a crack in its band's own colour: darkest zone thread
                t = min(set(p.thread for p in parts if p.meta.get("mass") == mi), key=lambda q: lum[ctx.threads.index(q)])
            ang = math.degrees(math.atan2(line.coords[-1][1] - line.coords[0][1], line.coords[-1][0] - line.coords[0][0])) % 180
            d = rb.direction("stratum_crack", outline=ang, technique=rb.technique_for("stratum_crack"))
            parts.append(Part(id=ctx.new_id(zone["id"]), kind="stratum_crack", geom=line.buffer(0.3), thread=t, z=zc, dir=d, zone=zone["id"],
                              meta=dict(splitter="stratum", mass=int(mi), line=[list(c) for c in line.coords], outline_angle=round(d.angle, 2))))
    return parts, used


def _rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
