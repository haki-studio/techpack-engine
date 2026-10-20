"""M4s: two gates read from the LABELLED written DST (compile.labelled_dst: the plan's part id on every file segment,
None on dst2's hidden travel and the writer's tie stitches).

part_stack     rule 6 (never more than 2 stacked layers) counted by PARTS, not by runs. The strict file gate
               (qa.stack_map) counts trim-delimited runs reaching layer density per 1 mm cell; most of its cells > 2 are
               junction cells and hidden travel crossing them (M4g: 441 cells > 2, 12 truly 3 deep). Here a layer is a
               PART (its underlay + top + edge together) whose own thread reaches layer density (1.5 mm/mm2) in a
               1 mm window, on 0.25 mm cells, ERODED by one cell (a part is a layer where it is solid, so a window
               straddling a seam or a pull-comp sliver is not a layer); travel (label None) and line parts (run / bean)
               are never layers. Gate: the area of connected regions >= 4 mm2 where >= 3 distinct parts are layers,
               per 100 cm2 of covered area, <= 2.5 (STACK_DEFAULTS; why these numbers: the comment there and
               bench/BENCH_m4s.md). It sees thick 3-deep AREAS only: 1 mm underlap bands three deep are mostly eroded
               away (M2 file: 23.5 mm2 flagged of 3.84 cm2 three deep in plan geometry), which the strict gate keeps.
travel_on_fill same-colour (or any-colour) travel lying ON TOP of fill sewn EARLIER in the file and not buried by fill
               sewn LATER: visible on the live view and on the garment (M2 4.9 m, M4g 3.3 m on the crop, ungated before
               M4s). Exposure thresholds as qa.exposed_stitches (M5 patches: min_mm 0.5, min_ex 0.3). Metric: exposed
               travel mm per 100 cm2 of covered area; gate: exposed stitches == 0 (target 0, the M5 house standard).

Both are density timelines on one raster; no Anthropic API calls."""
import math
import numpy as np

# Why these numbers (the sweep is in bench/BENCH_m4s.md):
# - window 1.0 mm: one row of thread gives 1.0 mm/mm2 (< layer_min 1.5, so a lone row or an edge run is not a layer) and
#   any fill with rows <= 0.5 mm apart gives >= 2.0 in EVERY window (a 0.75 mm window aliases: 1 or 2 rows, half the
#   cells of a real layer drop out).
# - cells 0.25 mm + erode 1 cell: on 0.5 mm cells a 1 mm window cannot resolve a seam (M4g, <= 2 deep in plan
#   geometry: 1,532 cells > 2, only 67 really 3 deep) and a 1-cell erosion there would delete whole 1 mm bands.
# - min_region_mm2 4.0 (the strict gate's own flag size, qa.stack_map min_flag_mm2): what is left after the erosion at a
#   3-part JUNCTION is a speck (pull comp of three parts meeting); a really 3-deep area is a region. On the M2 file
#   94 % of the area in regions >= 2 mm2 is >= 3 deep in plan geometry; on the main crop 0 %.
# - cap 2.5 mm2 per 100 cm2 of covered area: M4g file 0, main crop 1.1 (one 4.3 mm2 village junction, plan depth 2),
#   M2 file 5.9, limit_stack-off 6.2. Chosen from these files; the founder decides before it replaces anything.
STACK_DEFAULTS = dict(cell_mm=0.25, window_mm=1.0, layer_min=1.5, erode_cells=1, max_parts=2, min_region_mm2=4.0, cap_per_100cm2=2.5)
TRAVEL_DEFAULTS = dict(cell_mm=0.5, window_mm=1.0, layer_min=1.5, min_mm=0.5, min_ex=0.3, target_exposed=0)


