#!/bin/bash
# commit one product's folder (+ lesson proposals) without colliding with other builders. usage: commit_project.sh <slug> "message"
set -e
R="$(cd "$(dirname "$0")/.." && pwd)"; S="$1"; M="${2:-update $1}"
exec 9>"$R/.git/techpack-commit.lock"; flock 9
cd "$R"
git add "projects/$S" 2>/dev/null || true
git diff --cached --quiet && { echo "nothing to commit for $S"; exit 0; }
git commit -q -m "$S: $M" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
# NO pull here: the working tree is shared with other builders (their uncommitted work would be autostashed and can be
# lost on a conflicting pop — LESSONS E8). Push only if it fast-forwards; otherwise the coordinator syncs after the batch.
git push -q 2>/dev/null || echo "remote is ahead — commit kept locally; the coordinator pulls + pushes when all builders are done"
echo "committed $S"
