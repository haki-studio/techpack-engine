"""LESSONS E8+: no merge-conflict markers in any tracked text file (they were once pushed to main after an autostash)."""
import os, re, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = re.compile(r"^(<<<<<<< |>>>>>>> |=======$)", re.M)

def test_no_conflict_markers():
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    bad = []
    for fn in files:
        if not fn.endswith((".py", ".md", ".sh", ".json", ".txt", ".yaml", ".yml")): continue
        p = os.path.join(ROOT, fn)
        if os.path.exists(p) and MARK.search(open(p, encoding="utf-8", errors="ignore").read()): bad.append(fn)
    assert not bad, f"conflict markers in: {bad}"
