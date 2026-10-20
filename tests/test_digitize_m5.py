"""ENGINE_PLAN M5: SVG parity on Konpeito. Each guard was proven RED by a mutation of the code it guards (listed in
RECAP-2026-10-20-engine-m5-svg.md) and is GREEN on this branch."""
import glob, math, os, tempfile
import numpy as np
import pytest
from shapely.geometry import box, LineString, Point
import qa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KJ = os.path.join(ROOT, "projects", "konpeito-jeans")
SVGS = sorted(glob.glob(os.path.join(KJ, "inputs", "svg", "*_ART.svg")))


# ------------------------------------------------------------------ svgart (konpeito ENGINE_NOTES 12)
def test_svg_parse_matches_cairosvg_per_layer():
    """every layer of every founder file: parsed geometry vs cairosvg's own rendering of that layer, IoU >= 0.98
    (the same renderer draws both, so the IoU measures the parser)."""
    import svgart
    assert len(SVGS) == 4
    for f in SVGS:
        ious = svgart.parse_iou(f, ppm=20)
        assert ious and min(ious.values()) >= 0.98, (os.path.basename(f), ious)


SYN = """<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="30mm" viewBox="0 0 40 30">
<g id="A_group" transform="translate(4 3) rotate(20 10 8)" fill="#C8162B">
  <path d="M2 2 h10 v6 h-10 z M4 4 l0 2 l6 0 l0 -2 z"/>
  <path d="M2 10 h10 v6 h-10 z M4 12 l6 0 l0 2 l-6 0 z"/>
  <path d="M15 2 q4 -2 8 0 t8 0 c0 4 -2 6 -4 6 s-4 -2 -4 -6 z" fill-rule="evenodd"/>
</g>
<g id="B_group" transform="matrix(0.9 0.1 -0.1 0.9 2 14)" style="fill:#1C1A1A">
  <rect x="1" y="1" width="12" height="8" rx="2"/><ellipse cx="22" cy="5" rx="5" ry="3" transform="rotate(30 22 5)"/>
  <polygon points="28,1 36,1 32,9"/>
</g></svg>"""


def test_svg_parser_transforms_relative_paths_and_holes():
    """group transforms (translate + rotate about a point, matrix), relative + smooth curves (q t c s, h v l), a
    nonzero hole drawn against the outer ring, style fills: parsed == rendered (IoU >= 0.98 per layer)"""
    import svgart
    d = tempfile.mkdtemp(); f = os.path.join(d, "syn.svg"); open(f, "w").write(SYN)
    Ls = svgart.layers(f)
    assert [L.id for L in Ls] == ["A_group", "B_group"] and Ls[1].fills() == ["#1C1A1A"]
    assert Ls[0].elements[0].geom.interiors                                     # nonzero: a ring wound against its outer ring is a hole
    assert not Ls[0].elements[1].geom.interiors                                 # ... and one wound the same way is not
    ious = svgart.parse_iou(f, ppm=20)
    assert min(ious.values()) >= 0.98, ious


def test_thread_of_exact_then_nearest():
    import svgart
    pal = {"red": "#C8162B", "black": "#1C1A1A"}
    assert svgart.thread_of("#c8162b", pal) == ("red", 0.0)
    k, dE = svgart.thread_of("#C9172C", pal); assert k == "red" and 0 < dE < 2


