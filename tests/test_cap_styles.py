"""Hat styles (founder 2026-10-28): a hat submitted for tech packing must name a style from the catalogue
(families/cap/styles.yaml). The catalogue validates strictly, intake refuses a hat with no/unknown style before it
writes anything, and dispatch refuses to start a build for one. LESSONS H1."""
import copy, html, json, os, re, subprocess, sys
import pytest
import yaml
import capstyle as CS
import cap_pages as CP

ROOT = CS.ROOT
KEYS = ["asce-dad", "hi-structured", "trucker-snap", "sweet", "someday", "ripstop-6p", "bucket", "beanie-cuff",
        "haki-cord-5p"]


@pytest.fixture(scope="module")
def cat():
    return CS.load(refresh=True)


def raw():
    return (yaml.safe_load(open(os.path.join(CS.CAP_DIR, "styles.yaml"))),
            yaml.safe_load(open(os.path.join(CS.CAP_DIR, "family.yaml"))))


# ------------------------------------------------------------------ catalogue
def test_catalogue_has_the_nine_styles_and_they_validate(cat):
    assert cat.keys() == KEYS
    r, f = raw()
    assert CS.validate(r, f) == []


@pytest.mark.parametrize("garment", ["cap", "Dad hat", "trucker", "bucket hat", "beanie", "snapback", "caps", "Beanies",
                                     "hats", "snapbacks", "snap-back", "Snap back cap", "dad-hat", "Trucker Caps", "visor"])
def test_a_hat_with_no_style_is_refused_and_told_the_valid_keys(cat, garment):
    err = CS.check_choice(garment, None, cat)
    assert err and all(k in err for k in KEYS)


def test_an_unknown_style_is_refused_and_told_the_valid_keys(cat):
    err = CS.check_choice("cap", "dad-cap-v2", cat)
    assert err and "unknown hat style 'dad-cap-v2'" in err and all(k in err for k in KEYS)


def test_a_style_of_the_wrong_kind_is_refused(cat):
    assert "beanie-cuff" in CS.check_choice("beanie", "asce-dad", cat)
    assert "bucket" in CS.check_choice("bucket hat", "sweet", cat)
    assert CS.check_choice("beanie", "beanie-cuff", cat) is None
    assert CS.check_choice("cap", "asce-dad", cat) is None


@pytest.mark.parametrize("garment", ["t-shirt", "hoodie", "Crewneck sweatshirt", "socks", ""])
def test_a_non_hat_needs_no_style(cat, garment):
    assert CS.check_choice(garment, None, cat) is None


def _errs(mut):
    r, f = raw(); mut(r["styles"]); return CS.validate(r, f)


@pytest.mark.parametrize("name,mut,needle", [
    ("POM value without a source", lambda s: s["asce-dad"]["pom"]["A"].pop("source"), "value 58 has no source"),
    ("plain value", lambda s: s["asce-dad"]["pom"].__setitem__("A", 58), "plain value 58 has no source"),
    ("missing field", lambda s: s["sweet"].pop("crown_die"), "missing required field 'crown_die'"),
    ("unknown field", lambda s: s["sweet"].__setitem__("colourway", "red"), "unknown field 'colourway'"),
    ("unknown POM code", lambda s: s["sweet"]["pom"].__setitem__("Z", {"proposed": 1}), "pom.Z: not a POM of kind cap"),
    ("knit with cap POMs", lambda s: s["beanie-cuff"]["pom"].__setitem__("G", {"proposed": 2.5}), "pom.G: not a POM of kind knit"),
    ("value and proposed", lambda s: s["asce-dad"]["pom"]["A"].__setitem__("proposed", 57), "has both value and proposed"),
    ("bad panels", lambda s: s["sweet"].__setitem__("panels", {"value": 7, "source": "x"}), "5 or 6 crown panels"),
])
def test_validator_refuses(name, mut, needle):
    errs = _errs(mut)
    assert any(needle in e for e in errs), (name, errs)


def test_a_broken_catalogue_will_not_load(tmp_path):
    r, f = raw(); r["styles"]["sweet"].pop("crown_die")
    p = tmp_path / "styles.yaml"; p.write_text(yaml.safe_dump(r))
    with pytest.raises(CS.StyleError, match="crown_die"):
        CS.Catalogue(str(p))


