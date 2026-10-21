"""Pro reference profiler (engine/proprofile.py, docs/PRO_REFERENCE.md): the stitch classifier on synthetic satin /
fill / run / bean / underlay built with the engine's own generators, and the per-area maths on a known square.
No pro files are needed (they are licensed and never in git); no Anthropic API calls."""
import json
import math
import os

import numpy as np
from shapely.geometry import LineString, Point, box

import dst2
import proprofile as PP


def _design(*blocks):
    """blocks of runs (lists of (x, y) mm) -> a design dict like proprofile.load returns"""
    return dict(blocks=[[np.asarray(r, float) for r in b] for b in blocks], colours=[])


def _quantise(pts):
    """DST resolution: 0.1 mm (the pro files and ours are read at this grid)"""
    return [(round(x, 1), round(y, 1)) for x, y in pts]


def _tatami(poly, ang=0.0, sp=0.45, L=3.5):
    rows = dst2.tatami_rows(poly, ang, sp, L)
    pts = []
    for r in rows: pts += r
    return _quantise(pts)


def _classes(design):
    objs, G = PP.analyse(design)
    out = {}
    for o in objs: out[o["cls"]] = out.get(o["cls"], 0) + o["stitches"]
    return objs, out


def _main(objs, cls):
    c = [o for o in objs if o["cls"] == cls]
    return max(c, key=lambda o: o["stitches"]) if c else None


# ------------------------------------------------------------------ classifier
def test_fill_is_fill_with_its_spacing_and_stitch_length():
    objs, share = _classes(_design([_tatami(box(0, 0, 30, 20), ang=0.0, sp=0.45, L=3.5)]))
    total = sum(share.values())
    assert share.get("fill", 0) / total > 0.9, share
    f = _main(objs, "fill")
    assert abs(f["spacing"] - 0.45) < 0.06, f["spacing"]
    assert abs(f["stitch_len"] - 3.5) < 0.6, f["stitch_len"]
    assert not f["open"]


def test_dense_pro_tatami_reads_its_own_spacing():
    """the pro files measure 0.20-0.25 mm rows; the classifier must read a 0.20 mm tatami as a dense fill at 0.20 mm
    (not halve or double it, not call it satin), with ~2.2x the thread per area of a 0.45 mm house fill"""
    sq = box(0, 0, 20, 20)
    objs, share = _classes(_design([_tatami(sq, ang=0.0, sp=0.20, L=2.6)]))
    assert share.get("fill", 0) / sum(share.values()) > 0.9, share
    f = _main(objs, "fill")
    assert abs(f["spacing"] - 0.20) < 0.03 and not f["open"], f["spacing"]
    dense, _, _, _ = PP.profile_design(_design([_tatami(sq, 0.0, sp=0.20, L=2.6)]))
    house, _, _, _ = PP.profile_design(_design([_tatami(sq, 0.0, sp=0.45, L=2.6)]))
    r = dense["decomposition"]["rho_thread_per_layer_mm2"] / house["decomposition"]["rho_thread_per_layer_mm2"]
    assert 1.9 < r < 2.5, r


def test_pes_source_reads_the_design_file_name(tmp_path):
    p = tmp_path / "x.PES"
    p.write_bytes(b"#PES0100\x00\x10\x00\x00A-0661 Drama Masks_M.EMB\x00Hoop SQ14 (140 x 140)\x00")
    assert PP.pes_source(str(p)) == "A-0661 Drama Masks_M.EMB"
    p.write_bytes(b"#PES0100\x00no design name here")
    assert PP.pes_source(str(p)) is None


def test_satin_is_satin_with_its_width():
    col = box(0, 0, 40, 3.0)                       # 3 mm column, satin across it (house spacing 0.42, pull 0.2)
    pts = _quantise(dst2.fixed_satin(col, 90.0, sp=0.42, pull=0.2))
    objs, share = _classes(_design([pts]))
    assert share.get("satin", 0) / sum(share.values()) > 0.9, share
    s = _main(objs, "satin")
    assert abs(s["width"] - 3.4) < 0.3, s["width"]   # 3.0 + 2 x 0.2 pull compensation
    assert abs(s["spacing"] - 0.42) < 0.06, s["spacing"]


def test_zigzag_satin_same_side_is_twice_the_step():
    # a true zig-zag (one penetration per side, no edge step): same-side spacing = 2 x the step (LESSONS B26)
    pts = [((i % 2) * 2.5, i * 0.2) for i in range(150)]
    objs, share = _classes(_design([pts]))
    s = _main(objs, "satin")
    assert s is not None and share["satin"] / sum(share.values()) > 0.9, share
    assert abs(s["spacing"] - 0.2) < 0.03 and abs(s["same_side"] - 0.4) < 0.06, (s["spacing"], s["same_side"])


def test_run_is_run():
    line = [(t, 6 * math.sin(t / 8.0)) for t in np.linspace(0, 80, 400)]
    pts = _quantise(dst2.run_path(line, 2.5))
    objs, share = _classes(_design([pts]))
    assert share == {"run": share.get("run", 0)} and share["run"] > 0, share
    L = np.hypot(*np.diff(np.asarray(pts, float), axis=0).T)
    assert abs(_main(objs, "run")["stitch_len"] - float(np.median(L[L > 0]))) < 0.05


