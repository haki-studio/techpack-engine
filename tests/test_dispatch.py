"""LESSONS E10: tech pack workers run as their own background sessions (scripts/dispatch.sh), so the session that
started them can close at any time; their progress reaches one board (~/.techpack/board) that status.py reads."""
import json, os, subprocess, sys, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLUG = sorted(d for d in os.listdir(os.path.join(ROOT, "projects")) if os.path.isdir(os.path.join(ROOT, "projects", d)))[0]

def run(args, state, **env):
    e = dict(os.environ, TECHPACK_STATE=str(state), TECHPACK_REAP="0", **env)   # never touch real sessions
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


def test_dry_run_drain_lists_the_queue_and_keeps_it(tmp_path):
    """LESSONS E13: `--dry-run --drain` deleted every queued job while only printing them (2026-10-21)."""
    q = f"review\t{SLUG}\t28\nfix\t{SLUG}\t34\n"
    (tmp_path / "queue").write_text(q)
    r = run(["--dry-run", "--drain"], tmp_path)
    assert r.returncode == 0, r.stderr
    assert f"tp-review-{SLUG}" in r.stdout and f"tp-fix-{SLUG}" in r.stdout
    assert (tmp_path / "queue").read_text() == q

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


def review_next(state, *args):
    e = dict(os.environ, TECHPACK_STATE=str(state))
    return subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "review_next.py"), SLUG, "7", *args],
                          capture_output=True, text=True, env=e)

def seed(state, *fixables, pr="7"):
    os.makedirs(state / "board", exist_ok=True)
    json.dump({"slug": SLUG, "log": [], "reviews": [{"pr": pr, "fixable": f, "founder": 0} for f in fixables]},
              open(state / "board" / f"{SLUG}.json", "w"))

def test_review_next_keeps_fixing_only_while_it_improves(tmp_path):
    def act(*a): return review_next(tmp_path, *a, "--dry-run").stdout.split(":")[0]
    assert act("--fixable", "0") == "reviewed"
    assert act("--fixable", "0", "--founder", "2") == "blocked"
    assert act("--fixable", "5") == "fix"                      # first review always gets a round
    seed(tmp_path, 5); assert act("--fixable", "3") == "fix"   # 5 -> 3: improving
    seed(tmp_path, 5); assert act("--fixable", "5") == "blocked"   # stalled
    seed(tmp_path, 3); assert act("--fixable", "4") == "blocked"   # worse
    seed(tmp_path, 9, 6, 4); assert act("--fixable", "2") == "blocked"   # ceiling: 3 rounds used
    r = review_next(tmp_path, "--fixable", "2", "--dry-run")
    assert "ceiling" in r.stdout
    # another PR's history does not count
    seed(tmp_path, 1, 1, 1, pr="8"); assert act("--fixable", "2") == "fix"


def test_a_worker_handing_off_does_not_count_itself(tmp_path):
    src = open(os.path.join(ROOT, "scripts", "dispatch.sh")).read()
    i = src.index("live_bg() {"); fn = src[i:src.index("\n}\n", i) + 3]
    fake = tmp_path / "bin"; fake.mkdir()
    agents = [{"kind": "background", "pid": os.getpid(), "name": "tp-build-me", "id": "a"},
              {"kind": "background", "pid": os.getppid(), "name": "tp-build-other", "id": "b"}]
    (fake / "claude").write_text("#!/bin/sh\necho '" + json.dumps(agents) + "'\n"); (fake / "claude").chmod(0o755)
    env = dict(os.environ, PATH=f"{fake}:{os.environ['PATH']}")
    out = lambda pid: subprocess.run(["bash", "-c", fn + "\nlive_bg tp-"], capture_output=True, text=True,
                                     env=dict(env, CLAUDE_PID=str(pid))).stdout.split()
    assert sorted(out(1)) == ["tp-build-me", "tp-build-other"]
    assert out(os.getpid()) == ["tp-build-other"]


def test_finished_workers_are_reaped_busy_and_foreign_ones_are_not(tmp_path):
    """LESSONS E11: an idle --bg worker held its slot and made the next fix round of the same slug 'already running'."""
    src = open(os.path.join(ROOT, "scripts", "dispatch.sh")).read()
    i = src.index("reap_idle() {"); fn = src[i:src.index("\n}\n", i) + 3]
    procs = {k: subprocess.Popen(["sleep", "60"]) for k in ("idle_tp", "busy_tp", "idle_other", "idle_me")}
    agents = [{"kind": "background", "pid": procs["idle_tp"].pid, "name": "tp-fix-x", "status": "idle"},
              {"kind": "background", "pid": procs["busy_tp"].pid, "name": "tp-review-x", "status": "busy"},
              {"kind": "background", "pid": procs["idle_other"].pid, "name": "lead-eng-x", "status": "idle"},
              {"kind": "background", "pid": procs["idle_me"].pid, "name": "tp-build-me", "status": "idle"}]
    fake = tmp_path / "bin"; fake.mkdir()
    (fake / "claude").write_text("#!/bin/sh\necho '" + json.dumps(agents) + "'\n"); (fake / "claude").chmod(0o755)
    env = dict(os.environ, PATH=f"{fake}:{os.environ['PATH']}")
    try:
        r = subprocess.run(["bash", "-c", fn + "\nreap_idle"], capture_output=True, text=True, timeout=30,
                           env=dict(env, CLAUDE_PID=str(procs["idle_me"].pid)))
        assert r.stdout.split() == ["reaped", "idle", "tp-fix-x"], r.stdout + r.stderr
        procs["idle_tp"].wait(timeout=5)
        assert all(procs[k].poll() is None for k in ("busy_tp", "idle_other", "idle_me"))
        r = subprocess.run(["bash", "-c", fn + "\nreap_idle"], capture_output=True, text=True, timeout=30,
                           env=dict(env, TECHPACK_REAP="0"))
        assert r.stdout == ""
    finally:
        for p in procs.values(): p.kill()
