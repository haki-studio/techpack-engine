"""cord: falls, trunks, vines, bodies lengthwise - a long mass sewn as split-satin strips ALONG its medial axis.

  1. silhouette of the claim (close close_mm, holes filled, open open_mm: dark streaks between strands belong to it);
     components >= min_mass_mm2 (input pixels only, A14).
  2. medial axis (dst2.centreline), cut where it bends > max_turn_deg (trunk.segments), so each piece has ONE axis.
  3. n = clip(round(median width / cord_mm), cords_min, cords_max) strips per piece along the axis (fall.cords: cross-
     sections every 1 mm cut into n equal pieces, so cords follow a curving or tapering mass).
  4. tones: the piece's threads covering >= tone_share (most first); each cord takes the one closest to its own mean
     colour, never the same as the cord beside it (alternating tones). colour: <key> forces one thread.
Direction: ALONG each cord, construct rule "axis" on the cord's own long mid-line (independent: where the mass runs).
params: cord_mm 5, cords_min 1, cords_max 10, close_mm 1.5, open_mm 0.5, min_mass_mm2 20, max_turn_deg 25, tone_share 0.08."""
import math
import numpy as np
from shapely.geometry import LineString
from shapely.ops import substring
import dst2
from digitize.primitives import register, part, forced_thread, silhouette, axis_chord
from digitize.schema import DirSpec
from digitize.extract.evidence import to_lab, delta_e

D = dict(cord_mm=5.0, cords_min=1, cords_max=10, close_mm=1.5, open_mm=0.5, min_mass_mm2=20.0, max_turn_deg=25.0, tone_share=0.08)


def _rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@register("cord")
def recognise(ctx, lp, z, claim):
    from digitize.extract.splitters.fall import sections, cords
    from digitize.extract.splitters.trunk import segments
    P = dict(D); P.update(lp.get("params") or {})
    ev = ctx.ev; parts = []; used = np.zeros_like(claim)
    if not claim.any(): return parts, used
    sil = silhouette(ctx, claim, P["close_mm"], P["open_mm"]); ft = forced_thread(ctx, lp)
    for G in ev.polys(sil, min_mm2=P["min_mass_mm2"], simplify=0.2):
        Gp = G if G.geom_type == "Polygon" else max(G.geoms, key=lambda q: q.area)
        line = dst2.centreline(Gp)
        if line is None: continue
        line = LineString(line.simplify(1.5).coords)
        pm = ev.mask(G) & sil; used |= pm
        v = ctx.thread_lab[pm]; v = v[v >= 0]
        if not len(v): continue
        cnt = np.bincount(v, minlength=len(ctx.threads)) / len(v)
        tones = [ft] if ft else ([ctx.threads[i] for i in np.argsort(-cnt) if cnt[i] >= P["tone_share"]] or [ctx.threads[int(cnt.argmax())]])
        tlab = to_lab(np.array([[_rgb(ev.hex[ev.keys.index(t)]) if t in ev.keys else (128, 128, 128) for t in tones]], float))[0]
        k_cord = 0
        w = Gp.area / max(line.length, 1e-6)
        if line.length > 3 * w: line = substring(line, w / 2, line.length - w / 2)   # the axis' last half-width runs into the corners
        for si, (seg, (s0, s1)) in enumerate(segments(Gp, line, P["max_turn_deg"], max(3.0, 2.0 * w))):
            sl = substring(line, s0, s1)
            if sl.length < 1.0: continue
            widths = [math.dist(a, b) for _, a, b in sections(seg, sl, step=2.0)] or [seg.area / max(sl.length, 1e-6)]
            n = int(np.clip(round(np.median(widths) / P["cord_mm"]), P["cords_min"], P["cords_max"]))
            prev = None
            pieces = [g for g in (cords(seg, n, sl) if n > 1 else [seg]) if not g.is_empty and g.area >= 0.05]
            pieces = _join_stubs(pieces)
            for i, g in enumerate(pieces):
                if g.area < 1.0: continue
                cl, ang = axis_chord(g)
                if cl is None:                     # still not a strip after joining (a short blob segment): sewn as one
                    from digitize.primitives import long_axis_dir
                    d0, extra = long_axis_dir(g, "a short cord piece: along its own long axis (outline)")
                    m = ev.mask(g); t = prev if prev else tones[0]
                    parts.append(part(ctx, lp, "cord", g, t, z, d0, m, cord=k_cord, segment=si, cords=n, **extra)); k_cord += 1
                    continue
                m = ev.mask(g); rgb = ev.mean_rgb(m) or (128, 128, 128)
                d_ = delta_e(to_lab(np.array([[rgb]], float))[0][0][None].repeat(len(tones), 0), tlab)
                rank = [tones[j] for j in np.argsort(d_)]
                t = rank[0] if rank[0] != prev or len(rank) == 1 else rank[1]; prev = t
                parts.append(part(ctx, lp, "cord", g, t, z, DirSpec(ang, source="splitter", note="split satin along the cord"), m,
                                  cord=k_cord, segment=si, cords=n, construct=dict(rule="axis", line=cl)))
                k_cord += 1
    return parts, used


def _join_stubs(pieces):
    """cords that are not strips (no axis chord) join the touching cord they share most border with"""
    from shapely.ops import unary_union
    out = list(pieces)
    changed = True
    while changed and len(out) > 1:
        changed = False
        for i, g in enumerate(out):
            if axis_chord(g)[0] is not None: continue
            best, bl = None, 0.0
            for j, h in enumerate(out):
                if j == i: continue
                L = g.buffer(0.05).intersection(h.buffer(0.05)).area
                if L > bl: best, bl = j, L
            if best is None: continue
            out[best] = unary_union([out[best], g]).buffer(0); del out[i]; changed = True; break
    return out
