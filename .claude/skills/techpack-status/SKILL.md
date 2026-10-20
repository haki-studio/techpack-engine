---
description: Show progress of every product's tech pack build (stage, latest note, open questions) and refresh status.html.
disable-model-invocation: true
---

Run `python3 scripts/status.py` (it merges the board `~/.techpack/board/`, written by background workers in their own
worktrees) and `gh pr list --state open`, and show Devin one table: product, stage, worker session, PR link.
`claude agents --json` says which workers are still alive; a product whose worker is gone before `delivered` is resumed
with `scripts/dispatch.sh build <slug> "resume from the branch"`, and `scripts/dispatch.sh --drain` starts anything queued. Then list every open question from the products'
STATUS.json files, grouped by product, and say which products are blocked and on what. Remind him `status.html`
(in the repo root) refreshes itself and shows each product's latest preview.
