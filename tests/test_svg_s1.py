"""ENGINE_PLAN S1: any SVG -> DST with NO run.yaml (engine/digitize/extract/svg_auto.py, scripts/svg2dst.py).
No Anthropic API calls. The CLI tests run the real engine on small fixtures (~10 s each)."""
import json, math, os, subprocess, sys
import numpy as np
import pytest
from shapely import affinity
from shapely.geometry import Point, Polygon, box

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures", "svg_s1")
CLI = os.path.join(ROOT, "scripts", "svg2dst.py")
sys.path.insert(0, os.path.join(ROOT, "services", "svg2dst"))

import qa, svgart  # noqa: E402
from digitize import config  # noqa: E402
from digitize.rulebook import Rulebook  # noqa: E402

# a true-size (mm) SVG with NO run.yaml palette: a navy bar, a red disc, a yellow dot, inside one named group
MM_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="24mm" viewBox="0 0 40 24"><g id="{gid}">'
          '<rect x="2" y="2" width="22" height="10" fill="#1b2a4a"/><circle cx="31" cy="12" r="6" fill="#e94f37"/>'
          '<circle cx="5" cy="20" r="0.45" fill="#f4d35e"/></g></svg>')


def cli(svg, out, width=60, answers=None):
    cmd = [sys.executable, CLI, "--svg", str(svg), "--width-mm", str(width), "--fabric", "twill", "--hoop", "300x300",
           "--out", str(out), "--name", "t", "--no-api"]
    if answers is not None:
        ap = os.path.join(str(out) + "_answers.json"); json.dump(answers, open(ap, "w")); cmd += ["--answers", ap]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    res = os.path.join(str(out), "result.json")
    return p.returncode, (json.load(open(res)) if os.path.exists(res) else None), p.stdout + p.stderr


def gate(res, gid): return {g["id"]: g for g in res["gates"]}[gid]


# ------------------------------------------------------------------ no config (red on main: KeyError 'palette')
def test_svg_with_no_palette_extracts(tmp_path):
    from digitize.extract import svg as XS
    (tmp_path / "a.svg").write_text(MM_SVG.format(gid="art"))
    (tmp_path / "run.yaml").write_text("name: t\nsource: svg\nout_dir: out\nproject: .\nsvg:\n  file: a.svg\n")
    cfg = config.load(str(tmp_path / "run.yaml"))
    rb = Rulebook(cfg.get("rules"), toggles=cfg["techniques"], overrides=cfg.get("rule_overrides"))
    parts, info = XS.extract(cfg, rb)
    assert len({p.thread for p in parts}) == 3 and len(cfg["threads"]["palette"]) == 3
    assert {p.thread for p in parts} <= set(cfg["threads"]["palette"])


# ------------------------------------------------------------------ geometry only: layer names never read
def test_layer_ids_renamed_same_decisions(tmp_path):
    from digitize.extract import svg_auto
    got = []
    for gid in ("art", "zz_lettering_BLACK"):
        src = tmp_path / f"{gid}.svg"; src.write_text(MM_SVG.format(gid=gid))
        dst, _ = svg_auto.normalize(str(src), str(tmp_path / f"{gid}_n.svg"), 40.0)
        d = svg_auto.derive(dst)
        (spec,) = d["cfg"]["svg"]["layers"].values()
        got.append((spec.get("role"), json.dumps(spec.get("shapes"), sort_keys=True), sorted(d["cfg"]["threads"]["palette"].values())))
    assert got[0] == got[1]


# ------------------------------------------------------------------ classifier on synthetic shapes (mm)
@pytest.mark.parametrize("geom,want", [
    (Point(0, 0).buffer(0.4, quad_segs=32), ("knot",)),
    (Point(0, 0).buffer(1.0, quad_segs=32), ("dot",)),
    (box(0, 0, 30, 1.2), ("stroke",)),
    (box(0, 0, 25, 18), ("fill",)),
    (Polygon([(10 * math.cos(math.radians(90 + 36 * k)) * (1 if k % 2 == 0 else 0.4),
               10 * math.sin(math.radians(90 + 36 * k)) * (1 if k % 2 == 0 else 0.4)) for k in range(10)]), ("star",)),
])
def test_classifier(geom, want):
    from digitize.extract import svg_auto
    assert svg_auto.classify(svg_auto.features(geom))[0] in want


@pytest.mark.parametrize("deg", [0.0, 30.0, 75.0, 120.0])
def test_fill_angle_is_long_axis(deg):
    from digitize.extract import svg_auto
    assert svg_auto.long_axis(affinity.rotate(box(0, 0, 30, 10), deg, origin=(0, 0))) == pytest.approx(deg, abs=0.5)


# ------------------------------------------------------------------ threads
def test_isacord_match_is_unique_and_merges_near_twins():
    from digitize.extract import svg_auto
    book = {h for _, _, h in svg_auto._isacord()}
    exact = sorted(book)[5]
    m = svg_auto.match_threads([exact, "#1B2A4A", "#1C2A4B", "#1B2B4D"])
    assert m[exact]["dE"] == 0.0 and m[exact]["merged_into"] is None
    assert m["#1C2A4B"]["merged_into"] == "#1B2A4A" and m["#1C2A4B"]["code"] == m["#1B2A4A"]["code"]
    codes = [v["code"] for f, v in m.items() if v["merged_into"] is None]
    assert len(codes) == len(set(codes))                                  # two fills never share a thread unless merged


