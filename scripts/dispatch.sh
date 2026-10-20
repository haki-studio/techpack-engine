#!/bin/bash
# Start a tech pack worker as its OWN background Claude session (claude --bg), never as an in-process subagent.
# The session that launches it can close at any moment: the worker keeps running, its state lives in its branch,
# its PR and the board (~/.techpack/board/<slug>.json), and it hands off to the next step itself (LESSONS E10).
#
#   scripts/dispatch.sh build  <slug> ["extra brief"]   builder in worktree .claude/worktrees/tp-<slug> (branch tp-<slug>)
#   scripts/dispatch.sh review <slug> <pr>              independent reviewer on that PR (its own scratch worktree)
#   scripts/dispatch.sh fix    <slug> <pr>              builder fix round in the existing tp-<slug> worktree
#   scripts/dispatch.sh --drain                         start queued jobs while there is room
#   scripts/dispatch.sh --dry-run <role> <slug> ...     print what would run; no worktree, no session
#
# Watch: `claude agents` (attach / logs / stop), `python3 scripts/status.py`, status.html.
# Limits: TECHPACK_MAX_WORKERS (default 2) tech pack sessions at once, HAKI_MAX_SESSIONS (default 6) background
# sessions machine-wide, >= 6 GB RAM free (the 2026-10-05 freeze, ~/.claude/company/PROTOCOL.md). A job that does
# not fit is queued in ~/.techpack/queue and started by the next dispatch/drain (every worker drains when it ends).
set -euo pipefail
R="$(cd "$(dirname "$0")/.." && pwd)"
MAIN="$(git -C "$R" rev-parse --path-format=absolute --git-common-dir)"; MAIN="$(dirname "$MAIN")"
STATE="${TECHPACK_STATE:-$HOME/.techpack}"; mkdir -p "$STATE/board"; QUEUE="$STATE/queue"; touch "$QUEUE"
DRY=0; [ "${1:-}" = "--dry-run" ] && { DRY=1; shift; }

live_bg() {   # ids of live background sessions (same test as ~/.claude/company/bin/spawn.sh)
  claude agents --json 2>/dev/null | python3 -c "
import json,os,sys
pre=sys.argv[1]
try: d=json.load(sys.stdin)
except Exception: d=[]
for a in d:
    if a.get('kind')!='background' or not a.get('pid'): continue
    if pre and not (a.get('name') or '').startswith(pre): continue
    try: os.kill(int(a['pid']),0); print(a.get('name') or a.get('id'))
    except OSError: pass" "${1:-}"
}
room() {      # 0 = there is room for one more worker
  [ "$DRY" = 1 ] && return 0
  local tp all mb
  tp=$(live_bg tp- | wc -l); all=$(live_bg | wc -l); mb=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  [ "$tp" -lt "${TECHPACK_MAX_WORKERS:-2}" ] && [ "$all" -lt "${HAKI_MAX_SESSIONS:-6}" ] && [ "$mb" -ge 6000 ]
}
board() {     # board <slug> <key> <value>: record who is working on what, outside git
  python3 - "$STATE/board/$1.json" "$2" "$3" <<'EOF'
import json, os, sys, datetime
p, k, v = sys.argv[1:]
s = json.load(open(p)) if os.path.exists(p) else {"slug": os.path.basename(p)[:-5], "log": []}
s.setdefault("worker", {})[k] = v; s["worker"]["at"] = datetime.datetime.now().isoformat(timespec="seconds")
json.dump(s, open(p, "w"), indent=1)
EOF
}

