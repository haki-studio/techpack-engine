"""Column satin for lettering, line art and heat-cut edges (ENGINE_PLAN M5; konpeito kjcore column builder, promoted).

A column = centreline + ONE needle width (part.meta: cl, w, caps ("round"/"flat" per end), closed, prof). Every stitch
crosses the column perpendicular to the smoothed centreline (column.rows), alternating sides, so each row puts ONE
needle point on one side: the distance between two penetrations on the SAME side is twice the row spacing.

Density is therefore given as `same_side` (konpeito ENGINE_NOTES 7: Rev A's "0.30" sewed 0.60 mm same side and read as
comb-like, open satin): 0.40 for 40wt, 0.28 for 60wt (params same_side: {40wt: 0.40, 60wt: 0.28}, picked by
part.meta["thread_wt"]), halved internally to the row spacing. Rows longer than 7 mm are split with the split_satin
stagger (deterministic, no jitter). Underlay (rule 7): a centre run on open columns >= centre_run_min_w wide and
> centre_run_min_len long, trimmed 0.6 mm short of the ends; the column then sews back over it (reversed), so the
needle ends where the underlay started. Closed columns (rings, the patch edge) have no centre run.

Checked by tests/test_digitize_m5.py::test_column_same_side_density_on_the_file (read-back stitches per mm of a 10 mm
column)."""
import math
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register
from digitize.techniques import column as C
from digitize.techniques.split_satin import split_row


def same_side_of(part):
    ss = part.stitch.params.get("same_side", 0.40)
    if isinstance(ss, dict): ss = ss.get(part.meta.get("thread_wt", "40wt"), ss.get("40wt", 0.40))
    return float(ss)


def zigzag(rr, max_piece=5.5, stagger=0.25):
    """rows [(A, B)] -> needle points B0, A0, B1, A1 ... (one point per row, alternating sides), long rows split"""
    if not rr: return []
    seq = [rr[0][1]]
    for k, (A, B) in enumerate(rr): seq.append(A if k % 2 == 0 else B)
    last = rr[-1]; seq.append(last[1] if (len(rr) - 1) % 2 == 0 else last[0])
    out = [seq[0]]
    for k, q in enumerate(seq[1:]): out += split_row(out[-1], q, k, max_piece, stagger)
    return out


def column_points(cl, w, same_side, pull=0.0, caps=("round", "round"), closed=False, prof=None, reverse=False, max_piece=5.5, stagger=0.25):
    if reverse: cl, caps = list(cl)[::-1], tuple(caps)[::-1]
    return zigzag(C.rows(cl, w, same_side / 2.0, pull, caps, closed, prof), max_piece, stagger)


@register
class ColumnSatin(Technique):
    name = "column_satin"; stype = "satin"; sequencing = {"after_fill": True}

    def check(self, part, principles):
        out = []; m = part.meta
        if not m.get("cl") or not m.get("w"):
            return [self.issue(part, "column satin without a centreline + width (part.meta cl, w)", rule=4)]
        w = float(m["w"]); lo, hi = principles.get("satin_min_w_mm", 1.0), principles.get("satin_max_w_mm", 7.0)
        if w > hi: out.append(self.issue(part, f"column {w:.2f} mm wide > {hi} mm: split satin (rule 4)", rule=4))
        if w < lo:
            out.append(self.issue(part, f"column {w:.2f} mm wide < {lo} mm house satin minimum (rule 9): reported, sewn at the art "
                                        f"width ({m.get('thread_wt', '40wt')})", rule=9, severity="report"))
        return out

    def plan(self, part):
        st = part.stitch; m = dict(part.meta); P = st.params
        if not m.get("cl"):                       # no declared column: the part's own skeleton + mean width
            line = dst2.centreline(part.geom if part.geom.geom_type == "Polygon" else max(part.geom.geoms, key=lambda g: g.area))
            if line is None: return []
            m["cl"] = list(line.coords); m.setdefault("w", part.geom.area / max(line.length, 1e-6)); m.setdefault("caps", ("flat", "flat"))
        cl = [tuple(c) for c in m["cl"]]; w = float(m["w"]); caps = tuple(m.get("caps") or ("round", "round"))
        closed = bool(m.get("closed", False)); prof = m.get("prof")
        if isinstance(prof, list): prof = tuple(prof)
        ss = same_side_of(part); pull = st.pull_comp; out = []
        L = C.poly_len(cl + ([cl[0]] if closed else []))
        cr = ("centre_run" in st.underlay and not closed and L > P.get("centre_run_min_len", 2.5)
              and w >= P.get("centre_run_min_w", 1.4))
        if cr:
            e = min(0.6, w / 2)
            out.append(Block(part.id, "underlay", dst2.path_resample(C.trim(cl, e, e), 2.0)))
        out.append(Block(part.id, "top", column_points(cl, w, ss, pull, caps, closed, prof, reverse=cr,
                                                        max_piece=P.get("max_piece", 5.5), stagger=P.get("stagger", 0.25))))
        return [b for b in out if len(b.pts) > 1]
