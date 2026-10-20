"""Guided fill (ENGINE_PLAN M2; DIGITIZING_PRINCIPLES rule 2, organic parts): tatami whose ROWS FOLLOW the part's
direction field instead of one straight angle (Wilcom "guided fill" / Ink/Stitch guided fill).

The field comes with the part (part.meta["field"], a grid written by the splitter from digitize.direction.Field: the
reference grain, evidence only) and is turned by the part's declared offset (dir.angle - meta["field_mean"]: rule 3
neighbour separation, stratum band alternation). Rows are the level sets phi = (k + 1/2) * spacing of the PHASE FIELD
(direction.phase: grad phi is the field's normal, solved by least squares), so they run along the grain and stay ~one
spacing apart even where the grain turns. Each row is clipped to the part (+ half the pull compensation), sewn
boustrophedon cell by cell (nearest next row end), and stitched every stitch_len with the tatami brick stagger (row k
offset by (k mod 3) / 3 of a stitch). A row shorter than one stitch gets a penetration (tatami.split_short, LESSONS A18).
Underlay: edge run + a 90-degree lattice at the field's mean angle (rule 7), like tatami."""
import math
import numpy as np
from shapely.geometry import LineString
import dst2
from digitize.schema import Block
from digitize.techniques import Technique, register, polys, fits_width
from digitize.techniques.tatami import split_short


def offset_of(part):
    return ((part.dir.angle - part.meta.get("field_mean", part.dir.angle) + 90.0) % 180.0) - 90.0


def rows_of(geom, grid, spacing, offset_deg=0.0, ppm=None):
    """[(k, LineString)] guided rows clipped to geom; k = level index (rows k and k + 1 are neighbours)"""
    from skimage import measure
    from digitize import direction as DR
    if ppm is None: ppm = max(3.0, min(6.0, 2.2 / spacing))       # ~5 px per row: level sets are interpolated, smooth
    ph = DR.phase(geom, grid, ppm=ppm, offset_deg=offset_deg)
    phi = ph["phi"]; m = ph["mask"]; b = ph["bounds"]
    if not np.isfinite(phi).any(): return []
    lo, hi = np.nanmin(phi), np.nanmax(phi)
    filled = np.where(m, phi, np.nanmean(phi))
    out = []
    k0 = int(math.floor(lo / spacing))
    for k in range(k0, int(math.ceil(hi / spacing)) + 1):
        lev = (k + 0.5) * spacing
        if not (lo < lev < hi): continue
        for c in measure.find_contours(filled, lev, mask=m):
            if len(c) < 2: continue
            xs = b[0] + (c[:, 1] + 0.5) / ph["ppm"]; ys = b[1] + (c[:, 0] + 0.5) / ph["ppm"]
            ln = LineString(np.c_[xs, ys]).simplify(0.05)
            g = ln.intersection(geom)
            for s in ([g] if g.geom_type == "LineString" else [q for q in getattr(g, "geoms", []) if q.geom_type == "LineString"]):
                if s.length >= 0.3: out.append((k - k0, s))
    return out