launch() {    # launch <role> <slug> [arg]
  local role=$1 slug=$2 arg="${3:-}" name="tp-$1-$2" wt="$MAIN/.claude/worktrees/tp-$2" agent prompt
  [ -d "$MAIN/projects/$slug" ] || git -C "$MAIN" cat-file -e "origin/main:projects/$slug" 2>/dev/null \
    || { echo "no such product: projects/$slug" >&2; return 2; }
  case $role in
    build)  agent=techpack-builder
            prompt="Build the tech pack for projects/$slug. Brief: projects/$slug/inputs/brief.md. ${arg}" ;;
    fix)    agent=techpack-builder; [ -n "$arg" ] || { echo "fix needs a PR number" >&2; return 2; }
            prompt="Fix round for projects/$slug, PR #$arg: read the reviewer's verdict (gh pr view $arg --comments), fix every blocker and should-fix, rebuild, re-render, push, comment what changed, then run scripts/dispatch.sh review $slug $arg." ;;
    review) agent=reviewer; [ -n "$arg" ] || { echo "review needs a PR number" >&2; return 2; }
            wt="$MAIN/.claude/worktrees/tp-review-$slug"
            prompt="Independent review of the tech pack in PR #$arg (projects/$slug), per .claude/skills/techpack/SKILL.md step 3: fidelity first (stitch preview vs mockup, zoomed, every missing detail), then every page rendered and read, every number vs the generated files, LESSONS gates incl. the A14/A15 tables, grep for hard-coded motif geometry. Post the verdict as a PR comment tied to the head sha, ending with two counts: fixable = blockers + should-fix items the builder can fix alone, founder = items only the founder can decide. Then run, as your last step: python3 scripts/review_next.py $slug $arg --fixable <n> --founder <m> (it approves, starts another fix round while each round clearly improves, or blocks for the founder)." ;;
    *) echo "unknown role: $role (build | fix | review)" >&2; return 2 ;;
  esac
  prompt="$prompt

You are a background worker (LESSONS E10): nobody is waiting on you and the session that started you may be gone. Work only in $wt. Report every stage with scripts/status_set.py. When your step is done, hand off with scripts/dispatch.sh as your instructions say, run scripts/dispatch.sh --drain, then stop."
  if [ "$DRY" = 1 ]; then printf 'worktree: %s\nclaude --bg -n %s --agent %s --permission-mode auto <prompt>\n%s\n' "$wt" "$name" "$agent" "$prompt"; return 0; fi
  if live_bg "$name" | grep -qx "$name"; then echo "already running: $name"; return 0; fi
  if ! room; then printf '%s\t%s\t%s\n' "$role" "$slug" "$arg" >> "$QUEUE"; board "$slug" queued "$role $arg"; echo "queued: $name (no room now)"; return 0; fi
  git -C "$MAIN" fetch -q origin
  if [ ! -d "$wt" ]; then
    if [ "$role" = review ]; then
      git -C "$MAIN" fetch -q origin "pull/$arg/head:tp-pr-$arg" 2>/dev/null || true
      git -C "$MAIN" worktree add -q --detach "$wt" "tp-pr-$arg"
    else
      git -C "$MAIN" worktree add -q -B "tp-$slug" "$wt" origin/main
      git -C "$wt" config "branch.tp-$slug.remote" origin; git -C "$wt" config "branch.tp-$slug.merge" "refs/heads/tp-$slug"
    fi
  fi
  local id
  id=$(cd "$wt" && claude --bg -n "$name" --agent "$agent" --permission-mode auto "$prompt" 2>&1 | sed -n 's/^backgrounded · \([0-9a-f]*\) .*/\1/p')
  board "$slug" "$role" "$name ${id:-?} $wt"
  echo "started $name (${id:-id unknown}) in $wt"
}

drain() {     # start queued jobs while there is room
  local role slug arg
  while [ -s "$QUEUE" ] && room; do
    IFS=$'\t' read -r role slug arg < "$QUEUE"; sed -i 1d "$QUEUE"
    launch "$role" "$slug" "$arg" || true
  done
}

case "${1:-}" in
  --drain) exec 9>"$STATE/dispatch.lock"; flock 9; drain ;;
  build|fix|review) [ $# -ge 2 ] || { sed -n 5,9p "$0"; exit 2; }
                    exec 9>"$STATE/dispatch.lock"; flock 9; launch "$1" "$2" "${*:3}"; [ "$DRY" = 1 ] || drain ;;
  *) sed -n 2,15p "$0"; exit 2 ;;
esac
