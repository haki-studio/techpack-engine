#!/bin/bash
# commit one product's folder (+ lesson proposals) without colliding with other builders. usage: commit_project.sh <slug> "message"
set -e
R="$(cd "$(dirname "$0")/.." && pwd)"; S="$1"; M="${2:-update $1}"
exec 9>"$R/.git/techpack-commit.lock"; flock 9
cd "$R"
git add "projects/$S" 2>/dev/null || true
git diff --cached --quiet && { echo "nothing to commit for $S"; exit 0; }
git commit -q -m "$S: $M" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
git pull -q --rebase --autostash || true
git push -q || echo "push failed — will retry on next commit"
echo "committed $S"