# ------------------------------------------------------------------ dst2.turning_satin (konpeito ENGINE_NOTES 2)
def test_turning_satin_skips_empty_perpendicular():
    """a C-shaped 0.8 mm stroke whose centreline overshoots the outline: perpendiculars past the ends miss the shape
    (an EMPTY LineString); main raised IndexError on sg.coords[0]."""
    import dst2
    arc = [(10 * math.cos(t), 10 * math.sin(t)) for t in np.linspace(math.radians(30), math.radians(330), 60)]
    p = LineString(arc).buffer(0.4, cap_style="flat")
    tan = lambda a, b: ((a[0] - b[0]), (a[1] - b[1]))
    t0 = tan(arc[0], arc[1]); t1 = tan(arc[-1], arc[-2])
    cl = LineString([(arc[0][0] + 3 * t0[0] / math.hypot(*t0), arc[0][1] + 3 * t0[1] / math.hypot(*t0))] + arc +
                    [(arc[-1][0] + 3 * t1[0] / math.hypot(*t1), arc[-1][1] + 3 * t1[1] / math.hypot(*t1))])
    pts = dst2.turning_satin(p, cl, sp=0.3, pull=0.0)
    assert len(pts) > 100 and all(p.buffer(0.05).contains(Point(q)) for q in pts)
    # the C's other side catches most far perpendiculars; a straight 0.8 mm stroke with a 3 mm overshoot has
    # perpendiculars that miss everything: intersection = LINESTRING EMPTY (the crash on main)
    s = LineString([(0, 0), (10, 0)]).buffer(0.4, cap_style="flat")
    pts = dst2.turning_satin(s, LineString([(-3, 0), (13, 0)]), sp=0.3, pull=0.0)
    assert len(pts) > 50 and all(s.buffer(0.05).contains(Point(q)) for q in pts)


# ------------------------------------------------------------------ qa.motif_match near / out_stops (ENGINE_NOTES 3)
def _sq(shape, ppm, x0, y0, x1, y1):
    m = np.zeros(shape, bool); m[int(y0 * ppm):int(y1 * ppm), int(x0 * ppm):int(x1 * ppm)] = True; return m


def test_motif_match_touching_motifs_compare_their_own_stitches():
    """two 5 mm squares 0.2 mm apart, each stitched exactly by its own stop (thread spreads 0.1 mm, so the DST shapes
    merge). Default: each motif is compared with the merged blob (IoU ~0.5, fails). With out_stops (its own stop) +
    near_mm, each motif reads IoU >= 0.9."""
    from scipy import ndimage as ndi
    ppm = 20; sh = (200, 300)
    A = _sq(sh, ppm, 1, 2, 6, 7); B = _sq(sh, ppm, 6.2, 2, 11.2, 7)
    ref = A | B
    sA, sB = ndi.binary_dilation(A, iterations=2), ndi.binary_dilation(B, iterations=2)
    old = qa.motif_match(ref, sA | sB, ppm)
    assert len(old) == 2 and max(r["iou"] for r in old) < 0.6
    rows = qa.motif_match(A, {0: sA, 1: sB}, ppm, near_mm=1.5, out_stops=[0]) + qa.motif_match(B, {0: sA, 1: sB}, ppm, near_mm=1.5, out_stops=[1])
    assert len(rows) == 2 and all(r["iou"] >= 0.9 and r["ok"] for r in rows), rows
    same = qa.motif_match(ref, sA | sB, ppm, near_mm=0.15)                     # same-stop family: near alone separates them
    assert all(r["iou"] >= 0.85 for r in same), same


# ------------------------------------------------------------------ centreline gate (ENGINE_NOTES 4 + 8)
def _line(shape, ppm, y, w, x0=2.0, x1=28.0):
    m = np.zeros(shape, bool); yy = np.arange(shape[0])[:, None] / ppm + 0.5 / ppm
    xx = np.arange(shape[1])[None, :] / ppm
    return (np.abs(yy - y) <= w / 2) & (xx >= x0) & (xx <= x1)


