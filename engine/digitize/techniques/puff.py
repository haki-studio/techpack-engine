"""3D PUFF (foam) satin columns (ENGINE_PLAN M6). Lock-stitch, so it sews on the factory's Brother heads (factory.json
puff_3d: true); the machine stops before the puff stop so the operator lays the foam, then the satin cuts through it.

House practice (cited in BENCH_m6.md; numbers marked [proposed - confirm] until the factory's strike-off):
  * satin columns only, never fill: fill rows put penetrations INSIDE the foam and flatten it (Ignition Drawing,
    Drawstitch); the satin's two edges are what cut the foam (Ignition: "the thread is what cuts through the foam").
  * dense: ~2x flat density (Impressions); Wilcom's webinar digitizer sews 0.18 mm. House default 0.20 mm row spacing,
    gate <= 0.30 mm (brief).
  * no underlay over the foam (Wilcom webinar: "none, only minimal support"). Allowed: an optional `tack` = one edge run
    0.3 mm inside the column sides (EmbPunch: a run to hold the foam), on the cut line, never across the body.
  * column width 3 mm minimum (Wilcom: 3 mm best case, 2 mm over-compresses the foam), 7 mm house maximum.
    Published practice allows 10-12 mm (Wilcom webinar 12, Ignition 12), but the house never sews a stitch > 7.5 mm
    (LESSONS B7 / B17: dst2.make_pattern splits anything > 7.4 mm), and a split point inside a puff column perforates
    the foam mid-column (the swatch gate satin_only reads it off the file: tests/test_digitize_m6.py). So wider art is
    split into side-by-side columns by the part extractor, never filled, never split across. Raising max_w needs the
    factory to confirm long stitches on their Brother heads AND a puff exemption in make_pattern (not built).
  * closed ends: an open column end is first PERFORATED (a dense run there and back across the end, 0.5 mm stitches:
    the cut-through tie-down that lets the foam tear away cleanly; Ignition "open ends need perforating"), then CAPPED
    with a small satin across the end (EmbPunch "close the open ends with a small column across"), reaching 0.5 mm
    past the column end (Wilcom). Rings (closed columns) have no ends.
  * foam: 3 mm (Wilcom: 3-4 mm, never over 4; Madeira E-Zee 3 mm), colour matched to the thread; gate 2-4 mm.

part.meta: cl, w (the column; else the part's skeleton + mean width), closed (ring), foam=dict(thickness_mm, colour).
Gates: digitize.techniques.specialty.puff_gates (on the WRITTEN file's segments) + plan_gates (foam stop, no tatami)."""
import math
import numpy as np
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys
from digitize.techniques import column as C

ROW_MAX = 7.5           # LESSONS B7: never a sewn stitch > 7.5 mm (dst2 splits at 7.4: inside puff, that perforates the foam)


def columns_of(part):
    """[dict(cl, w, closed)] for the part: part.meta columns (list), else cl/w, else each polygon's skeleton"""
    m = part.meta
    if m.get("columns"):
        return [dict(cl=[tuple(c) for c in q["cl"]], w=float(q["w"]), closed=bool(q.get("closed", False))) for q in m["columns"]]
    if m.get("cl") and m.get("w"):
        return [dict(cl=[tuple(c) for c in m["cl"]], w=float(m["w"]), closed=bool(m.get("closed", False)))]
    out = []
    for p in polys(part.geom):
        ln = dst2.centreline(p)
        if ln is None: continue
        cl = list(ln.coords); out.append(dict(cl=cl, w=float(p.area / max(C.poly_len(cl), 1e-6)), closed=False))
    return out


def foam_of(part):
    P = part.stitch.params if part.stitch else {}
    f = dict(thickness_mm=P.get("foam_mm", 3.0), colour=P.get("foam_colour", "match thread"))
    f.update(part.meta.get("foam") or {})
    return f


def zigzag_rows(rr):
    """rows [(A, B)] -> B0, A0, B1, A1 ... one needle point per row, never split (puff: no split points in the foam)"""
    if not rr: return []
    seq = [rr[0][1]]
    for k, (A, B) in enumerate(rr): seq.append(A if k % 2 == 0 else B)
    return seq