def chain(rows, spacing=0.45, hop=1.5):
    """cell by cell, like dst2.chain_rows (LESSONS B23) on curved rows: a cell is a run of rows on consecutive levels
    that lie side by side (overlap: one row runs within 1.6 spacings of the other for >= 0.3 mm). Start a cell at a
    free row with no free neighbour on the level below (nearest to the needle); walk up, boustrophedon, while the next
    level has a free neighbour whose nearer end is within hop mm; stop where the run splits around a hole or where
    another unsewn run merges in (it gets its own cell, so the needle never has to travel back over sewn rows)."""
    from shapely.strtree import STRtree
    by = {}
    for i, (k, s) in enumerate(rows): by.setdefault(k, []).append(i)
    geoms = [s for _, s in rows]; tree = STRtree(geoms) if geoms else None
    halo = [s.buffer(1.6 * spacing) for s in geoms]
    nb = [set() for _ in rows]
    for i, (k, s) in enumerate(rows):
        for j in tree.query(halo[i]):
            j = int(j)
            if j != i and abs(rows[j][0] - k) == 1 and halo[i].intersection(geoms[j]).length >= 0.3: nb[i].add(j); nb[j].add(i)
    used = [False] * len(rows); out = []; pos = None
    ends = [(tuple(s.coords[0]), tuple(s.coords[-1])) for s in geoms]
    near = lambda i: min(math.dist(pos, ends[i][0]), math.dist(pos, ends[i][1]))
    while not all(used):
        free = [i for i in range(len(rows)) if not used[i]]
        starts = [i for i in free if not any(not used[j] and rows[j][0] == rows[i][0] - 1 for j in nb[i])] or free
        i = min(starts, key=lambda i: (rows[i][0], ends[i][0])) if pos is None else min(starts, key=near)
        blk = []
        while True:
            used[i] = True; a, b = ends[i]; pts = list(rows[i][1].coords)
            if pos is not None and math.dist(pos, b) < math.dist(pos, a): pts = pts[::-1]
            blk.append((rows[i][0], pts)); pos = pts[-1]
            up = [j for j in nb[i] if not used[j] and rows[j][0] == rows[i][0] + 1]
            if not up: break
            t = min(up, key=near)
            if near(t) > hop: break
            if any(not used[u] and rows[u][0] == rows[i][0] for u in nb[t]): break      # another unsewn run joins here
            i = t
        out.append(blk)
    return out


def stitch_row(pts, k, L):
    """penetrations every L mm along a polyline, first one at (k mod 3) / 3 of a stitch (brick stagger)"""
    ln = LineString(pts); d = ln.length
    if d < 1e-6: return [tuple(pts[0])]
    off = (k % 3) * L / 3.0; t = off if off > 0.4 else L; run = [tuple(pts[0])]
    while t < d - 0.4:
        q = ln.interpolate(t); run.append((q.x, q.y)); t += L
    run.append(tuple(pts[-1]))
    return run


@register
class GuidedFill(Technique):
    name = "guided_fill"; stype = "tatami"

    def check(self, part, principles):
        out = []
        if not part.meta.get("field"):
            out.append(self.issue(part, "guided fill without a direction field (part.meta['field']): the splitter must give one", rule=2))
        w = principles.get("fill_min_w_mm", 5.0)
        if not fits_width(part.geom, w):
            out.append(self.issue(part, f"fill narrower than {w} mm everywhere (rule 4: fill only where >= ~5 mm wide)", rule=4))
        return out

    def plan(self, part):
        st = part.stitch; grid = part.meta.get("field")
        if not grid: raise ValueError(f"guided_fill {part.id}: no direction field in part.meta['field'] (never a guessed angle)")
        off = offset_of(part); out = []
        for p in polys(part.geom):
            if p.area < 0.3: continue
            if "edge_run" in st.underlay:
                out += [Block(part.id, "underlay", b) for b in dst2.edge_run(p, 0.6)]
            if "lattice_90" in st.underlay and p.area > st.params.get("lattice_min_mm2", 60.0):
                q = p.buffer(-0.8)
                if not q.is_empty: out += [Block(part.id, "underlay", b) for b in dst2.join_rows(dst2.tatami_rows(q, part.dir.angle + 90, 2.0, 4.0))]
            top = p.buffer(st.pull_comp * 0.5) if st.pull_comp else p
            for blk in chain(rows_of(top, grid, st.spacing, off), st.spacing):
                rr = split_short([stitch_row(pts, k, st.stitch_len) for k, pts in blk])
                pts = []
                for r in rr:
                    if pts and math.dist(pts[-1], r[0]) > 1.6:
                        out.append(Block(part.id, "top", pts)); pts = []
                    pts += [q for q in r if not pts or q != pts[-1]]
                if len(pts) > 1: out.append(Block(part.id, "top", pts))
        return [b for b in out if len(b.pts) > 1]