def test_recorded_conflicts_stay_proposed(cat):
    assert cat.get("asce-dad").t["panels"].proposed            # ASCE 5 vs 6 panels
    assert cat.get("trucker-snap").pom["C"].proposed            # trucker back height 12.5 vs 16.2-16.8
    assert cat.get("ripstop-6p").t["panels"].proposed           # ripstop 6 panels


@pytest.mark.parametrize("product,style", [
    ("Easy Come, Easy Go Dad Hat", "asce-dad"), ("Fire Fist Dad Hat", "asce-dad"), ("Rain Dinners Dad Hat", "asce-dad"),
    ("Superrrr Dad Hat", "asce-dad"), ("Big News Dad Hat", "asce-dad"), ("Greed Island Dad Hat", "asce-dad"),
    ("Guardian Deity Dad Hat", "asce-dad"), ("Valentine Dad Hat", "asce-dad"), ("Dead or Alive Dad Hat", "asce-dad"),
    ("Tiger Dad Hat", "asce-dad"), ("Will of D Hat", "sweet"), ("You Wish Hat", "someday"),
    ("Rabbit Escape Hat", "ripstop-6p"), ("Shibuya Hat", "ripstop-6p"), ('Haki "Block" Hat', "haki-cord-5p"),
    ('Pink "Hearts" Beanie', "beanie-cuff"), ("Hat Box", None), ("Mystery Hat", None), ("Drum Island Tee", None),
])
def test_live_product_names_map_to_their_style(cat, product, style):
    assert CS.style_for_product(product, cat) == style


@pytest.mark.parametrize("key", KEYS)
def test_every_style_renders_and_lists_every_proposed_value_on_F1(cat, key):
    st = cat.get(key)
    codes = [c for c, _, _ in CP.pages(st)]
    assert ("K1" in codes and "H3" not in codes) if st.kind == "knit" else ("H3" in codes and "K1" not in codes)
    assert codes[0] == "H1" and "F1" in codes
    items = CP.open_items(st)
    assert len(items) == len(st.proposed()) > 0
    f1 = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)) for c, _, ss in CP.pages(st) if c == "F1" for s in ss)
    f1 = re.sub(r"\s+", " ", f1)
    missing = [lab for _, lab, _ in items if lab and re.sub(r"\s+", " ", lab)[:18] not in f1]
    assert not missing, missing


# ------------------------------------------------------------------ intake gate
def _intake(tmp_path, *args):
    e = dict(os.environ, TECHPACK_ROOT=str(tmp_path), TECHPACK_STATE=str(tmp_path / "state"))
    return subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "intake.py"), *args], capture_output=True,
                          text=True, env=e)


def _plan(tmp_path, **pr):
    (tmp_path / "inbox").mkdir(exist_ok=True)
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"products": [dict({"slug": "probe-cap", "name": "Probe Cap", "garment": "cap"}, **pr)]}))
    return str(p)


@pytest.mark.parametrize("cmd", ["plan", "apply"])
def test_intake_refuses_a_hat_with_no_style_and_writes_nothing(tmp_path, cmd):
    r = _intake(tmp_path, cmd, _plan(tmp_path))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "probe-cap" in r.stdout and all(k in r.stdout for k in KEYS)
    assert not (tmp_path / "projects").exists()


def test_intake_refuses_an_unknown_style(tmp_path):
    r = _intake(tmp_path, "apply", _plan(tmp_path, style="dad-cap-v2"))
    assert r.returncode == 1 and "unknown hat style 'dad-cap-v2'" in r.stdout
    assert not (tmp_path / "projects").exists()


def test_intake_records_the_style_in_status_and_brief(tmp_path):
    r = _intake(tmp_path, "apply", _plan(tmp_path, style="asce-dad"))
    assert r.returncode == 0, r.stdout + r.stderr
    P = tmp_path / "projects" / "probe-cap"
    s = json.loads((P / "STATUS.json").read_text())
    assert (s["garment"], s["style"]) == ("cap", "asce-dad")
    brief = (P / "inputs" / "brief.md").read_text()
    assert "- Hat style: asce-dad — ASCE dad cap (crown die SN508, brim die 202)" in brief
    assert CS.project_info("probe-cap", str(tmp_path)) == ("cap", "asce-dad")
    (P / "STATUS.json").unlink()                                    # the brief alone is enough for the build gate
    assert CS.project_info("probe-cap", str(tmp_path)) == ("cap", "asce-dad")


