"""Bead dot (ENGINE_PLAN M5; konpeito ENGINE_NOTES 11 + 13, from kjletter.knot_points): a round dot sewn as a tiny
cross underlay (lifts the bead) + dense satin rows at ONE angle, each row's half-length following the circle. dst2's
auto-angle satin fans on circles; this does not.

part.meta["knots"] = [(x, y, needle_d, angle_deg)], one or more beads sewn as one object (a knot cluster). Needle
diameter = art diameter - 0.2 mm (thread + pull: the bead reads ~0.2 mm wider than its needle span; gate-calibrated on
the konpeito DST read-back), never below the house minimum (dot min_d, 1.1 mm for satin dots): a smaller art dot sews
at the minimum and is REPORTED (part.meta["house_min"], check() issue), not hidden. extract/svg.py sets the numbers;
this plugin only sews them. Row spacing = StitchSpec.spacing (0.18)."""
import math
from digitize.schema import Block
from digitize.techniques import Technique, register


def bead_points(knots, sp=0.18, underlay=True):
    seq = []
    for kn in knots:
        x, y, d = kn[:3]; a = kn[3] if len(kn) > 3 else 0.0
        r = d / 2; t = math.radians(a); ux, uy = math.cos(t), math.sin(t); vx, vy = -uy, ux
        if underlay:
            q = 0.3 * r
            seq += [(x - ux * q, y - uy * q), (x + ux * q, y + uy * q), (x, y), (x - vx * q, y - vy * q), (x + vx * q, y + vy * q)]
        n = max(4, int(d / sp))
        for k in range(n + 1):
            o = -r + d * k / n; hw = math.sqrt(max(0.0, r * r - o * o)) * 0.95
            if hw < 0.1: continue
            A = (x + vx * o - ux * hw, y + vy * o - uy * hw); B = (x + vx * o + ux * hw, y + vy * o + uy * hw)
            seq += [A, B] if k % 2 == 0 else [B, A]
    return seq


def needle_d(art_d, min_d=1.1, allow=0.2):
    """(needle diameter, house_min) for an art dot of diameter art_d"""
    d = round(art_d - allow, 3)
    return (max(min_d, d), d < min_d - 1e-9)


@register
class Dot(Technique):
    name = "dot"; stype = "satin"; sequencing = {"after_fill": True}

    def check(self, part, principles):
        out = []
        if not part.meta.get("knots"): out.append(self.issue(part, "dot without beads (part.meta knots)", rule=4))
        if part.meta.get("house_min"):
            out.append(self.issue(part, f"art dot Ø{part.meta.get('art_d', 0):.2f} mm is under the house minimum: sewn at "
                                        f"Ø{part.meta['knots'][0][2]:.2f} (reported, rule 9)", rule=9, severity="report"))
        return out

    def plan(self, part):
        sp = part.stitch.spacing or 0.18
        knots = part.meta.get("knots")
        if not knots:                             # no declared beads: one bead at the part's centre, its area's diameter
            c = part.geom.centroid; d, _ = needle_d(2 * math.sqrt(part.geom.area / math.pi), part.stitch.params.get("min_d", 1.1))
            knots = [(c.x, c.y, d, float(part.dir.angle))]
        pts = bead_points(knots, sp, underlay="cross" in part.stitch.underlay)
        return [Block(part.id, "top", pts)] if len(pts) > 1 else []