def test_centreline_gate_thin_line_shift():
    """a 0.7 mm line: shifted 0.2 mm passes the centreline gate (and FAILS area IoU, which is why thin strokes are gated
    on centrelines); shifted 0.6 mm fails it."""
    ppm = 20; sh = (200, 600); ref = _line(sh, ppm, 5.0, 0.7)
    near = _line(sh, ppm, 5.2, 0.7); far = _line(sh, ppm, 5.6, 0.7)
    ok = qa.centreline_match(ref, near, ppm, near_mm=1.0); bad = qa.centreline_match(ref, far, ppm, near_mm=1.0)
    assert ok["ok"] and abs(ok["mean_d"] - 0.2) <= 0.06, ok
    assert not bad["ok"] and bad["mean_d"] > 0.5, bad
    iou = (ref & near).sum() / (ref | near).sum(); assert iou < 0.70            # area IoU would fail the good file
    wide = _line(sh, ppm, 5.0, 1.0)                                             # same centreline, 43 % wider: width fails
    assert not qa.centreline_match(ref, wide, ppm)["ok"]


# ------------------------------------------------------------------ column satin same-side density (ENGINE_NOTES 7)
def _plan_part(kind, geom, tech, meta, ang=0.0):
    from digitize.schema import Part, DirSpec
    from digitize.rulebook import Rulebook
    from digitize.svgrun import kind_params
    rb = Rulebook(); p = Part(id=f"t.{tech}", kind=kind, geom=geom, thread="t1", z=0, dir=DirSpec(ang), meta=meta)
    p.technique = tech; p.stitch = rb.stitch_spec(kind, tech); p.stitch.params.update(kind_params(rb, kind)); return p


def _write(blocks, geom, tmp):
    import dst2, readback
    r = dict(col="t1", geom=geom, st="satin", ang=0.0, grp="pool", part="x", blocks=blocks)
    pat, _ = dst2.make_pattern([r], [dict(col="t1", regions=[r])], (0.0, 0.0), builder=lambda r, e: r["blocks"], keep_order=True,
                               threads={"t1": dict(hex="#000000")})
    base = os.path.join(tmp, "c"); dst2.write(pat, base); return base


def test_column_same_side_density_on_the_file(tmp_path):
    """a 10 mm, 1.0 mm wide column at same_side 0.40 (40wt) and 0.28 (60wt): read back from the DST, the needle
    penetrations on ONE side are 0.40 / 0.28 mm apart (Rev A's 0.30 'spacing' sewed 0.60 same side)."""
    from digitize import techniques
    for wt, want in (("40wt", 0.40), ("60wt", 0.28)):
        cl = [(0.0, 0.0), (10.0, 0.0)]
        p = _plan_part("lettering", LineString(cl).buffer(0.5), "column_satin", dict(cl=cl, w=1.0, caps=("flat", "flat"), closed=False, thread_wt=wt))
        bl = techniques.get("column_satin").plan(p)
        assert [b.role for b in bl] == ["top"]                                  # 1.0 mm: no centre run
        base = _write([b.pts for b in bl], p.geom, str(tmp_path))
        pts = [(a[0], a[1]) for _, a, _ in qa.dst_stitches(base + ".dst")]
        side = sorted(x for x, y in pts if y > 0.3 and 0.5 < x < 9.5)
        gaps = np.diff(side); ss = float(np.median(gaps))
        assert abs(ss - want) <= 0.03, (wt, ss)


# ------------------------------------------------------------------ bead dots (ENGINE_NOTES 11 + 13)
def test_dot_needle_diameter_and_house_minimum():
    from digitize.techniques.dot import needle_d, bead_points
    assert needle_d(1.5) == (1.3, False)
    assert needle_d(1.1, 0.9) == (0.9, False)                                   # exactly at the knot minimum: not house-min
    assert needle_d(1.0) == (1.1, True)                                         # under the minimum: sewn at 1.1, REPORTED
    pts = bead_points([(0.0, 0.0, 1.3, 30.0)], 0.18)
    assert all(math.hypot(*q) <= 0.65 + 1e-6 for q in pts)
    rows = [(a, b) for a, b in zip(pts[5:], pts[6:]) if math.dist(a, b) > 0.6]  # the across-stitches: ONE angle (no fan)
    ang = [math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180 for a, b in rows]
    assert len(rows) >= 5 and max(ang) - min(ang) < 1.0, ang


