"""Fall splitter (motif playbook: falls = 4-10 cords of split satin, alternating tones, vertical).

  1. silhouette: the zone's claimed water pixels, closed (1.5 mm) and hole-filled so the dark streaks between strands
     belong to the fall, opened (0.5 mm); components >= 50 mm2 (input pixels only, LESSONS A14).
  2. medial axis: dst2.centreline (skeleton longest path, extended to the outline), smoothed.
  3. cords: n = clip(round(median width / cord_mm), cords_min, cords_max) strips running along the axis, built from
     cross-sections every 1 mm (each cross-section cut into n equal pieces), so cords follow a curving or tapering fall.
     Leftover silhouette (ends, kinks) joins the nearest cord.
  4. tones: the fall's threads that cover >= 8 % of it (most first); each cord takes the one closest to its own mean
     colour, but never the same as the cord beside it (alternating tones).
Direction: the rulebook's fall_cord angle (90 deg: threads down the water)."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union
import dst2
from digitize.schema import Part
from digitize.extract.evidence import to_lab, delta_e


def silhouette(ctx, claim):
    m = ndi.binary_closing(claim, ctx.disk(1.5), iterations=1) | claim
    m = ndi.binary_fill_holes(m)
    m = ndi.binary_opening(m, ctx.disk(0.5))
    return m


def sections(P, line, step=1.0, R=80.0):
    """cross-sections of P perpendicular to `line` every step mm: [(s, a, b)] with a/b the left/right ends"""
    out = []; L = line.length
    for k in range(int(L / step) + 1):
        s = min(L, k * step); c = line.interpolate(s); th = dst2.tangent_at(line, s) + math.pi / 2
        seg = LineString([(c.x - R * math.cos(th), c.y - R * math.sin(th)), (c.x + R * math.cos(th), c.y + R * math.sin(th))]).intersection(P)
        segs = [seg] if seg.geom_type == "LineString" else [g for g in getattr(seg, "geoms", []) if g.geom_type == "LineString"]
        segs = [g for g in segs if g.length > 0.2]
        if not segs: continue
        g = min(segs, key=lambda g: g.distance(c)); a, b = g.coords[0], g.coords[-1]
        if out:                                                    # keep a = the same side as before
            pa, pb = out[-1][1], out[-1][2]
            if math.dist(a, pa) + math.dist(b, pb) > math.dist(b, pa) + math.dist(a, pb): a, b = b, a
        out.append((s, a, b))
    return out


def cords(P, n, line):
    secs = sections(P, line)
    if len(secs) < 2: return [P]
    pts = lambda a, b: [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]
    cut = [pts(a, b) for _, a, b in secs]
    out = []
    for i in range(n):
        quads = []
        for k in range(len(cut) - 1):
            q = Polygon([cut[k][i], cut[k][i + 1], cut[k + 1][i + 1], cut[k + 1][i]]).buffer(0)
            if not q.is_empty: quads.append(q)
        out.append(unary_union(quads).buffer(0.01).intersection(P).buffer(0) if quads else Polygon())
    # cords must not overlap each other: each keeps what earlier cords did not take
    taken = Polygon(); clean = []
    for g in out:
        g = g.difference(taken).buffer(0); clean.append(g); taken = taken.union(g)
    rest = P.difference(taken).buffer(0)
    for piece in ([rest] if rest.geom_type == "Polygon" else list(getattr(rest, "geoms", []))):
        if piece.is_empty or piece.area < 0.05: continue
        j = min(range(n), key=lambda i: clean[i].distance(piece.representative_point()) if not clean[i].is_empty else 1e9)
        clean[j] = clean[j].union(piece).buffer(0)
    return clean


def split(ctx, zone, z, claim):
    ev = ctx.ev; fc = ctx.cfg.get("fall", {}); sil = silhouette(ctx, claim); parts = []
    used = np.zeros_like(sil)
    for P in ev.polys(sil, min_mm2=50.0, simplify=0.2):
        if P.geom_type != "Polygon": P = max(P.geoms, key=lambda q: q.area)
        line = dst2.centreline(P)
        if line is None: continue
        line = LineString(line.simplify(1.5).coords)
        widths = [math.dist(a, b) for _, a, b in sections(P, line, step=2.0)]
        n = int(np.clip(round(np.median(widths) / fc.get("cord_mm", 5.0)), fc.get("cords_min", 4), fc.get("cords_max", 10)))
        pm = ev.mask(P) & sil; used |= pm
        v = ctx.thread_lab[pm]; v = v[v >= 0]; cnt = np.bincount(v, minlength=len(ctx.threads)) / max(len(v), 1)
        tones = [ctx.threads[i] for i in np.argsort(-cnt) if cnt[i] >= 0.08] or [ctx.threads[int(cnt.argmax())]]
        tlab = to_lab(np.array([[_rgb(ev.hex[ev.keys.index(t)]) for t in tones]], float))[0]
        prev = None
        for i, g in enumerate(cords(P, n, line)):
            if g.is_empty or g.area < 1.0: continue
            m = ev.mask(g); rgb = ev.mean_rgb(m) or (128, 128, 128)
            d = delta_e(to_lab(np.array([[rgb]], float))[0][0][None].repeat(len(tones), 0), tlab)
            rank = [tones[j] for j in np.argsort(d)]
            t = rank[0] if rank[0] != prev or len(rank) == 1 else rank[1]
            prev = t
            parts.append(Part(id=ctx.new_id(zone["id"]), kind="fall_cord", geom=g, thread=t, z=z, dir=ctx.rb.direction("fall_cord"),
                              zone=zone["id"], rgb=rgb, meta=dict(cord=i, cords=n, splitter="fall")))
    return parts, used


def _rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