# ------------------------------------------------------------------ parser + normalize
@pytest.mark.parametrize("name", ["logo_badge", "lettering_haki", "illustration_wave"])
def test_parser_reads_everything_cairosvg_paints(name, tmp_path):
    """arcs, strokes -> outlines, <style> classes, px units, gradients: the parse matches the renderer"""
    from digitize.extract import svg_auto
    dst, info = svg_auto.normalize(os.path.join(FIX, name + ".svg"), str(tmp_path / "n.svg"), 80.0)
    assert info["art_mm"][0] == pytest.approx(80.0, abs=0.05)
    W, H, scale = svgart.size_mm(dst)
    assert scale == pytest.approx(1.0) and W == pytest.approx(82.0, abs=0.1)       # art + 1 mm margin each side
    assert svgart.art_read(dst) >= 0.98


def test_twill_is_identity():
    from digitize.extract import svg_auto
    from digitize.svgrun import apply_fabric
    from digitize.schema import StitchSpec
    fab = svg_auto.fabric_rules("twill")
    class P: pass
    for t in ("tatami", "column_satin", "radial"):
        p = P(); p.technique = t; p.kind = "x"; p.stitch = StitchSpec(technique=t)
        before = repr(p.stitch); apply_fabric(p, fab); assert repr(p.stitch) == before
    with pytest.raises(svg_auto.AutoError): svg_auto.fabric_rules("silk")


# ------------------------------------------------------------------ the per-shape thick-end gate (prove-the-guard)
def _crescent_masks(ppm=20):
    """a tapered crescent (belly ~3.7 mm) and the same centreline sewn at ONE width (its median): the 2026-10-22 defect"""
    from digitize.techniques import column as C
    a = Point(20, 20).buffer(9, quad_segs=64); b = Point(25.6, 20).buffer(10.6, quad_segs=64); cres = a.difference(b)
    st = C.glyph_columns(cres, ppm=40.0)[0]
    one = C.column_geom(st["cl"], st["w"], st["caps"], False)
    from shapely import contains_xy
    yy, xx = np.mgrid[0:40 * ppm, 0:40 * ppm]
    m = lambda g: contains_xy(g, (xx + 0.5) / ppm, (yy + 0.5) / ppm)
    return m(cres), m(one), m(cres)


def test_centreline_gate_fails_a_tapered_shape_sewn_at_one_width():
    ref, one_width, faithful = _crescent_masks()
    pooled = qa.centreline_match(ref, one_width, 20)                     # the old row: median width only
    per_shape = qa.centreline_match(ref, one_width, 20, profile=True)
    assert pooled["ok"] is True                                          # why the defect passed
    assert per_shape["tapered"] is True and per_shape["ok"] is False and per_shape["ratio90"] < 0.8
    assert qa.centreline_match(ref, faithful, 20, profile=True)["ok"] is True


def test_even_stroke_is_not_gated_on_its_thick_end():
    ppm = 20; yy, xx = np.mgrid[0:200, 0:600]
    ref = (yy >= 90) & (yy < 106)                                        # 0.8 mm bar
    out = ref.copy(); out[80:120, 290:310] = True                       # a junction blob in the stitches
    r = qa.centreline_match(ref, out, ppm, profile=True)
    assert r["tapered"] is False and r["ok"] is True


# ------------------------------------------------------------------ the CLI (real engine)
@pytest.fixture(scope="module")
def logo(tmp_path_factory):
    out = tmp_path_factory.mktemp("logo") / "out"
    return out, cli(os.path.join(FIX, "logo_badge.svg"), out)


def test_cli_logo_contract_and_per_shape_rows(logo):
    from contract import check_result
    out, (rc, res, log) = logo
    assert rc == 0, log
    check_result(res)
    assert gate(res, "engine_real")["pass"] and gate(res, "art_read")["pass"] and gate(res, "exposed_none")["pass"]
    rows = json.load(open(out / "gates.json"))["centreline"]
    assert len(rows) == 3 and all(r["ok"] for r in rows), rows          # ring, crescent, bar: one row each
    cres = [r for r in rows if r.get("tapered")]
    assert len(cres) == 1 and abs(cres[0]["ratio90"] - 1) <= 0.2
    parts = json.load(open(out / "parts.json"))["parts"]
    assert any(p.get("meta", {}).get("prof") for p in parts)            # the crescent sews on a width profile


def test_cli_question_answer_round_trip(logo, tmp_path):
    _, (_, res, _) = logo
    assert res["questions"]
    q = res["questions"][0]; other = [o for o in q["options"] if o != q["default"]][0]
    rc, r2, log = cli(os.path.join(FIX, "logo_badge.svg"), tmp_path / "a", answers={q["id"]: other})
    assert rc == 0, log
    assert q["id"] not in [x["id"] for x in r2["questions"]]
    rc, _, log = cli(os.path.join(FIX, "logo_badge.svg"), tmp_path / "b", answers={q["id"]: "not-an-option"})
    assert rc == 2 and "not one of" in log


def test_cli_more_than_12_colours_is_a_gate_fail_not_a_crash(tmp_path):
    cols = ["#%02x%02x%02x" % (40 + 13 * k, 200 - 11 * k, (70 * k) % 255) for k in range(14)]
    body = "".join(f'<rect x="{2 + (k % 7) * 14}" y="{2 + (k // 7) * 14}" width="12" height="12" fill="{c}"/>' for k, c in enumerate(cols))
    (tmp_path / "many.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 30">{body}</svg>')
    rc, res, log = cli(tmp_path / "many.svg", tmp_path / "o", width=100)
    assert rc == 0, log
    assert gate(res, "threads_le_needles")["pass"] is False and res["ok"] is False