# ------------------------------------------------------------------ exact-geometry travel (ENGINE_NOTES 9)
def _two_dots(gap):
    from digitize.techniques.dot import bead_points
    regs = []
    for i, x in enumerate((0.0, 1.3 + gap)):
        g = Point(x, 0).buffer(0.65)
        regs.append(dict(col="t1", geom=g, st="satin", ang=0.0, grp="pool", part=f"d{i}", blocks=[bead_points([(x, 0.0, 1.3, 30.0)])]))
    field = box(-3, -3, 6, 3)
    regs = [dict(col="t0", geom=field, st="tatami", ang=0.0, grp="pool", part="f", blocks=[[(-3, -2.9), (6, -2.9)]])] + regs
    return regs, [dict(col="t0", regions=regs[:1]), dict(col="t1", regions=regs[1:])]


def test_exact_travel_trims_floats_between_close_objects(tmp_path):
    """two 1.3 mm bead dots 1.1 mm apart on a field sewn earlier: the default router sews the move across the gap (a
    visible float, found on the waistband accent dots); exact_travel trims it, and qa.exposed_stitches (exact
    geometry, on the read-back DST) reports it on the default file and not on the exact one."""
    import dst2
    TH = {"t0": dict(hex="#FFFFFF"), "t1": dict(hex="#FF0000")}
    regs, stops = _two_dots(1.1); geo = [s["regions"][0]["geom"] if len(s["regions"]) == 1 else regs[1]["geom"].union(regs[2]["geom"]) for s in stops]
    out = {}
    for name, ex in (("default", None), ("exact", dict(halo=0.25, max_ex=0.3, unsewn_only=True))):
        pat, st = dst2.make_pattern(regs, stops, (0.0, 0.0), builder=lambda r, e: r["blocks"], keep_order=True, threads=TH, exact_travel=ex)
        base = os.path.join(str(tmp_path), name); dst2.write(pat, base)
        out[name] = (qa.exposed_stitches(base + ".dst", (0.0, 0.0), geo, halo=0.25, min_mm=0.5, min_ex=0.3), st)
    assert out["default"][0], "the default file should float across the gap (else this test proves nothing)"
    assert out["exact"][0] == [] and out["exact"][1]["exact_trims"] >= 1


def test_exposed_stitches_reads_the_file(tmp_path):
    import dst2
    regs = [dict(col="t1", geom=box(0, 0, 2, 2), st="satin", ang=0.0, grp="pool", part="a", blocks=[[(0.5, 1.0), (1.5, 1.0), (4.5, 1.0)]])]
    pat, _ = dst2.make_pattern(regs, [dict(col="t1", regions=regs)], (0.0, 0.0), builder=lambda r, e: r["blocks"], keep_order=True,
                               threads={"t1": dict(hex="#000000")})
    base = os.path.join(str(tmp_path), "e"); dst2.write(pat, base)
    ex = qa.exposed_stitches(base + ".dst", (0.0, 0.0), [regs[0]["geom"]], halo=0.25, min_mm=0.5, min_ex=0.3)
    assert len(ex) == 1 and abs(ex[0][3] - 2.25) < 0.15, ex
    assert qa.exposed_stitches(base + ".dst", (0.0, 0.0), [box(0, 0, 5, 2)], halo=0.25, min_mm=0.5, min_ex=0.3) == []


