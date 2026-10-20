"""Satin COLUMN: a centreline + a width, every stitch perpendicular to the smoothed centreline, alternating sides
(promoted column.py, from konpeito kjsatin). For stroke-like parts 1-7 mm wide (rule 4, aspect >= 2.5, LESSONS A16):
check() flags anything else so it is asked about, never sewn as a blob. Rows wider than 7 mm are split with the
split_satin stagger (no random jitter). Underlay: centre run from 2 mm, + edge run above edge_run_min_w (rule 7).
Centreline: part.meta["cl"] when the splitter gives one, else the part's skeleton (dst2.centreline)."""
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys, aspect_of
from digitize.techniques.split_satin import column_rows
from digitize.techniques import column as C


def _cl_w(part, p):
    cl = part.meta.get("cl")
    if cl is None:
        line = dst2.centreline(p)
        if line is None: return None, None
        cl = list(line.coords)
    w = part.meta.get("w") or (p.area / max(C.poly_len(cl), 1e-6))
    return [tuple(c) for c in cl], float(w)


@register
class Satin(Technique):
    name = "satin"; stype = "satin"

    def check(self, part, principles):
        out = []; lo, hi = principles.get("satin_min_w_mm", 1.0), principles.get("satin_max_w_mm", 7.0)
        for p in polys(part.geom):
            cl, w = _cl_w(part, p)
            if cl is None: out.append(self.issue(part, "no centreline: not a stroke", rule=4)); continue
            asp = C.poly_len(cl) / max(w, 1e-6)
            if w < lo: out.append(self.issue(part, f"satin {w:.2f} mm wide < {lo} mm: run / bean (rule 4)", rule=4))
            if w > hi: out.append(self.issue(part, f"satin {w:.2f} mm wide > {hi} mm: split satin (rule 4)", rule=4))
            if min(asp, aspect_of(p)) < principles.get("satin_min_aspect", 2.5) and p.area > 2.5:
                out.append(self.issue(part, f"satin on a blob (aspect {asp:.1f} < 2.5, LESSONS A16)", rule=4))
        return out

    def plan(self, part):
        st = part.stitch; out = []
        for p in polys(part.geom):
            cl, w = _cl_w(part, p)
            if cl is None: continue
            if w > st.params.get("edge_run_min_w", 4.0) and "centre_run" in st.underlay:
                out += [Block(part.id, "underlay", b) for b in dst2.edge_run(p, 0.5)]
            if w >= 2.0 and "centre_run" in st.underlay:
                out.append(Block(part.id, "underlay", dst2.path_resample(cl, 2.0)))
            out.append(Block(part.id, "top", column_rows(cl, w, st.spacing, st.pull_comp)))
        return [b for b in out if len(b.pts) > 1]
