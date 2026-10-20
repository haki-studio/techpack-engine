# RECAP 2026-10-20 — detached workers (session 093e980c)

## Why
Founder: closing the last coordinator meant waiting for every builder to finish — not an efficient use of his time.
Cause: builders were in-process `Agent` subagents. They die with the session, so the company hand-off rule (session-size
hook, step 3) says "wait for running subagents". Keeping the coordinator open also keeps its token bill growing.

## What changed (branch `session-dispatch`)
- `scripts/dispatch.sh build|review|fix <slug> [pr]` — each worker is its own `claude --bg` session in its own worktree
  (`.claude/worktrees/tp-<slug>`, branch `tp-<slug>`). Caps: TECHPACK_MAX_WORKERS (2), HAKI_MAX_SESSIONS (6), ≥ 6 GB RAM;
  overflow goes to `~/.techpack/queue`, drained by every dispatch and by each worker as it ends.
- Chain without a coordinator: builder → PR → `dispatch.sh review` → approve / one `fix` round / blocked-for-founder.
- Board: `status_set.py` mirrors to `~/.techpack/board/<slug>.json`; `status.py` shows the newer row + the worker name.
- `commit_project.sh` works inside a worktree (lock in the common git dir).
- `/techpack` SKILL step 2–3, builder agent rules 10–12, `/techpack-status`, LESSONS E10, `tests/test_dispatch.py`.

## Verified
- `claude --bg` probe: answered, ran under Claude's own supervisor (not a child of this session), stopped + removed.
- 273 tests pass; the board-merge test goes red when the merge is broken.
- Not yet run: a real build through dispatch.sh end to end (first real product run is the proof).

## Open
- Company-wide: `~/.claude/company/PROTOCOL.md` line ~92 ("prefer in-process subagents for builders") and the
  session-size hook step 3 ("wait for running subagents") still push the old pattern — founder decision (asked).
- Konpeito RevE external sample reviewed (see the session's answer): 07a/07b not sew-out ready.