# ------------------------------------------------------------------ direction per object layer (ENGINE_NOTES 14)
def test_direction_match_per_object_layer():
    """one 8 mm tile: a 0 deg field (long stitches) with 90 deg lettering on top over part of it. The reference grain
    runs along x. All stitches together read chaotic / off; judged per object layer (groups) the tile is the field's
    and passes. Default (groups=None) unchanged."""
    ppm = 12; H = W = 96
    y = np.arange(H)[:, None] / ppm
    ref = np.repeat(128 + 100 * np.sin(2 * math.pi * y / 0.8), W, axis=1)
    segs, grp = [], []
    for k in range(18):                                    # field rows at 0 deg, across the whole tile
        yy = 0.2 + k * 0.42; segs.append((0.2, yy, 7.8, yy)); grp.append("field")
    for k in range(20):                                    # lettering column at 90 deg on top (sewn later)
        xx = 2.0 + k * 0.1; segs.append((xx, 1.0, xx, 4.5)); grp.append("letter")
    a = qa.direction_match(ref, ppm, segs, visible=False, min_stitches=5)
    b = qa.direction_match(ref, ppm, segs, visible=False, min_stitches=5, groups=grp)
    assert a["pct_ok"] == 0.0 and b["pct_ok"] == 100.0, (a, b)


# ------------------------------------------------------------------ extract/svg + svgrun end to end
def test_svg_extract_waistband_parts():
    """the waistband SVG -> 230 parts, every one with a DECLARED direction (source rule), a palette thread, the
    heat-cut edge marked last; one needle width per column layer = art width - 0.15 (floors per thread)."""
    from digitize import config
    from digitize.extract import svg as XS
    from digitize.rulebook import Rulebook
    cfg = config.load(os.path.join(KJ, "bench", "run_wb_svg.yaml"))
    parts, info = XS.extract(cfg, Rulebook())
    assert len(parts) == 230
    assert all(p.dir.source == "rule" for p in parts)
    assert {p.thread for p in parts} <= set(cfg["threads"]["palette"])
    assert [p.kind for p in parts if p.meta.get("last")] == ["patch_edge"]
    w = info["widths"]
    assert w["13_lettering_BLACK"]["w_needle"] == pytest.approx(w["13_lettering_BLACK"]["w_art"] - 0.15, abs=0.011)
    assert w["05_frame_RED"]["w_needle"] == 0.85                                # 40wt floor
    kinds = {}
    for p in parts: kinds[p.kind] = kinds.get(p.kind, 0) + 1
    assert kinds["floret"] == 20 and kinds["petal"] == 20 and kinds["knot"] == 24 and kinds["patch_band"] == 4


def test_svgrun_star_end_to_end(tmp_path):
    """the pink back-pocket star through every svgrun stage: a DST/PES, the same stitch count as the delivered file
    (281), and every gate passing on the file"""
    from digitize import svgrun
    r = svgrun.SvgRun(os.path.join(KJ, "bench", "run_starP_svg.yaml"), overrides={"out_dir": str(tmp_path)})
    r.extract(); r.make_plan(); r.compile(); g = r.gates()
    assert os.path.exists(r.base + ".dst") and os.path.exists(r.base + ".pes")
    assert g["file"]["stitches"] == 281 and g["file"]["stops"] == 2 and g["all_pass"], g["gates"]


def test_run_dispatches_svg_source():
    import inspect
    from digitize import run
    assert 'get("source") == "svg"' in inspect.getsource(run.main)


def test_svg_coin_sequence_sews_each_colour_once(tmp_path):
    """coin patch: paint order binds only overlapping shapes, and a thread whose remaining parts wait on no other
    thread is sewn whole: one white stop for border motifs + specks (M1's deepest-first rule sewed the specks once per
    candy: 14 stops)"""
    from digitize import svgrun
    r = svgrun.SvgRun(os.path.join(KJ, "bench", "run_coin_svg.yaml"), overrides={"out_dir": str(tmp_path)})
    r.extract(); plan = r.make_plan()
    th = [s["thread"] for s in plan.stops]
    assert len(th) == 11 and th[-1] == "kj_red" and plan.stops[-1].get("last"), th
    body = th[:-1]; assert body.count("kj_white") == 1 and body.count("kj_red") == 2 and len(set(body)) == 9, th
