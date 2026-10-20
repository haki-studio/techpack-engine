"""Turning satin along a declared axis (ENGINE_PLAN M5; konpeito petals / candy lobes, kjcore "tl" builder): one satin
per petal, every stitch perpendicular to the petal's axis (part.meta["axis"] = [centre, tip], a polyline), so the
lobe reads domed and radiating from the flower / candy centre. dst2.turning_satin does the rows (it skips an empty
perpendicular instead of crashing: konpeito ENGINE_NOTES 2). The part's DirSpec is the stitch angle at the axis start
(across the axis), declared by the extractor. A part with no usable axis (< 0.4 mm inside it) falls back to a fixed
satin at that declared angle, never "auto". Underlay: centre run on the axis when the part is >= 1.4 mm wide and the
axis > 2.5 mm (rule 7)."""
from shapely.geometry import LineString
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys, width_of


def long_axis(p):
    """the long mid-line of the part's minimum rotated rectangle (a default axis when none is declared)"""
    import math
    cs = list(p.minimum_rotated_rectangle.exterior.coords)
    e = [(math.dist(cs[i], cs[i + 1]), i) for i in range(4)]
    _, i = max(e); c = lambda k: cs[k % 4]
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return [mid(c(i + 3), c(i)), mid(c(i + 1), c(i + 2))]          # through the middles of the two short edges


@register
class Turning(Technique):
    name = "turning_satin"; stype = "satin"

    def check(self, part, principles):
        out = []; hi = principles.get("satin_max_w_mm", 7.0)
        if not part.meta.get("axis"): out.append(self.issue(part, "turning satin without an axis (part.meta axis)", rule=4))
        w = width_of(part.geom)
        if w > hi: out.append(self.issue(part, f"turning satin {w:.1f} mm wide > {hi} mm (rule 4)", rule=4))
        return out

    def plan(self, part):
        st = part.stitch; out = []
        for p in polys(part.geom):
            if p.area < 0.06: continue
            ax = part.meta.get("axis") or long_axis(p)
            ln = LineString(ax).intersection(p.buffer(0.6))
            ln = max(getattr(ln, "geoms", [ln]), key=lambda g: g.length) if not ln.is_empty else None
            if ln is None or ln.geom_type != "LineString" or ln.length < 0.4:
                out.append(Block(part.id, "top", dst2.fixed_satin(p, part.dir.angle, sp=st.spacing, pull=st.pull_comp))); continue
            if "centre_run" in st.underlay and width_of(p) >= 1.4 and ln.length > 2.5:
                inner = ln.intersection(p.buffer(-0.3))          # the run stays INSIDE the petal (the axis overshoots the tip)
                inner = max(getattr(inner, "geoms", [inner]), key=lambda g: g.length) if not inner.is_empty else None
                if inner is not None and inner.geom_type == "LineString" and inner.length > 1.0:
                    out.append(Block(part.id, "underlay", dst2.path_resample(list(inner.coords), 2.0)))
            top = dst2.turning_satin(p, ln, sp=st.spacing, pull=st.pull_comp, short=st.params.get("short", False))
            out.append(Block(part.id, "top", top))
        return [b for b in out if len(b.pts) > 1]

