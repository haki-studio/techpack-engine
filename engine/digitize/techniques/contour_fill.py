"""Contour fill (ENGINE_PLAN M2; motif playbook: clouds = one object per lobe, contour / turning fill): rows run
PARALLEL TO THE OUTLINE, as rings inset one spacing at a time (the outline, then the outline inset by 1 x spacing, ...),
sewn from the outside in, each ring entered at the point nearest the end of the last one so the hop is one spacing.
Stitches every stitch_len along each ring with the tatami brick stagger ((ring mod 3) / 3 of a stitch). A ring shorter
than one stitch gets a penetration (split_short). Direction mode "contour": the declared angle (the lobe's long axis,
source "outline") only labels the part; the rows are the outline's.
Underlay: edge run (rule 7) and, above lattice_min_mm2, a 90-degree lattice across the declared axis."""
import math
from shapely.geometry import LineString
from shapely.geometry.polygon import orient
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys, fits_width
from digitize.techniques.tatami import split_short
from digitize.techniques.guided_fill import stitch_row


def rings(p, spacing, min_len=0.6):
    """[(level, closed ring coords)] outside in; every polygon piece and hole of each inset, CCW exteriors"""
    out = []; k = 0
    while True:
        q = p.buffer(-(k + 0.5) * spacing, join_style="round")
        if q.is_empty: break
        for g in polys(q):
            g = orient(g)
            for r in [g.exterior] + list(g.interiors):
                if r.length >= min_len: out.append((k, list(r.coords)))
        k += 1
        if k > 400: break
    return out


def rotate_to(ring, pt):
    """closed ring re-started at its vertex nearest pt (the first and last point stay equal)"""
    cs = ring[:-1] if ring[0] == ring[-1] else ring
    i = min(range(len(cs)), key=lambda i: math.dist(cs[i], pt))
    cs = cs[i:] + cs[:i]
    return cs + [cs[0]]


@register
class ContourFill(Technique):
    name = "contour_fill"; stype = "tatami"

    def check(self, part, principles):
        w = principles.get("fill_min_w_mm", 5.0)
        if not fits_width(part.geom, w):
            return [self.issue(part, f"fill narrower than {w} mm everywhere (rule 4: fill only where >= ~5 mm wide)", rule=4)]
        return []

    def plan(self, part):
        st = part.stitch; out = []
        for p in polys(part.geom):
            if p.area < 0.3: continue
            if "edge_run" in st.underlay:
                out += [Block(part.id, "underlay", b) for b in dst2.edge_run(p, 0.6)]
            if "lattice_90" in st.underlay and p.area > st.params.get("lattice_min_mm2", 60.0):
                q = p.buffer(-0.8)
                if not q.is_empty: out += [Block(part.id, "underlay", b) for b in dst2.join_rows(dst2.tatami_rows(q, part.dir.angle + 90, 2.0, 4.0))]
            top = p.buffer(st.pull_comp * 0.5) if st.pull_comp else p
            pos = None; cur = []
            for k, ring in rings(top, st.spacing):
                if pos is not None: ring = rotate_to(ring, pos)
                rr = split_short([stitch_row(ring, k, st.stitch_len)]) if len(ring) > 1 else []
                if not rr: continue                                    # a ring under 0.6 mm: dropped
                r = rr[0]
                if cur and math.dist(cur[-1], r[0]) > 1.2:
                    out.append(Block(part.id, "top", cur)); cur = []
                cur += [q for q in r if not cur or q != cur[-1]]; pos = cur[-1]
            if len(cur) > 1: out.append(Block(part.id, "top", cur))
        return [b for b in out if len(b.pts) > 1]