def test_bean_on_a_curve_is_a_run_not_a_fill():
    # triple run (bean): forward, back, forward over each stitch. On a curve its passes are 0.1-0.2 mm apart, which
    # linked into a "fill" before the retrace test (pro mug lattice, 21 Oct 2026)
    base = _quantise(dst2.run_path([(t, 10 * math.sin(t / 6.0)) for t in np.linspace(0, 60, 300)], 2.0))
    pts = [base[0]]
    for a, b in zip(base, base[1:]): pts += [b, a, b]
    objs, share = _classes(_design([pts]))
    assert share.get("fill", 0) == 0 and share.get("satin", 0) == 0, share


def test_edge_run_under_its_fill_is_underlay():
    sq = box(0, 0, 25, 25)
    edge = []
    for r in dst2.edge_run(sq, inset=0.5, L=2.5): edge += r
    blk = [_quantise(edge), _tatami(sq, ang=30.0)]
    objs, share = _classes(_design(blk))
    assert share.get("underlay", 0) >= len(edge) - 2, share          # the whole edge run (bar ties) is underlay
    assert share.get("run", 0) <= 2, share
    # the same run sewn AFTER the fill is a visible run, not underlay
    objs, share = _classes(_design([_tatami(sq, ang=30.0), _quantise(edge)]))
    assert share.get("run", 0) >= len(edge) - 2, share
    assert share.get("underlay", 0) <= 0.01 * sum(share.values()), share   # only the fill's own turn bits


def test_lattice_underlay_with_side_steps_is_underlay():
    # open 2 mm lattice with 2 mm side-steps between rows (dst2 lattice underlay), then the top fill at 90 deg
    sq = box(0, 0, 20, 20)
    lat = _tatami(sq, ang=0.0, sp=2.0, L=3.5)
    objs, share = _classes(_design([lat, _tatami(sq, ang=90.0)]))
    u = [o for o in objs if o["cls"] == "underlay"]
    assert sum(o["stitches"] for o in u) >= 0.8 * (len(lat) - 1), share
    assert any(o.get("base_cls") == "fill" for o in u), [o.get("base_cls") for o in u]


# ------------------------------------------------------------------ per-area maths
def test_per_area_maths_on_a_known_square():
    sq = box(0, 0, 10, 10)                        # 1.00 cm2
    pts = _tatami(sq, ang=0.0, sp=0.45, L=3.5)
    m, objs, G, _ = PP.profile_design(_design([pts]))
    assert abs(m["covered_cm2"] - 1.0) < 0.1, m["covered_cm2"]
    P = np.asarray(pts, float); w, h = P.max(0) - P.min(0)
    assert abs(m["bbox_cm2"] - w * h / 100) < 0.01 and abs(m["bbox_cm2"] - 1.0) < 0.1, m["bbox_cm2"]
    assert m["stitches"] == len(pts) - 1
    assert abs(m["st_per_cm2_covered"] - 100 * m["stitches"] / (100 * m["covered_cm2"])) < 0.5
    dec = m["decomposition"]
    assert abs(dec["check"] - m["st_per_cm2_covered"]) < 0.5            # st/cm2 = 100 x D x rho / L (identity)
    assert abs(dec["D_mean_depth"] - 1.0) < 0.05                      # one layer
    assert abs(dec["rho_thread_per_layer_mm2"] - 1 / 0.45) < 0.35     # ~ 1 / row spacing
    assert m["depth_all"]["1"] > 0.95


def test_two_stacked_squares_are_two_layers_deep():
    sq = box(0, 0, 10, 10)
    one, _, _, _ = PP.profile_design(_design([_tatami(sq, 0.0)]))
    two, _, _, _ = PP.profile_design(_design([_tatami(sq, 0.0)], [_tatami(sq, 90.0)]))
    assert abs(two["covered_cm2"] - one["covered_cm2"]) < 0.1         # same area ...
    assert abs(two["decomposition"]["D_mean_depth"] - 2.0) < 0.1      # ... twice as deep
    assert two["depth_all"]["2"] > 0.9 and two["depth_top"]["2"] > 0.9
    assert 1.8 < two["st_per_cm2_covered"] / one["st_per_cm2_covered"] < 2.2


# ------------------------------------------------------------------ reference set + stats file
def test_allowlist_is_the_ten_pro_designs_only(tmp_path):
    assert len(PP.PRO_ALLOW) == 10 and len(set(PP.PRO_ALLOW)) == 10
    for n in ("A-0661 Drama Masks_M.DST", "A-0661 Drama Masks_M.PES", "Law.DST", "Chopper_M.DST", "X-1234 Other_M.DST"):
        (tmp_path / n).write_bytes(b"")
    found = PP.pro_files(str(tmp_path))
    assert [c for c, _, _ in found] == ["A-0661"], found       # Law.DST and anything not allow-listed is never read
    assert found[0][2].endswith(".PES")


def test_stats_json_is_derived_numbers_only():
    """the committed stats file holds numbers for the 10 allow-listed designs and no stitch data"""
    d = json.load(open(PP.STATS_JSON))
    assert sorted(d["pro"]) == sorted(PP.PRO_ALLOW)
    assert os.path.getsize(PP.STATS_JSON) < 200_000
    for m in d["pro"].values():
        assert "pts" not in m and "stitches" in m and m["st_per_cm2_covered"] > 0
    s = d["summary"]["stitches / cm2 covered"]
    assert s["p10"] <= s["median"] <= s["p90"]
