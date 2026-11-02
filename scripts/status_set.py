#!/usr/bin/env python3
"""Record a product's progress: status_set.py <slug> <stage> "<note>" [--preview path] [--question "..."] [--blocked]
                                [--field key=value ...]   (intake records garment + hat style this way)
TECHPACK_ROOT overrides the data root (projects/), for tests.
Stages (in order): intake inventory pattern art stitch qa documents delivered review reviewed"""
import sys, os, json, datetime, argparse
ROOT = os.environ.get("TECHPACK_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ["intake", "inventory", "pattern", "art", "stitch", "qa", "documents", "delivered", "review", "reviewed"]
ap = argparse.ArgumentParser(); ap.add_argument("slug"); ap.add_argument("stage"); ap.add_argument("note", nargs="?", default="")
ap.add_argument("--preview"); ap.add_argument("--question", action="append"); ap.add_argument("--blocked", action="store_true")
ap.add_argument("--field", action="append", default=[])
a = ap.parse_args()
p = os.path.join(ROOT, "projects", a.slug, "STATUS.json")
s = json.load(open(p)) if os.path.exists(p) else {"slug": a.slug, "log": [], "questions": []}
s["stage"] = a.stage; s["stage_index"] = STAGES.index(a.stage) if a.stage in STAGES else s.get("stage_index", 0)
s["blocked"] = a.blocked; s["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
if a.preview: s["preview"] = os.path.relpath(os.path.abspath(a.preview), os.path.join(ROOT, "projects", a.slug))
FIELDS = ("garment", "style")      # the only extra keys a caller may set (never stage/log/...)
for f in a.field:
    k, _, v = f.partition("=")
    if k not in FIELDS: sys.exit(f"--field {k}: not allowed (allowed: {', '.join(FIELDS)})")
    s[k] = v
if a.question: s["questions"] = list(dict.fromkeys(s.get("questions", []) + a.question))
s["log"].append([s["updated"], a.stage, a.note]); s["log"] = s["log"][-40:]
json.dump(s, open(p, "w"), indent=1)
# mirror to the board outside git, so status.py sees workers running in their own worktrees (LESSONS E10)
board = os.path.join(os.environ.get("TECHPACK_STATE", os.path.expanduser("~/.techpack")), "board"); os.makedirs(board, exist_ok=True)
bp = os.path.join(board, a.slug + ".json")
b = dict(s, worker=(json.load(open(bp)).get("worker", {}) if os.path.exists(bp) else {}), project_dir=os.path.join(ROOT, "projects", a.slug))
json.dump(b, open(bp, "w"), indent=1)
