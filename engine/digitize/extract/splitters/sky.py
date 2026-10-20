"""Sky splitter (motif playbook: sky = horizontal tatami bands with blends, 0 deg, sewn under the clouds, cut away).

Per window of the zone: every evidence row inside the window votes for its dominant sky thread (claimed pixels only);
runs of rows with the same vote become BANDS, runs thinner than min_band_mm merge into the band above (or below at the
top). A band covers its whole window across (the sky sews behind everything in it; sequence.cut_under then removes what
the parts above cover, keeping 1 mm). Between two bands a sky_blend part carries the upper thread blend_mm into the
lower band at half density with no underlay (rule 8: gradients from density; rule 7: no underlay on shading)."""
import numpy as np
from shapely.geometry import box
from digitize.schema import Part


def bands_of(votes, min_rows):
    """votes: per row thread or None -> [(r0, r1, thread)] (r1 exclusive), short runs merged into a neighbour"""
    v = list(votes)
    for i in range(len(v)):                       # fill gaps from the row above, then below
        if v[i] is None and i: v[i] = v[i - 1]
    for i in range(len(v) - 2, -1, -1):
        if v[i] is None: v[i] = v[i + 1]
    runs = []
    for i, t in enumerate(v):
        if t is None: continue
        if runs and runs[-1][2] == t and runs[-1][1] == i: runs[-1][1] = i + 1
        else: runs.append([i, i + 1, t])
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for k, r in enumerate(runs):
            if r[1] - r[0] < min_rows:
                j = k - 1 if k > 0 else k + 1
                a, b = sorted((k, j)); runs[a] = [runs[a][0], runs[b][1], runs[j][2]]; del runs[b]; changed = True; break
        merged = []
        for r in runs:
            if merged and merged[-1][2] == r[2]: merged[-1][1] = r[1]
            else: merged.append(r)
        runs = merged
    return [tuple(r) for r in runs]


def split(ctx, zone, z, claim):
    ev = ctx.ev; sc = ctx.cfg.get("sky", {}); parts = []; zb = ctx.rb.z("sky_blend")
    min_rows = max(1, int(round(sc.get("min_band_mm", 3.0) * ev.ppm))); bl = sc.get("blend_mm", 2.5)
    for w in zone["geoms"]:
        wm = ev.mask(w) & claim
        if not wm.any(): continue
        rows = np.nonzero(wm.any(axis=1))[0]; r0, r1 = rows.min(), rows.max() + 1
        votes = []
        for r in range(r0, r1):
            v = ctx.thread_lab[r][wm[r]]; v = v[v >= 0]
            votes.append(ctx.threads[int(np.bincount(v).argmax())] if len(v) >= 2 else None)
        bands = bands_of(votes, min_rows)
        x0, _, x1, _ = w.bounds
        for k, (a, b, t) in enumerate(bands):
            ya, yb = ev.to_mm(0, r0 + a)[1], ev.to_mm(0, r0 + b)[1]
            if k == 0: ya = w.bounds[1]
            if k == len(bands) - 1: yb = w.bounds[3]
            g = w.intersection(box(x0 - 1, ya, x1 + 1, yb)).buffer(0)
            if g.is_empty: continue
            m = ev.mask(g)
            parts.append(Part(id=ctx.new_id(zone["id"]), kind="sky_band", geom=g, thread=t, z=z, dir=ctx.rb.direction("sky_band"),
                              zone=zone["id"], rgb=ev.mean_rgb(m & claim) or ev.mean_rgb(m), meta=dict(band=k, splitter="sky")))
            if k + 1 < len(bands) and bl > 0:
                gb = w.intersection(box(x0 - 1, yb, x1 + 1, yb + bl)).buffer(0)
                if not gb.is_empty:
                    parts.append(Part(id=ctx.new_id(zone["id"]), kind="sky_blend", geom=gb, thread=t, z=z + (zb - ctx.rb.z("sky_band")),
                                      dir=ctx.rb.direction("sky_blend"), zone=zone["id"], rgb=None,
                                      meta=dict(blend=f"{t} into {bands[k + 1][2]}", splitter="sky", blend_from=[[x0 - 1, yb], [x1 + 1, yb]])))
    return parts, claim
