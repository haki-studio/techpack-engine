"""Split satin: satin rows too long for one stitch (> 7 mm), split into pieces <= ~6.9 mm whose split points are
STAGGERED from row to row (a three-phase brick offset, deterministic), so no split line shows. dst2.turning_satin splits
every row into equal pieces, so its split points line up across the whole column: a visible seam (and the reason this
plugin exists; tests/test_digitize_m1.py::test_split_satin_staggers).

Two modes (StitchSpec.params["mode"]):
  "fixed"  (default) rows are hatch lines across the part at the declared angle, sewn boustrophedon cell by cell. Falls:
           cords at 90 deg, so the threads run down the water like the reference's long vertical stitches.
  "column" rows cross a centreline (part.meta["cl"], else the part's skeleton) at its width: a wide stroke.
Underlay: centre_run along the part's centreline (rule 7: centre run on narrow parts)."""
import math
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys
from digitize.techniques import column as C

PHASES = (0.0, 1.0, -1.0)            # x stagger: row k's split points shift by PHASES[k % 3] * stagger of a piece


def split_row(a, b, k, max_piece=5.5, stagger=0.25, limit=7.0, min_pieces=1):
    """points after a on the stitch a -> b: [b] when short, else the staggered split points then b. Every piece
    <= (1 + stagger) * max_piece (6.9 mm with the defaults). Rows k and k +- 1 get different phases (a three-phase
    cycle), so on rows of similar length their split points do not line up; rows k and k + 3 share a phase, and rows of
    different lengths can still coincide here and there, which is why the file is checked, not this promise
    (qa.split_satin_rows aligned fraction; tests/test_digitize_m1.py::test_split_satin_staggers). min_pieces=2 splits
    every row longer than 0.6 mm (fixed-angle cords: their short end rows would otherwise sew as a satin blob)."""
    L = math.dist(a, b)
    m = max(int(math.ceil(L / max_piece)), min_pieces if L > 0.6 else 1)
    if m <= 1 and L <= limit: return [b]
    m = max(m, 2); ph = PHASES[k % 3] * stagger
    flip = tuple(b) < tuple(a)                 # phase measured from the same side whichever way the row is sewn
    fs = sorted(((j + ph) / m if not flip else 1 - (j + ph) / m) for j in range(1, m))
    return [(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f) for f in fs] + [b]


def column_rows(cl, w, sp, pull=0.0, caps=("flat", "flat"), max_piece=5.5, stagger=0.25):
    """zig-zag satin along a column with staggered splits (column.column_pts, minus its random jitter)"""
    rr = C.rows(cl, w, sp, pull, caps)
    if not rr: return []
    seq = [rr[0][1]]
    for k, (A, B) in enumerate(rr): seq.append(A if k % 2 == 0 else B)
    out = [seq[0]]
    for k, q in enumerate(seq[1:]): out += split_row(out[-1], q, k, max_piece, stagger)
    return out


@register
class SplitSatin(Technique):
    name = "split_satin"; stype = "satin"

    def check(self, part, principles):
        return []

    def plan(self, part):
        st = part.stitch; P = st.params; mode = P.get("mode", "fixed"); out = []
        piece = st.stitch_len; stg = P.get("stagger", 0.25)
        for p in polys(part.geom):
            if p.area < 0.3: continue
            cl = part.meta.get("cl") if mode == "column" else None
            line = None
            if cl is None:
                line = dst2.centreline(p)
                if line is not None: cl = list(line.coords)
            if "centre_run" in st.underlay and cl is not None and len(cl) >= 2:
                out.append(Block(part.id, "underlay", dst2.path_resample([tuple(c) for c in cl], 2.0)))
            if mode == "column":
                if cl is None: continue
                w = part.meta.get("w") or (p.area / max(line.length if line is not None else C.poly_len(cl), 1e-6))
                out.append(Block(part.id, "top", column_rows([tuple(c) for c in cl], w, st.spacing, st.pull_comp, max_piece=piece, stagger=stg)))
                continue
            top = p.buffer(st.pull_comp * 0.5) if st.pull_comp else p
            rows = dst2.chain_rows(dst2.SR.hatch(top, part.dir.angle, st.spacing), top, part.dir.angle, st.spacing)
            cur = []
            for a, b, k in rows:
                if cur and math.dist(cur[-1], a) > 1.2:
                    out.append(Block(part.id, "top", cur)); cur = []
                if not cur: cur = [a]
                elif cur[-1] != a: cur.append(a)
                cur += split_row(a, b, k, piece, stg, min_pieces=2)
            if cur: out.append(Block(part.id, "top", cur))
        return [b for b in out if len(b.pts) > 1]
