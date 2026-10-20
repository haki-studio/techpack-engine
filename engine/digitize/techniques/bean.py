"""Bean (triple run): every stitch sewn forward, back, forward, for a bold line under 1 mm (rule 4)."""
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register
from digitize.techniques.run import Run, lines


def triple(pts):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]): out += [b, a, b]
    return out


@register
class Bean(Technique):
    name = "bean"; stype = "bean"; sequencing = {"after_fill": True}

    def check(self, part, principles):
        return Run.check(self, part, principles)

    def plan(self, part):
        return [Block(part.id, "top", triple(dst2.path_resample(l, part.stitch.stitch_len))) for l in lines(part) if len(l) >= 2]
