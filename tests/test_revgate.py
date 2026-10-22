"""Rev-log <-> chart / callout agreement gate (engine/revgate.py). Was a TD pack-checklist item; now deterministic."""
import copy, os, tempfile
import pytest
import yaml
from family.spec import Spec, SpecError
from family.build import rev_gate, build
import revgate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAM = os.path.join(ROOT, "families", "tee")
ALA = os.path.join(FAM, "variants", "alabasta.yaml")


def fam_raw(): return yaml.safe_load(open(os.path.join(FAM, "family.yaml")))
def var_raw(): return yaml.safe_load(open(ALA))


def spec_with(fam=None, var=None):
    d = tempfile.mkdtemp()
    yaml.safe_dump(fam or fam_raw(), open(os.path.join(d, "family.yaml"), "w"), allow_unicode=True)
    vp = os.path.join(d, "v.yaml"); v = var or var_raw()
    v["decorations"] = [dict(x, artwork=dict(x["artwork"], file=os.path.join(FAM, "variants", x["artwork"]["file"])))
                        if isinstance(x.get("artwork"), dict) and x["artwork"].get("file") else x for x in v["decorations"]]
    yaml.safe_dump(v, open(vp, "w"), allow_unicode=True)
    return Spec(d, vp)


def fails(sp):
    with pytest.raises(SpecError) as e: rev_gate(sp)
    return str(e.value)


def test_real_packs_pass_and_report_what_they_checked():
    for v in ("alabasta", "from-the-shadows"):
        reps = rev_gate(Spec(FAM, os.path.join(FAM, "variants", f"{v}.yaml")))
        assert all(r.ok for r in reps)
        assert reps[0].entries == 1 and reps[0].values == 16      # 4 'to' values + 2 'by' x 6 sizes


def test_R1_current_rev_must_be_the_newest_entry():
    v = var_raw(); v["rev"] = "Rev B"
    assert "the pack says Rev B but the newest rev-log entry is Rev A" in fails(spec_with(var=v))
    v = var_raw(); v["revisions"] = v["revisions"] + [dict(v["revisions"][0])]
    assert "rev 'Rev A' is logged twice" in fails(spec_with(var=v))
    v = var_raw(); v["revisions"] = []
    assert "R1 the rev log is empty" in fails(spec_with(var=v))
    v = var_raw(); v["revisions"][0].pop("date")
    assert "missing 'date'" in fails(spec_with(var=v))


def test_R2_logged_value_must_match_the_chart():
    f = fam_raw(); f["pom_chart"]["deltas"]["changes"]["A"]["to"] = "26 1/2"     # chart edited, log not
    msg = fails(spec_with(fam=f))
    assert "log says A Body length = 27 in at L; the chart prints 26 1/2" in msg
    f = fam_raw(); f["revisions"][0]["pom_changes"][3]["by"] = -2                # G by -1.5 cm on the chart
    assert "log says G Bicep -2 cm (Rev A) on every size; the chart moved it -1.5 cm" in fails(spec_with(fam=f))


def test_R2_newest_statement_wins():
    f = fam_raw(); f["rev"] = "Rev B"
    f["revisions"] = f["revisions"] + [{"rev": "Rev B", "date": "22 Oct 2026", "change": "body length back to 27 1/2",
                                        "pom_changes": [{"pom": "A", "size": "L", "to": "27 1/2"}]}]
    assert "log says A Body length = 27 1/2 in at L; the chart prints 27" in fails(spec_with(fam=f))
    f["pom_chart"]["deltas"]["changes"]["A"]["to"] = "27 1/2"
    assert all(r.ok for r in rev_gate(spec_with(fam=f)))


def test_R3_chart_change_missing_from_the_log():
    f = fam_raw(); f["revisions"][0]["pom_changes"] = [c for c in f["revisions"][0]["pom_changes"] if c["pom"] != "H"]
    assert "R3 the chart callout 'H: Sleeve opening" in fails(spec_with(fam=f))


def test_R4_pattern_measurement_must_agree():
    sp = Spec(FAM, ALA)
    log = fam_raw()["revisions"]
    good = {"A": {s: sp.chart.mm("A", s) for s in sp.chart.sizes}}
    assert revgate.check(log, sp.chart, "Rev A", measured=good).ok
    bad = copy.deepcopy(good); bad["A"]["M"] += 12                                # 12 mm off, tol 1 cm
    rep = revgate.check(log, sp.chart, "Rev A", measured=bad)
    assert any(f.startswith("R4 A Body length M: pattern measures") for f in rep.failures)


def test_build_refuses_a_disagreeing_pack(tmp_path):
    f = fam_raw(); f["pom_chart"]["deltas"]["changes"]["F"]["to"] = "10"
    sp_dir = tempfile.mkdtemp(); yaml.safe_dump(f, open(os.path.join(sp_dir, "family.yaml"), "w"), allow_unicode=True)
    with pytest.raises(SpecError, match="log says F Armhole straight = 10 1/4"):
        build(ALA, out_root=str(tmp_path), png=False, family_dir=sp_dir)


def test_R1_page_prints_the_logged_chart_values():
    from family import tee_pages as TP
    sp = Spec(FAM, ALA)
    r1 = "".join(next(p for c, _, p in TP.pages(sp) if c == "R1"))
    assert "A Body length 27 in at L" in r1 and "G Bicep -1.5 cm every size" in r1


def test_every_variant_in_the_repo_passes_the_rev_gate():
    import glob
    vs = glob.glob(os.path.join(ROOT, "families", "*", "variants", "*.yaml"))
    assert len(vs) >= 2
    for v in vs:
        fam = os.path.dirname(os.path.dirname(v))
        assert all(r.ok for r in rev_gate(Spec(fam, v))), v


def test_repeated_by_changes_add_up():
    f = fam_raw(); f["rev"] = "Rev B"
    f["pom_chart"]["deltas"]["changes"]["G"]["by"] = -2.0                         # chart: -2 cm in total
    f["revisions"] = f["revisions"] + [{"rev": "Rev B", "date": "22 Oct 2026", "change": "bicep another -0.5 cm",
                                        "pom_changes": [{"pom": "G", "by": -0.5, "unit": "cm"}]}]
    assert all(r.ok for r in rev_gate(spec_with(fam=f)))                         # -1.5 (Rev A) + -0.5 (Rev B) = -2
    f["pom_chart"]["deltas"]["changes"]["G"]["by"] = -0.5                         # chart shows only the last step
    assert "log says G Bicep -1.5 cm (Rev A) + -0.5 cm (Rev B) on every size" in fails(spec_with(fam=f))