def end_frame(cl, at_start):
    """(end point E, outward unit tangent t, unit normal n) at one end of an open centreline"""
    pts = cl if at_start else cl[::-1]
    E = np.array(pts[0], float); q = np.array(C._at(pts, C._cum(pts), min(1.0, C.poly_len(pts))), float)
    t = E - q; t /= max(np.linalg.norm(t), 1e-9); n = np.array([-t[1], t[0]])
    return E, t, n


def perforation(E, n, w, step=0.5, over=0.3, passes=2):
    """the cut-through tie-down across an open end: a run of `step` mm stitches across the end line, there and back"""
    h = w / 2 + over; m = max(2, int(math.ceil(2 * h / step)))
    line = [tuple(E + n * (h - 2 * h * i / m)) for i in range(m + 1)]
    out = list(line)
    for k in range(1, passes): out += (line[::-1] if k % 2 else line)[1:]
    return out


def cap(E, t, n, w, cap_w=1.5, ext=0.5, sp=0.20, over=0.3):
    """a small satin ACROSS the open end: its centreline runs along the end line, its stitches run along the column
    (parallel to t), from cap_w - ext inside the end to ext past it (Wilcom: end caps reach ~0.5 mm past the end)"""
    h = w / 2 + over; m = max(2, int(math.ceil(2 * h / sp)))
    a, b = E - t * (cap_w - ext), E + t * ext
    out = []
    for i in range(m + 1):
        off = n * (h - 2 * h * i / m)
        out.append(tuple((b if i % 2 == 0 else a) + off))
    return out


@register
class Puff(Technique):
    name = "puff"; stype = "satin"
    sequencing = {"after_fill": True, "foam_stop": True}      # its own stop, after the flat work it touches

    def check(self, part, principles):
        out = []; P = part.stitch.params if part.stitch else {}
        lo, hi = P.get("min_w", 3.0), P.get("max_w", 7.0)
        cols = columns_of(part)
        if not cols: out.append(self.issue(part, "puff part without a column (centreline + width): puff is satin only, never fill", rule=4))
        for q in cols:
            if q["w"] < lo: out.append(self.issue(part, f"puff column {q['w']:.2f} mm wide < {lo} mm: the foam over-compresses (Wilcom: 3 mm min)", rule=4))
            if q["w"] > hi: out.append(self.issue(part, f"puff column {q['w']:.2f} mm wide > {hi} mm: split the art into columns (never fill puff)", rule=4))
        f = foam_of(part); fl, fh = P.get("foam_min_mm", 2.0), P.get("foam_max_mm", 4.0)
        if not (fl <= float(f["thickness_mm"]) <= fh): out.append(self.issue(part, f"foam {f['thickness_mm']} mm outside {fl}-{fh} mm", rule=4))
        return out

    def plan(self, part):
        st = part.stitch; P = st.params; out = []
        for q in columns_of(part):
            cl, w, closed = q["cl"], q["w"], q["closed"]
            if "tack" in st.underlay:
                for sgn in (1, -1):
                    rr = C.rows(cl, max(w - 0.6, 0.3), P.get("tack_len", 2.5), 0.0, ("flat", "flat"), closed)
                    out.append(Block(part.id, "underlay", [r[0] if sgn > 0 else r[1] for r in rr]))
            rr = C.rows(cl, w, st.spacing, st.pull_comp, ("flat", "flat"), closed)
            col = zigzag_rows(rr)
            if closed:
                out.append(Block(part.id, "top", col)); continue
            cw, ext = P.get("cap_w", 1.5), P.get("cap_ext", 0.5)
            E0, t0, n0 = end_frame(cl, True); E1, t1, n1 = end_frame(cl, False)
            out.append(Block(part.id, "top", perforation(E0, n0, w, P.get("perf_step", 0.5))))
            out.append(Block(part.id, "top", cap(E0, t0, n0, w, cw, ext, st.spacing)))
            out.append(Block(part.id, "top", col))
            out.append(Block(part.id, "top", perforation(E1, n1, w, P.get("perf_step", 0.5))))
            out.append(Block(part.id, "top", cap(E1, t1, n1, w, cw, ext, st.spacing)))
        return [b for b in out if len(b.pts) > 1]
