"""Run: single running stitch along the part's line (part.meta["line"], else its centreline, else its outline).
For parts under 1 mm wide (rule 4) and outlines. No underlay."""
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys, width_of


def line_of(part, p):
    ln = part.meta.get("line")
    if ln: return [tuple(c) for c in ln]
    if p.area > 0 and width_of(p) * 4 < p.length / 2:
        c = dst2.centreline(p)
        if c is not None: return list(c.coords)
    return list(p.exterior.coords)


def lines(part):
    if part.meta.get("line"): return [line_of(part, None)]
    return [line_of(part, p) for p in polys(part.geom)]


@register
class Run(Technique):
    name = "run"; stype = "run"; sequencing = {"after_fill": True}

    def check(self, part, principles):
        w = principles.get("run_max_w_mm", 1.0)
        if part.geom.area > 0 and width_of(part.geom) > 2 * w:
            return [self.issue(part, f"run on a part {width_of(part.geom):.1f} mm wide (rule 4: run below {w} mm)", rule=4)]
        return []

    def plan(self, part):
        return [Block(part.id, "top", dst2.path_resample(l, part.stitch.stitch_len)) for l in lines(part) if len(l) >= 2]
