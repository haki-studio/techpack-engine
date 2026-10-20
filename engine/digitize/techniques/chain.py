"""CHAIN STITCH lines (ENGINE_PLAN M6): two plugins, the run's toggles choose (kind chain_line: [chain, faux_chain],
first enabled wins; both off = RulebookError, as for every kind).

  chain        a true chain stitch, sewn on a CHENILLE head in chain mode (sequencing machine="chenille"): a path at a
               CONSTANT stitch length (the head forms the links; Wilcom: stitch length sets the link size and must stay
               constant). Plan only: the machine file waits for the factory's chenille format (F1,
               specialty.export_chenille raises FactoryFormatNeeded). Default OFF in config.DEFAULTS until it is known.
  faux_chain   the lock-stitch fallback for the Brother heads when chain mode is not available: every link is a closed
               oval loop (forward along one side, back along the other) followed by a hidden advance along the line,
               so the line reads as linked loops, not a run; each stitch is short (link / 2), like a bean it is
               sewn three times over the line. Gate: specialty.faux_chain_gates (on the written file).

Line: part.meta["line"], else the part's centreline, else its outline (run.lines)."""
import math
import numpy as np
from shapely.geometry import LineString
from digitize.schema import Block
from digitize.techniques import Technique, register
from digitize.techniques.run import Run, lines
from digitize.techniques.chenille import resample_const


def faux_links(pts, link=2.5, h=0.45, overlap=0.3):
    """lock-stitch chain: per link a -> b along the line, needle points a, m+ (left of the line), b, m- (right), a, b.
    The next link starts `overlap` of a link back from b, so the loops interlock like a real chain."""
    ls = LineString(pts); T = ls.length
    if T < 1e-6: return [tuple(pts[0])]
    step = link * (1 - overlap); n = max(1, int(math.ceil(T / step))); step = T / n
    P = lambda s: np.array(ls.interpolate(min(max(s, 0.0), T)).coords[0])
    def normal(s):
        t = P(s + 0.2) - P(s - 0.2); t = t / max(np.linalg.norm(t), 1e-9); return np.array([-t[1], t[0]])
    out = [tuple(P(0.0))]
    for i in range(n):
        s = i * step; e = min(s + max(link, step), T); m = (s + e) / 2; nn = normal(m)   # a link along the line itself
        out += [tuple(P(m) + nn * h), tuple(P(e)), tuple(P(m) - nn * h), tuple(P(s)), tuple(P(s + step))]
    return out


@register
class Chain(Technique):
    name = "chain"; stype = "run"
    sequencing = {"machine": "chenille", "after_fill": True}

    def check(self, part, principles):
        return Run.check(self, part, principles)

    def detail(self, part):
        P = part.stitch.params; L = float(P.get("chain_len", part.stitch.stitch_len or 2.0))
        paths = [resample_const(l, L, closed=math.dist(l[0], l[-1]) < 1e-6) for l in lines(part) if len(l) >= 2]
        return dict(chain=paths, moss=[], spec=dict(chain_len=L, chain_needle_height=P.get("chain_needle_height"),
                                                   yarn=P.get("yarn", "chenille yarn [proposed - confirm]")))

    def plan(self, part):
        return [Block(part.id, "top", p) for p in self.detail(part)["chain"] if len(p) > 1]


@register
class FauxChain(Technique):
    name = "faux_chain"; stype = "bean"; sequencing = {"after_fill": True}

    def check(self, part, principles):
        return Run.check(self, part, principles)

    def plan(self, part):
        P = part.stitch.params
        return [Block(part.id, "top", faux_links(l, P.get("link", 2.5), P.get("half_w", 0.45), P.get("overlap", 0.3)))
                for l in lines(part) if len(l) >= 2]
