"""LESSONS E10: tech pack workers run as their own background sessions (scripts/dispatch.sh), so the session that
started them can close at any time; their progress reaches one board (~/.techpack/board) that status.py reads."""
import json, os, subprocess, sys, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLUG = sorted(d for d in os.listdir(os.path.join(ROOT, "projects")) if os.path.isdir(os.path.join(ROOT, "projects", d)))[0]

def run(args, state, **env):
    e = dict(os.environ, TECHPACK_STATE=str(state), **env)
    return subprocess.run(["bash", os.path.join(ROOT, "scripts", "dispatch.sh"), *args], capture_output=True, text=True, env=e)

def test_dry_run_starts_a_background_session_not_a_subagent(tmp_path):
    existed = os.path.exists(os.path.join(ROOT, ".claude", "worktrees", f"tp-{SLUG}"))
    r = run(["--dry-run", "build", SLUG], tmp_path)
    assert r.returncode == 0, r.stderr
    assert f"claude --bg -n tp-build-{SLUG} --agent techpack-builder --permission-mode auto" in r.stdout
    assert f".claude/worktrees/tp-{SLUG}" in r.stdout and "scripts/dispatch.sh --drain" in r.stdout
    assert os.path.exists(os.path.join(ROOT, ".claude", "worktrees", f"tp-{SLUG}")) == existed   # dry run touches nothing

def test_review_and_fix_need_a_pr_and_a_real_product(tmp_path):
    assert run(["--dry-run", "review", SLUG], tmp_path).returncode == 2
    assert run(["--dry-run", "fix", SLUG], tmp_path).returncode == 2
    assert run(["--dry-run", "build", "no-such-product-xyz"], tmp_path).returncode == 2
    r = run(["--dry-run", "review", SLUG, "42"], tmp_path)
    assert r.returncode == 0 and "--agent reviewer" in r.stdout and f"tp-review-{SLUG}" in r.stdout

def test_no_room_queues_instead_of_starting(tmp_path):
    r = run(["build", SLUG, "extra words here"], tmp_path, TECHPACK_MAX_WORKERS="0")
    assert r.returncode == 0, r.stderr
    assert "queued" in r.stdout
    assert (tmp_path / "queue").read_text() == f"build\t{SLUG}\textra words here\n"
    assert json.load(open(tmp_path / "board" / f"{SLUG}.json"))["worker"]["queued"] == "build extra words here"
    # draining with still no room keeps the job queued
    assert run(["--drain"], tmp_path, TECHPACK_MAX_WORKERS="0").returncode == 0
    assert (tmp_path / "queue").read_text().count("\n") == 1

def test_board_mirror_reaches_status(tmp_path):
    e = dict(os.environ, TECHPACK_STATE=str(tmp_path))
    proj = os.path.join(ROOT, "projects", SLUG, "STATUS.json")
    before = open(proj).read() if os.path.exists(proj) else None
    try:
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "status_set.py"), SLUG, "art", "probe note"], check=True, env=e)
        b = json.load(open(tmp_path / "board" / f"{SLUG}.json"))
        assert b["stage"] == "art" and b["log"][-1][2] == "probe note"
        # a worker in another worktree writes only the board: status.py must show the newer board row
        b["updated"] = "9999-01-01T00:00:00"; b["log"].append([b["updated"], "qa", "from a worktree"]); b["stage"] = "qa"
        b["worker"] = {"build": f"tp-build-{SLUG} abc123 /x"}
        json.dump(b, open(tmp_path / "board" / f"{SLUG}.json", "w"))
        os.environ["TECHPACK_STATE"] = str(tmp_path)
        spec = importlib.util.spec_from_file_location("status_probe", os.path.join(ROOT, "scripts", "status.py"))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        row = {r["slug"]: r for r in m.load()}[SLUG]
        assert row["stage"] == "qa" and m.worker(row) == f"tp-build-{SLUG}"
        assert f"tp-build-{SLUG}" in m.table([row])
    finally:
        os.environ.pop("TECHPACK_STATE", None)
        if before is None: os.path.exists(proj) and os.remove(proj)
        else: open(proj, "w").write(before)
