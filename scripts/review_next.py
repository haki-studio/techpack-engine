#!/usr/bin/env python3
"""After a review: decide the next step and take it (LESSONS E10). The reviewer calls this once, last.
  review_next.py <slug> <pr> --fixable N [--founder M] [--dry-run]
N = blockers + should-fix items the builder can fix alone; M = items only the founder can decide.
  nothing open                          -> reviewed
  only founder items                    -> blocked for the founder
  fewer fixable items than last review  -> another fix round (first review always gets one)
  same or more than last review         -> blocked: not improving
  TECHPACK_MAX_FIX_ROUNDS (3) used up   -> blocked: ceiling (cost safety net)
History per PR lives on the board (~/.techpack/board/<slug>.json, "reviews")."""
import argparse, datetime, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument("slug"); ap.add_argument("pr")
ap.add_argument("--fixable", type=int, required=True); ap.add_argument("--founder", type=int, default=0)
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
MAX = int(os.environ.get("TECHPACK_MAX_FIX_ROUNDS", "3"))

def decide(prev, fixable, founder):
    """prev = earlier reviews of this PR (oldest first). Returns (action, reason)."""
    if fixable == 0:
        return ("reviewed", "approved") if founder == 0 else ("blocked", f"needs founder: {founder} decision(s)")
    if prev and fixable >= prev[-1]["fixable"]:
        return "blocked", f"not improving: {prev[-1]['fixable']} -> {fixable} fixable items"
    if len(prev) >= MAX:
        return "blocked", f"ceiling: {MAX} fix rounds used, {fixable} fixable items left"
    return "fix", f"round {len(prev) + 1}: {fixable} fixable items" + (f" (was {prev[-1]['fixable']})" if prev else "")

board = os.path.join(os.environ.get("TECHPACK_STATE", os.path.expanduser("~/.techpack")), "board")
os.makedirs(board, exist_ok=True); bp = os.path.join(board, a.slug + ".json")
b = json.load(open(bp)) if os.path.exists(bp) else {"slug": a.slug, "log": []}
prev = [r for r in b.get("reviews", []) if str(r["pr"]) == str(a.pr)]
action, reason = decide(prev, a.fixable, a.founder)
print(f"{action}: {reason}")
if a.dry_run: sys.exit(0)

b.setdefault("reviews", []).append({"pr": a.pr, "fixable": a.fixable, "founder": a.founder, "action": action,
                                     "at": datetime.datetime.now().isoformat(timespec="seconds")})
json.dump(b, open(bp, "w"), indent=1)
S = os.path.join(ROOT, "scripts")
if action == "reviewed":
    subprocess.run([sys.executable, os.path.join(S, "status_set.py"), a.slug, "reviewed", f"PR #{a.pr} approved"], check=True)
elif action == "blocked":
    subprocess.run([sys.executable, os.path.join(S, "status_set.py"), a.slug, "review", f"PR #{a.pr} {reason}", "--blocked"], check=True)
else:
    subprocess.run([sys.executable, os.path.join(S, "status_set.py"), a.slug, "review", f"PR #{a.pr} fix {reason}"], check=True)
    subprocess.run(["bash", os.path.join(S, "dispatch.sh"), "fix", a.slug, str(a.pr)], check=True)