def _samples(segs, bounds, step):
    """every segment sampled every ~step mm: (x, y, length weight, segment index), inside bounds only"""
    S = np.asarray(segs, float).reshape(-1, 4)
    if not len(S): return np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0, int)
    L = np.hypot(S[:, 2] - S[:, 0], S[:, 3] - S[:, 1]); k = np.maximum(1, np.ceil(L / step)).astype(int)
    idx = np.repeat(np.arange(len(S)), k); j = np.arange(len(idx)) - np.repeat(np.cumsum(k) - k, k)
    t = (j + 0.5) / k[idx]
    x = S[idx, 0] + t * (S[idx, 2] - S[idx, 0]); y = S[idx, 1] + t * (S[idx, 3] - S[idx, 1]); w = L[idx] / k[idx]
    x0, y0, x1, y1 = bounds; inb = (x >= x0) & (x < x1) & (y >= y0) & (y < y1)
    return x[inb], y[inb], w[inb], idx[inb]


def _window_cells(x, y, bounds, cell, win):
    """each sample is counted in every cell whose win x win mm window (centred on the cell) contains it.
    Returns (cell flat index, sample index) pairs and the grid shape."""
    x0, y0, x1, y1 = bounds
    H = int(math.ceil((y1 - y0) / cell - 1e-9)); W = int(math.ceil((x1 - x0) / cell - 1e-9))
    r = int(round((win / cell - 1) / 2))                   # 1 mm window on 0.5 mm cells: the cell + half a cell around
    cx = (x - x0) / cell - 0.5; cy = (y - y0) / cell - 0.5  # sample in cell-centre units
    fl, si = [], []
    n = np.arange(len(x))
    for dy in range(-r - 1, r + 2):
        for dx in range(-r - 1, r + 2):
            ix = np.floor(cx).astype(int) + dx; iy = np.floor(cy).astype(int) + dy
            inside = (np.abs(cx - ix) <= win / cell / 2) & (np.abs(cy - iy) <= win / cell / 2) & (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
            fl.append(iy[inside] * W + ix[inside]); si.append(n[inside])
    return np.concatenate(fl), np.concatenate(si), (H, W)


def part_stack(segs, labels, bounds, line_parts=(), **kw):
    """rule 6 by PARTS on the labelled file. segs / labels: compile.labelled_dst output (labels None = travel / ties).
    line_parts: ids of run / bean parts (lines, never a layer). Returns dict(grid = parts per cell, max, over_mm2,
    covered_mm2, pct_over, cap_pct, flags, ok, params)."""
    P = dict(STACK_DEFAULTS, **kw); cell, win = P["cell_mm"], P["window_mm"]
    line = set(line_parts)
    keep = [i for i, l in enumerate(labels) if l is not None and l not in line]
    ids = {}; pid = np.array([ids.setdefault(labels[i], len(ids)) for i in keep], np.int64)
    S = [segs[i] for i in keep]
    x, y, w, si = _samples(S, bounds, cell / 5)
    fl, sj, (H, W) = _window_cells(x, y, bounds, cell, win)
    out = dict(params=P, parts_seen=len(ids))
    if not len(fl):
        grid = np.zeros((H, W), int)
    else:
        key = pid[si[sj]] * (H * W) + fl
        uk, inv = np.unique(key, return_inverse=True); dens = np.bincount(inv, w[sj]) / win ** 2
        lk = uk[dens >= P["layer_min"]]
        er = int(P.get("erode_cells", 0))
        if not er:
            grid = np.bincount(lk % (H * W), minlength=H * W).reshape(H, W)
        else:
            # a part is a layer only where it is SOLID: its layer cells eroded by erode_cells (a 1 mm window touching
            # three parts at a Y-junction, or a pull-comp sliver, is not three layers)
            from scipy import ndimage as ndi
            grid = np.zeros((H, W), int); part = lk // (H * W); flat = lk % (H * W)
            cut = np.r_[0, np.flatnonzero(np.diff(part)) + 1, len(part)]
            st = np.ones((3, 3), bool)
            for a, b in zip(cut[:-1], cut[1:]):
                iy, ix = np.divmod(flat[a:b], W)
                y0_, x0_ = iy.min() - er, ix.min() - er
                m = np.zeros((iy.max() - y0_ + er + 1, ix.max() - x0_ + er + 1), bool); m[iy - y0_, ix - x0_] = True
                m = ndi.binary_erosion(m, structure=st, iterations=er)
                yy, xx = np.nonzero(m); yy += y0_; xx += x0_
                ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
                np.add.at(grid, (yy[ok], xx[ok]), 1)
    # covered = any stitch at all (travel too) reaching layer density in the window: the denominator of the cap
    xa, ya, wa, _ = _samples(segs, bounds, cell / 5)
    fa, sa, _ = _window_cells(xa, ya, bounds, cell, win)
    cov = np.bincount(fa, wa[sa], minlength=H * W).reshape(H, W) / win ** 2 >= P["layer_min"]
    over = grid > P["max_parts"]
    from scipy import ndimage as ndi
    lab, _ = ndi.label(over, structure=np.ones((3, 3), bool)); flags = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        m = lab[sl] == k; a = float(m.sum()) * cell ** 2
        if a < P["min_region_mm2"]: continue               # a junction spill is a speck; a 3-deep area is a region
        flags.append(dict(at_mm=(round(bounds[0] + (sl[1].start + sl[1].stop) / 2 * cell, 1), round(bounds[1] + (sl[0].start + sl[0].stop) / 2 * cell, 1)),
                          area_mm2=round(a, 2), peak=int(grid[sl][m].max())))
    flags.sort(key=lambda f: -f["area_mm2"])
    raw_mm2 = float(over.sum()) * cell ** 2; cov_mm2 = float(cov.sum()) * cell ** 2
    if cov_mm2 <= 0: raise ValueError("part_stack: nothing sewn inside the bounds; a gate that saw nothing cannot pass")
    over_mm2 = float(sum(f["area_mm2"] for f in flags)); per = over_mm2 / (cov_mm2 / 1e4)
    out.update(grid=grid, max=int(grid.max()) if grid.size else 0, raw_over_mm2=round(raw_mm2, 2), over_mm2=round(over_mm2, 2),
               covered_mm2=round(cov_mm2, 1), per_100cm2=round(per, 2), cap_per_100cm2=P["cap_per_100cm2"],
               flags=flags[:40], n_flags=len(flags), ok=per <= P["cap_per_100cm2"])
    return out


def travel_on_fill(segs, labels, bounds, line_parts=(), travel_segs=None, **kw):
    """travel stitched ON TOP of fill sewn earlier and not buried by fill sewn later, on the labelled file.
    travel = file segments labelled None (dst2 hidden travel + the writer's ties) plus, when travel_segs is given, the
    segment indices of planned role "travel" blocks (sequence.plan_inner_travel). Fill = every other labelled segment
    of a non-line part. A travel sample is ON sewn fill when the fill sewn before it reaches layer_min in the 1 mm
    window around it, and BURIED when the fill sewn after it does. A stitch >= min_mm with more than min_ex mm on
    sewn fill and not buried is exposed. Returns dict(exposed=[(seg index, x, y, mm)], exposed_mm, n_exposed,
    travel_mm, covered_mm2, per_100cm2 (exposed mm), n_per_100cm2, ok)."""
    P = dict(TRAVEL_DEFAULTS, **kw); cell, win = P["cell_mm"], P["window_mm"]
    line = set(line_parts); tr = set(travel_segs or ())
    is_tr = np.array([(l is None) or (i in tr) for i, l in enumerate(labels)], bool)
    is_fill = np.array([(l is not None) and (l not in line) and (i not in tr) for i, l in enumerate(labels)], bool)
    x, y, w, si = _samples(segs, bounds, cell / 5)
    fl, sj, (H, W) = _window_cells(x, y, bounds, cell, win)
    N = H * W
    # fill events per cell in sew order -> first time the earlier fill reaches layer_min (t_on) and the last time the
    # LATER fill still does (t_off: a travel sewn before t_off is buried)
    fm = is_fill[si[sj]]
    fc, ft, fw = fl[fm], si[sj][fm], w[sj][fm] / win ** 2
    o = np.lexsort((ft, fc)); fc, ft, fw = fc[o], ft[o], fw[o]
    big = np.iinfo(np.int64).max
    t_on = np.full(N, big, np.int64); t_off = np.full(N, -1, np.int64)
    if len(fc):
        start = np.r_[0, np.flatnonzero(np.diff(fc)) + 1]
        cs = np.cumsum(fw); base = np.repeat(np.r_[0.0, cs[start[1:] - 1]], np.diff(np.r_[start, len(fc)]))
        cum = cs - base                                       # density sewn up to and including this event, per cell
        tot = np.zeros(N); np.add.at(tot, fc, fw)
        hit = cum >= P["layer_min"]
        first = np.full(N, big, np.int64); np.minimum.at(first, fc[hit], ft[hit]); t_on = first
        after = tot[fc] - cum + fw                             # density sewn from this event on (this event included)
        late = after >= P["layer_min"]
        last = np.full(N, -1, np.int64); np.maximum.at(last, fc[late], ft[late]); t_off = last
    # travel samples: a sample is exposed when every window cell it is counted in says "on sewn fill, not buried"
    # (the centre cell decides; the window already smooths the fill density)
    xt, yt, wt, st = _samples([segs[i] for i in np.flatnonzero(is_tr)], bounds, cell / 5)
    tidx = np.flatnonzero(is_tr)[st] if len(st) else np.zeros(0, int)
    x0, y0 = bounds[:2]
    ix = np.clip(((xt - x0) // cell).astype(int), 0, W - 1); iy = np.clip(((yt - y0) // cell).astype(int), 0, H - 1)
    c = iy * W + ix
    on = (t_on[c] < tidx) & ~(t_off[c] > tidx)
    ex_len = np.bincount(tidx[on], wt[on], minlength=len(segs)) if len(tidx) else np.zeros(len(segs))
    L = np.array([math.dist(s[:2], s[2:]) for s in segs]) if len(segs) else np.zeros(0)
    bad = np.flatnonzero(is_tr & (L >= P["min_mm"]) & (ex_len > P["min_ex"]))
    exposed = [(int(i), round((segs[i][0] + segs[i][2]) / 2, 1), round((segs[i][1] + segs[i][3]) / 2, 1), round(float(ex_len[i]), 2)) for i in bad]
    # covered area: any stitch reaching layer density in the window
    allc = np.bincount(fl, w[sj], minlength=N) / win ** 2 >= P["layer_min"]
    cov_mm2 = float(allc.sum()) * cell ** 2
    if cov_mm2 <= 0: raise ValueError("travel_on_fill: nothing sewn inside the bounds; a gate that saw nothing cannot pass")
    ex_mm = float(ex_len[bad].sum()); on_mm = float(ex_len[is_tr].sum())
    return dict(exposed=sorted(exposed, key=lambda e: -e[3])[:40], n_exposed=len(exposed), exposed_mm=round(ex_mm, 1),
                on_fill_mm_all=round(on_mm, 1), travel_mm=round(float(wt.sum()), 1), travel_segs=int(is_tr.sum()),
                covered_mm2=round(cov_mm2, 1), per_100cm2=round(ex_mm / (cov_mm2 / 1e4), 1),
                n_per_100cm2=round(len(exposed) / (cov_mm2 / 1e4), 1), target_exposed=P["target_exposed"], params=P,
                ok=len(exposed) <= P["target_exposed"])


def travel_segment_index(dst_segs, dst_labels, blocks_by_part, tol=0.16):
    """indices of labelled file segments that come from planned role "travel" blocks: the block's consecutive points,
    matched on the 0.1 mm grid (within tol) to file segments carrying the same part id"""
    want = {}
    for pid, bl in blocks_by_part.items():
        for b in bl:
            role = b.role if hasattr(b, "role") else b.get("role")
            pts = b.pts if hasattr(b, "pts") else b.get("pts")
            if role != "travel": continue
            for a, c in zip(pts[:-1], pts[1:]):
                want.setdefault(pid, set()).add((round(a[0], 1), round(a[1], 1), round(c[0], 1), round(c[1], 1)))
    out = []
    for i, (s, l) in enumerate(zip(dst_segs, dst_labels)):
        if l in want and (round(s[0], 1), round(s[1], 1), round(s[2], 1), round(s[3], 1)) in want[l]: out.append(i)
    return out


def plan_stack_area(parts, k=3, line_stypes=("run", "bean"), stype=None):
    """INDEPENDENT side for proving part_stack: area (mm2) of plan geometry covered by >= k fill parts (exact shapely,
    no stitches), from the part outlines the plan sews. stype(part) -> stitch type (default sequence._stype)."""
    from shapely.strtree import STRtree
    from shapely.ops import unary_union
    from digitize import sequence as SQ
    st = stype or SQ._stype
    lay = [SQ.clean(p.geom) for p in parts if st(p) not in line_stypes]
    lay = [g for g in lay if not g.is_empty]
    if not lay: return 0.0
    tree = STRtree(lay); pieces = []
    for i, g in enumerate(lay):
        nb = [lay[int(j)] for j in tree.query(g, predicate="intersects") if int(j) != i]
        nb = [o for o in nb if g.intersection(o).area > 1e-3]
        if len(nb) < k - 1: continue
        o = SQ._over_k(g, nb, k - 1)
        if o is not None and not o.is_empty: pieces.append(o)
    return float(unary_union(pieces).area) if pieces else 0.0


def run_hook(row, plan, segs, labels, bounds, cfg=None):
    """M4s gates for digitize.run: measure both on the labelled written file and store them in the row
    (row["stack_parts"], row["travel_on_fill"]); bench.verdict turns them into two NEW verdict lines next to the old 9.
    cfg: run.yaml `gates_m4s: {stack: {...}, travel: {...}}` (overrides of STACK_DEFAULTS / TRAVEL_DEFAULTS)."""
    from digitize import techniques
    cfg = cfg or {}
    line = [p.id for p in plan.parts if p.technique and techniques.get(p.technique).stype in ("run", "bean")]
    trs = travel_segment_index(segs, labels, plan.blocks)
    st = part_stack(segs, labels, bounds, line_parts=line, **cfg.get("stack", {}))
    tr = travel_on_fill(segs, labels, bounds, line_parts=line, travel_segs=trs, **cfg.get("travel", {}))
    row["stack_parts"] = {k: v for k, v in st.items() if k != "grid"}
    row["travel_on_fill"] = dict(tr, planned_travel_segs=len(trs))
    return row


def verdict_lines(row, T):
    """the two NEW verdict lines (M4s) for bench.verdict; {} on a row without them (older rows keep their 8 / 9 lines).
    Targets: bench.json targets stack_parts_per_100cm2_max / travel_on_fill_exposed_max (else the module defaults)."""
    out = {}
    if "stack_parts" in row:
        cap = T.get("stack_parts_per_100cm2_max", STACK_DEFAULTS["cap_per_100cm2"])
        out["stack_parts"] = row["stack_parts"]["per_100cm2"] <= cap
    if "travel_on_fill" in row:
        out["travel_on_fill"] = row["travel_on_fill"]["n_exposed"] <= T.get("travel_on_fill_exposed_max", TRAVEL_DEFAULTS["target_exposed"])
    return out


OLD_GATES = ("direction_ok", "direction_chaos", "angle_coherence", "density", "trims", "satin_shape", "stack", "colours", "separation")


def summary(verdict):
    """'x/11 (old 9: y/9)': the new total and the old 9 lines alone, so numbers stay comparable with earlier rows"""
    old = [k for k in OLD_GATES if k in verdict]
    return f"{sum(verdict.values())}/{len(verdict)} (old {len(old)}: {sum(verdict[k] for k in old)}/{len(old)})"
