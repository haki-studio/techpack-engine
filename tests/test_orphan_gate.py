"""Orphan-fragment gate (digitize.gates_orphan, HANDOFF 'Engine follow-up already agreed'): a tiny block sewn in a
different stop from a bigger touching block of the same thread. Red on the KCOS Rev H FL M file (the founder's 8 spots,
21 Oct 2026), green on the Rev I file where the slivers sew with their letter. Synthetic cases hold each condition
(other stop, same thread, touching, tiny, much bigger) so a mutation of any one of them goes red."""
import os, sys, tempfile
import pytest
import pyembroidery as pe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from digitize import gates_orphan as GO

FIX = os.path.join(ROOT, "tests", "fixtures", "orphan")


def test_red_on_kcos_rev_h_fl_m():
    r = GO.orphan_fragments(os.path.join(FIX, "kcos_revH_FL_M.pes"))
    assert not r["ok"] and r["n"] == 8, r["hits"]
    # the founder's spots: EN badge slivers in the flat stops 7 / 8, after the foam letters (stops 3 / 4) they touch
    assert sorted(h["stop"] for h in r["hits"]) == [7] + [8] * 7
    assert all(h["sewn_after"] and h["big_stop"] in (3, 4) for h in r["hits"])


def test_red_on_kcos_rev_h_fr_m():
    r = GO.orphan_fragments(os.path.join(FIX, "kcos_revH_FR_M.pes"))
    assert not r["ok"] and r["n"] == 21


def test_green_on_kcos_rev_i_fl_m():
    r = GO.orphan_fragments(os.path.join(FIX, "kcos_revI_FL_M.pes"))
    assert r["ok"] and r["n"] == 0 and r["blocks"] > 200        # it saw the whole file, not an empty read


def write_pes(stops):
    """stops: [(hex, [[(x, y) mm, ...] block, ...]), ...] -> a PES path; blocks inside a stop are separated by a trim"""
    p = pe.EmbPattern()
    for i, (hx, blks) in enumerate(stops):
        if i: p.add_command(pe.COLOR_CHANGE)
        p.add_thread(pe.EmbThread(hx))
        for b in blks:
            p.add_stitch_absolute(pe.JUMP, b[0][0] * 10, b[0][1] * 10)
            for x, y in b: p.add_stitch_absolute(pe.STITCH, x * 10, y * 10)
            p.add_command(pe.TRIM)
    p.add_command(pe.END)
    path = os.path.join(tempfile.mkdtemp(), "o.pes"); pe.write_pes(p, path); return path


def rows(x0, x1, y0, y1, step=0.4):
    """a zig-zag fill block over the box"""
    pts, y, k = [], y0, 0
    while y <= y1 + 1e-9:
        pts += [(x0, y), (x1, y)] if k % 2 == 0 else [(x1, y), (x0, y)]; y += step; k += 1
    return pts

BIG = rows(0, 20, 0, 10)                          # 52 stitches, the letter
SLIVER = rows(20.1, 22, 2, 4)                     # 12 stitches, 1.9 x 2 mm, touching the letter's right edge
OTHER = rows(50, 60, 0, 5)                        # a stop of another thread between: the PES writer merges two consecutive
                                                  # stops of one thread into one, so a real orphan always has one between


def test_synthetic_red_sliver_in_a_later_stop():
    r = GO.orphan_fragments(write_pes([("#ff0000", [BIG]), ("#00ff00", [OTHER]), ("#ff0000", [SLIVER])]))
    assert r["n"] == 1 and r["hits"][0]["stop"] == 3 and r["hits"][0]["big_stop"] == 1 and r["hits"][0]["sewn_after"]


def test_synthetic_red_sliver_sewn_before_its_block():
    r = GO.orphan_fragments(write_pes([("#ff0000", [SLIVER]), ("#00ff00", [OTHER]), ("#ff0000", [BIG])]))
    assert r["n"] == 1 and not r["hits"][0]["sewn_after"]


@pytest.mark.parametrize("case", ["same_stop", "other_thread", "gap_1mm", "not_tiny", "not_bigger", "dense_small"])
def test_synthetic_green(case):
    stops = {
        "same_stop": [("#ff0000", [BIG, SLIVER])],                                   # sewn with its block: the fix
        "other_thread": [("#ff0000", [BIG]), ("#0000ff", [SLIVER])],                 # a different colour is a detail
        "gap_1mm": [("#ff0000", [BIG]), ("#00ff00", [OTHER]), ("#ff0000", [rows(21, 23, 2, 4)])],          # not touching
        "not_tiny": [("#ff0000", [rows(0, 40, 0, 30)]), ("#00ff00", [OTHER]), ("#ff0000", [rows(40.1, 49, 0, 3)])],   # 9 mm: a shape, not a sliver
        "not_bigger": [("#ff0000", [rows(0, 3, 0, 4)]), ("#00ff00", [OTHER]), ("#ff0000", [rows(3.1, 5, 0, 4)])],      # siblings, neither the body
        "dense_small": [("#ff0000", [rows(0, 40, 0, 30, 0.1)]), ("#00ff00", [OTHER]), ("#ff0000", [rows(40.1, 47, 0, 7, 0.1)])],  # 142 st: a motif
    }[case]
    r = GO.orphan_fragments(write_pes(stops))
    assert r["ok"] and r["n"] == 0, (case, r["hits"])


