"""Radial satin (ENGINE_PLAN: radial only for face-on florets; M5 adds it for the konpeito patches): stitches run along
rays from the part's centre (part.meta["centre"]), every other one shortened toward the centre (dst2.radial_satin).
For 5-petal border flowers, puffy stars and tiny rings (handakuten). Underlay: edge run (0.45 inset) on parts wider
than 2.5 mm when "edge_run" is in the spec (as dst2.build_object). check() flags radial on a kind that is not a floret
(rule 4: radial only for face-on florets; params allowed_kinds)."""
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys, width_of


@register
class Radial(Technique):
    name = "radial"; stype = "satin"

    def check(self, part, principles):
        ok = part.stitch.params.get("allowed_kinds") if part.stitch else None
        out = []
        if ok and part.kind not in ok:
            out.append(self.issue(part, f"radial satin on kind {part.kind!r} (rule 4: radial only for face-on florets {ok})", rule=4))
        if not part.meta.get("centre"): out.append(self.issue(part, "radial without a centre (part.meta centre)", rule=4))
        return out

    def plan(self, part):
        st = part.stitch; out = []
        cx, cy = part.meta.get("centre") or part.geom.centroid.coords[0]      # a floret's centre (default: its centroid)
        for p in polys(part.geom):
            if p.area < 0.06: continue
            if "edge_run" in st.underlay and width_of(p) > 2.5: out += [Block(part.id, "underlay", b) for b in dst2.edge_run(p, 0.45)]
            out.append(Block(part.id, "top", dst2.radial_satin(p, cx, cy, sp=st.spacing, pull=st.pull_comp)))
        return [b for b in out if len(b.pts) > 1]
