"""Tatami fill at the part's declared angle, staggered penetrations (each row's stitches offset by a third of a stitch
from the row before, dst2.tatami_rows), rows chained cell by cell around holes (LESSONS B23).
Underlay per StitchSpec.underlay: edge_run (0.6 mm inset) and lattice_90 (2 mm tatami at +90 deg, only above
lattice_min_mm2; DIGITIZING_PRINCIPLES rule 7). No underlay on shading / blend layers (their spec has underlay: [])."""
import math
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys, fits_width


def split_short(rows, min_row=0.6):
    """a tatami row shorter than one stitch is ONE stitch; a run of those, each reversing the last, sews (and reads
    back, qa.satin_runs) as a satin column, a blob on a small part. Every one-stitch row gets a staggered penetration
    (at 1/3, 1/2 or 2/3 along, by row) so it stays tatami; rows under min_row mm (slivers under pull comp) are dropped."""
    out = []
    for i, r in enumerate(rows):
        if len(r) == 2:
            a, b = r; d = math.dist(a, b)
            if d < min_row: continue
            f = (1 / 3, 1 / 2, 2 / 3)[i % 3]
            r = [a, (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), b]
        out.append(r)
    return out


@register
class Tatami(Technique):
    name = "tatami"; stype = "tatami"

    def check(self, part, principles):
        w = principles.get("fill_min_w_mm", 5.0)
        if not fits_width(part.geom, w):
            return [self.issue(part, f"fill narrower than {w} mm everywhere (rule 4: fill only where >= ~5 mm wide)", rule=4)]
        return []

    def plan(self, part):
        st = part.stitch; a = part.dir.angle; out = []
        for p in polys(part.geom):
            if p.area < 0.3: continue
            if "edge_run" in st.underlay:
                out += [Block(part.id, "underlay", b) for b in dst2.edge_run(p, 0.6)]
            if "lattice_90" in st.underlay and p.area > st.params.get("lattice_min_mm2", 60.0):
                q = p.buffer(-0.8)
                if not q.is_empty: out += [Block(part.id, "underlay", b) for b in dst2.join_rows(dst2.tatami_rows(q, a + 90, 2.0, 4.0))]
            top = p.buffer(st.pull_comp * 0.5) if st.pull_comp else p
            out += [Block(part.id, "top", b) for b in dst2.join_rows(split_short(dst2.tatami_rows(top, a, st.spacing, st.stitch_len)))]
        return [b for b in out if len(b.pts) > 1]