def test_exempt_hook_moves_hits_out_of_the_count():
    f = write_pes([("#ff0000", [BIG]), ("#00ff00", [OTHER]), ("#ff0000", [SLIVER])])
    r = GO.orphan_fragments(f, exempt=lambda h: "test reason" if h["stop"] == 3 else None)
    assert r["ok"] and r["n"] == 0 and r["n_exempt"] == 1 and r["exempt"][0]["exempt"] == "test reason"


def test_a_file_with_no_threads_or_no_stitches_cannot_pass():
    p = pe.EmbPattern(); p.add_stitch_absolute(pe.STITCH, 0, 0); p.add_stitch_absolute(pe.STITCH, 10, 0); p.add_command(pe.END)
    d = os.path.join(tempfile.mkdtemp(), "o.dst"); pe.write_dst(p, d)
    with pytest.raises(ValueError, match="thread"): GO.orphan_fragments(d)          # a DST carries no thread list
    assert GO.orphan_fragments(d, colours=["#ff0000"])["ok"]
    e = pe.EmbPattern(); e.add_thread(pe.EmbThread("#ff0000")); e.add_command(pe.END)
    f = os.path.join(tempfile.mkdtemp(), "e.pes"); pe.write_pes(e, f)
    with pytest.raises(ValueError): GO.orphan_fragments(f)


# --- ratchet (lead 22 Oct 2026): 0-products block on any orphan, the rest may not exceed their committed baseline
def test_ratchet_red_above_baseline_green_when_restored():
    base = {"products": {"wave": 100}}
    assert GO.ratchet({"wave": 100}, base)["ok"]
    over = GO.ratchet({"wave": 101}, base)
    assert not over["ok"] and over["rows"]["wave"]["status"] == "over" and over["rows"]["wave"]["below"] == -1
    assert GO.ratchet({"wave": 100}, base)["ok"]
    low = GO.ratchet({"wave": 60}, base)
    assert low["ok"] and low["rows"]["wave"]["status"] == "lower" and low["rows"]["wave"]["below"] == 40


def test_ratchet_zero_products_and_unknown_products_block_on_one_orphan():
    base = {"products": {"wave": 100, "comet-city-hoodie": 0}}
    for s in ("comet-city-hoodie", "a-new-product"):
        r = GO.ratchet({s: 1, "wave": 0}, base)
        assert not r["ok"] and r["rows"][s]["status"] == "block"
        assert GO.ratchet({s: 0, "wave": 0}, base)["ok"]


def test_update_baseline_only_lowers():
    b = GO.lowered({"products": {"wave": 100, "koi": 50}}, {"wave": 120, "koi": 10, "new": 5})
    assert b["products"] == {"wave": 100, "koi": 10}


def test_committed_baseline_holds_the_zero_products_at_zero():
    b = GO.load_baseline()
    for s in ("comet-city-hoodie", "red-beast-hoodie", "keep-clean-our-space-hoodie"):
        assert b["products"].get(s, 0) == 0
    assert all(isinstance(v, int) and v >= 0 for v in b["products"].values())


def test_production_file_selection():
    for rel, ok in [("01_wave/M/X.pes", True), ("01_wave/M/splits/X_S1.pes", True), ("stitch/M/X.pes", True),
                    ("pkg/elements/01/M/X.pes", False), ("pkg_sampling/elements/X.pes", False), ("old_revH_stitch/M/X.pes", False),
                    ("_wip/X.pes", False), ("_r3_backup/X.pes", False), ("stitch_RevA_backup/X.pes", False),
                    ("before_seamfill/M/X.pes", False), ("gate_cal/s0.pes", False), ("digitize/BK/BK.pes", False),
                    ("engine_m5/wb/X.pes", False), ("_revB_superseded/X.pes", False)]:
        assert GO._production(rel) == ok, rel


def test_product_files_falls_back_to_the_package_when_it_is_all_there_is(tmp_path):
    for rel in ("projects/a/out/01/M/A.pes", "projects/a/out/pkg/elements/01/M/A.pes", "projects/b/out/pkg/elements/01/M/B.PES",
                "projects/b/out/pkg/elements/_wip/W.pes"):
        p = tmp_path / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"")
    f = GO.product_files(str(tmp_path))
    assert [os.path.basename(x) for x in f["a"]] == ["A.pes"] and "pkg" not in f["a"][0]
    assert [os.path.basename(x) for x in f["b"]] == ["B.PES"]          # moon: only its package copy exists; case-blind


def _cli(root, *args):
    import subprocess
    return subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "orphan_fragments.py"), "--root", str(root), "--products", *args],
                          capture_output=True, text=True)


