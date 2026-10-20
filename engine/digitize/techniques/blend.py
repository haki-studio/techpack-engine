"""Blend (ENGINE_PLAN M2; DIGITIZING_PRINCIPLES rule 8: gradients from density, not threads; rule 7: no underlay on
shading layers). One OPEN layer of rows at the part's declared angle, sewn on top of the fill below it:

  mode "feather"  two-colour density blend (accordion): rows start on the SOURCE side (part.meta["blend_from"], a line:
                  the edge of the band whose colour this is) and reach a fraction of the way across, longer and shorter
                  in a fixed low-discrepancy order (golden-ratio sequence, never random), so the colour thins out into
                  the tone below. Consecutive rows are joined tip to tip / source to source (accordion zig-zag).
  mode "open"     an open shading layer: full rows at an open spacing (StitchSpec.spacing, e.g. 1.0-1.5 mm), ordered
                  cell by cell (dst2.chain_rows) and joined only across short hops, like tatami.
Rows get the tatami brick stagger and a penetration when shorter than a stitch (split_short); every stitch <= 7 mm.
check() flags any underlay (a shading layer has none) and a feather without a source line."""
import math
from shapely.geometry import LineString, Point
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys
from digitize.techniques.tatami import split_short
from digitize.techniques.guided_fill import stitch_row

GOLD = 0.6180339887498949


def reach(k, lo=0.15, power=1.6):
    """fraction of row k that the feather covers: lo..1, low-discrepancy (rows k, k+1, ... never repeat a pattern)"""
    return lo + (1 - lo) * (((k + 1) * GOLD) % 1.0) ** power


@register
class Blend(Technique):
    name = "blend"; stype = "run"; sequencing = {"open_layer": True}    # an open layer does not hide travel

    def check(self, part, principles):
        out = []
        if part.stitch and part.stitch.underlay:
            out.append(self.issue(part, f"blend / shading layer with underlay {part.stitch.underlay} (rule 7: no underlay on shading layers)", rule=7))
        mode = (part.stitch.params.get("mode") if part.stitch else None) or "feather"
        if mode == "feather" and not part.meta.get("blend_from"):
            out.append(self.issue(part, "feather blend without meta['blend_from'] (its source edge): sewn as an open layer", rule=8))
        return out

    def plan(self, part):
        st = part.stitch; P = st.params; mode = P.get("mode", "feather"); out = []
        src = LineString(part.meta["blend_from"]) if part.meta.get("blend_from") else None
        if mode == "feather" and src is None: mode = "open"
        lo = float(P.get("reach_min", 0.15)); pw = float(P.get("reach_power", 1.6))
        for p in polys(part.geom):
            if p.area < 0.3: continue
            if mode == "open":                                         # open layer: tatami rows, cell by cell, short hops only
                rows = split_short([stitch_row([a, b], k, st.stitch_len) for a, b, k in dst2.chain_rows(dst2.SR.hatch(p, part.dir.angle, st.spacing), p, part.dir.angle, st.spacing)])
                out += [Block(part.id, "top", b) for b in dst2.join_rows(rows)]
                continue
            segs = dst2.SR.hatch(p, part.dir.angle, st.spacing)
            rows = []
            for k, s in enumerate(segs):
                cs = list(s.coords)
                if len(cs) < 2: continue
                a, b = cs[0], cs[-1]
                if src is not None and Point(b).distance(src) < Point(a).distance(src): a, b = b, a
                if mode == "feather":
                    f = reach(k, lo, pw); b = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                if math.dist(a, b) < 0.3: continue
                rows.append((k, a, b))
            pts = []
            for i, (k, a, b) in enumerate(rows):
                seg = [a, b] if i % 2 == 0 else [b, a]                 # accordion: source -> tip, tip -> source
                rr = split_short([stitch_row(seg, k, st.stitch_len)])
                if not rr: continue                                    # a row under 0.6 mm: below pull comp, dropped
                r = rr[0]
                if pts and math.dist(pts[-1], r[0]) > 1.2 and not LineString([pts[-1], r[0]]).within(p.buffer(0.3)):
                    out.append(Block(part.id, "top", pts)); pts = []           # a link would leave the part: new block
                if pts and math.dist(pts[-1], r[0]) > 1e-6:            # tip-to-tip / source-to-source link, <= 7 mm stitches
                    pts += dst2.path_resample([pts[-1], r[0]], min(st.stitch_len, 6.5))[1:-1]
                pts += [q for q in r if not pts or q != pts[-1]]
            if len(pts) > 1: out.append(Block(part.id, "top", pts))
        return [b for b in out if len(b.pts) > 1]