def test_intake_plan_prints_the_style_and_a_tee_needs_none(tmp_path):
    r = _intake(tmp_path, "plan", _plan(tmp_path, style="beanie-cuff", garment="beanie"))
    assert r.returncode == 0 and "beanie-cuff" in r.stdout
    r = _intake(tmp_path, "plan", _plan(tmp_path, slug="probe-tee", garment="t-shirt"))
    assert r.returncode == 0, r.stdout


# ------------------------------------------------------------------ dispatch build gate
def _project(tmp_path, slug, status):
    P = tmp_path / "projects" / slug / "inputs"; P.mkdir(parents=True)
    (P.parent / "STATUS.json").write_text(json.dumps(status))


def _dispatch(tmp_path, *args):
    e = dict(os.environ, TECHPACK_ROOT=str(tmp_path), TECHPACK_STATE=str(tmp_path / "state"), TECHPACK_REAP="0")
    return subprocess.run(["bash", os.path.join(ROOT, "scripts", "dispatch.sh"), "--dry-run", *args],
                          capture_output=True, text=True, env=e)


def test_dispatch_will_not_build_a_hat_without_a_style(tmp_path):
    _project(tmp_path, "probe-cap", {"slug": "probe-cap", "garment": "cap"})
    r = _dispatch(tmp_path, "build", "probe-cap")
    assert r.returncode == 2, r.stdout + r.stderr
    out = r.stdout + r.stderr
    assert "REFUSED" in out and all(k in out for k in KEYS) and "claude --bg" not in out


def test_dispatch_builds_a_hat_with_a_valid_style(tmp_path):
    _project(tmp_path, "probe-cap", {"slug": "probe-cap", "garment": "cap", "style": "asce-dad"})
    r = _dispatch(tmp_path, "build", "probe-cap")
    assert r.returncode == 0 and "claude --bg -n tp-build-probe-cap" in r.stdout, r.stdout + r.stderr
    _project(tmp_path, "probe-tee", {"slug": "probe-tee", "garment": "t-shirt"})
    assert _dispatch(tmp_path, "build", "probe-tee").returncode == 0


def test_a_garment_text_cannot_run_shell_commands_at_intake(tmp_path):
    """reviewer 2026-10-28: the --field values went through os.system inside double quotes, so $(...) ran"""
    probe = tmp_path / "PWNED"
    r = _intake(tmp_path, "apply", _plan(tmp_path, garment=f"cap $(touch {probe})", style="asce-dad"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert not probe.exists()
    s = json.loads((tmp_path / "projects" / "probe-cap" / "STATUS.json").read_text())
    assert s["garment"] == f"cap $(touch {probe})"


def test_status_set_only_takes_known_fields(tmp_path):
    e = dict(os.environ, TECHPACK_ROOT=str(tmp_path), TECHPACK_STATE=str(tmp_path / "state"))
    (tmp_path / "projects" / "x").mkdir(parents=True)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "status_set.py"), "x", "intake", "n", "--field", "stage=delivered"],
                       capture_output=True, text=True, env=e)
    assert r.returncode != 0 and not (tmp_path / "projects" / "x" / "STATUS.json").exists()


def test_dispatch_with_no_garment_recorded_still_catches_a_hat_by_its_name(tmp_path):
    """reviewer 2026-10-28: check-project passed any project with no garment line; old non-hat projects (no garment
    line: drum-island-plum-pine, konpeito-jeans, ...) must still pass"""
    for slug, title in (("probe-beanie", "Pink Hearts Beanie"), ("probe-ff", "Fire Fist"), ("probe-jeans", "Konpeito jeans")):
        P = tmp_path / "projects" / slug / "inputs"; P.mkdir(parents=True)
        (P / "brief.md").write_text(f"# Brief — {title}\n\n- Slug: {slug}\n")
    r = _dispatch(tmp_path, "build", "probe-beanie")
    assert r.returncode == 2 and "beanie-cuff" in r.stdout + r.stderr, r.stdout + r.stderr
    assert _dispatch(tmp_path, "build", "probe-ff").returncode == 2           # a product we sell on asce-dad
    assert _dispatch(tmp_path, "build", "probe-jeans").returncode == 0