def test_cli_prod_gate_end_to_end(tmp_path):
    """the thin CLI on a products tree: KCOS (held to 0) red on Rev H, green on Rev I; a ratcheted product red above its
    baseline, green at it, and --update-baseline lowers it"""
    import json, shutil
    d = tmp_path / "projects" / "keep-clean-our-space-hoodie" / "out" / "stitch" / "M"; d.mkdir(parents=True)
    shutil.copy(os.path.join(FIX, "kcos_revH_FL_M.pes"), d / "HAKI_KCOS_FL_M.pes")
    bl = tmp_path / "baseline.json"; bl.write_text(json.dumps({"products": {"keep-clean-our-space-hoodie": 0}}))
    r = _cli(tmp_path, "--baseline", str(bl)); assert r.returncode == 1 and "FAIL (held to 0)" in r.stdout, r.stdout
    shutil.copy(os.path.join(FIX, "kcos_revI_FL_M.pes"), d / "HAKI_KCOS_FL_M.pes")
    r = _cli(tmp_path, "--baseline", str(bl)); assert r.returncode == 0 and "ORPHAN GATE PASS" in r.stdout, r.stdout
    # the same product under a baseline of 8: Rev H (8) passes at the limit, FR (21) added on top goes over
    shutil.copy(os.path.join(FIX, "kcos_revH_FL_M.pes"), d / "HAKI_KCOS_FL_M.pes")
    bl.write_text(json.dumps({"products": {"keep-clean-our-space-hoodie": 8}}))
    assert _cli(tmp_path, "--baseline", str(bl)).returncode == 0
    shutil.copy(os.path.join(FIX, "kcos_revH_FR_M.pes"), d / "HAKI_KCOS_FR_M.pes")
    r = _cli(tmp_path, "--baseline", str(bl)); assert r.returncode == 1 and "21 over the baseline" in r.stdout, r.stdout
    os.remove(d / "HAKI_KCOS_FR_M.pes")
    assert _cli(tmp_path, "--baseline", str(bl)).returncode == 0
    shutil.copy(os.path.join(FIX, "kcos_revI_FL_M.pes"), d / "HAKI_KCOS_FL_M.pes")
    r = _cli(tmp_path, "--baseline", str(bl), "--update-baseline"); assert r.returncode == 0 and "8 below the baseline" in r.stdout
    assert json.loads(bl.read_text())["products"]["keep-clean-our-space-hoodie"] == 0


def test_a_trim_alone_ends_a_block(monkeypatch):
    """a trim with no jump after it (possible in a DST) still splits the stop into two blocks"""
    p = pe.EmbPattern(); p.add_thread(pe.EmbThread("#ff0000"))
    for x in (0, 1, 2): p.add_stitch_absolute(pe.STITCH, x * 10, 0)
    p.add_stitch_absolute(pe.TRIM, 20, 0)
    for x in (3, 4): p.add_stitch_absolute(pe.STITCH, x * 10, 0)
    p.add_stitch_absolute(pe.END, 40, 0)
    monkeypatch.setattr(GO.pe, "read", lambda path: p)
    assert [len(b[2]) for b in GO.blocks("mem")] == [3, 2]


def test_unjudged_products_are_refused():
    base = {"products": {"comet-city-hoodie": 0, "wave": 10}}
    assert GO.unjudged({"comet-city-hoodie": 84, "wave": 3}, base) == []
    assert GO.unjudged({"comet-city-hoodie": 0, "wave": 3}, base) == ["comet-city-hoodie"]       # emptied out/
    assert GO.unjudged({"wave": 3}, base) == ["comet-city-hoodie"]                               # wrong root / no folder
    assert GO.unjudged({"drum-island": 0, "comet-city-hoodie": 1, "wave": 1}, base) == []        # pattern-only, not asked
    assert GO.unjudged({}, {"products": {}}, ["no-such-product"]) == ["no-such-product"]         # typo'd slug


def test_cli_exits_2_when_it_judged_nothing(tmp_path):
    """review PR #39: a held-to-0 product with no files, a typo'd slug or a wrong --root must not read PASS"""
    import json
    bl = tmp_path / "baseline.json"; bl.write_text(json.dumps({"products": {"comet-city-hoodie": 0}}))
    (tmp_path / "projects" / "comet-city-hoodie" / "out").mkdir(parents=True)                    # out/ with no PES
    r = _cli(tmp_path, "--baseline", str(bl)); assert r.returncode == 2 and "saw nothing" in r.stdout, r.stdout
    assert "ORPHAN GATE UNJUDGED" in r.stdout and "PASS" not in r.stdout, r.stdout                # exit 2 must not print PASS
    r = _cli(tmp_path, "--baseline", str(bl), "no-such-product"); assert r.returncode == 2 and "PASS" not in r.stdout, r.stdout
    r = _cli(tmp_path / "nowhere", "--baseline", str(bl)); assert r.returncode == 2, r.stdout + r.stderr
    r = _cli(tmp_path, "--baseline", str(bl), "--update-baseline")
    assert r.returncode == 2 and "NOT updated" in r.stdout and json.loads(bl.read_text())["products"] == {"comet-city-hoodie": 0}
