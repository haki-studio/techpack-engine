# RECAP 2026-10-20 — engine coordinator (session 19b9021e)

## What happened
Picked up HANDOFF (M1 merged) and ran the engine milestones as builder → independent reviewer → founder-merge loops.
| PR | milestone | review rounds | key review catches |
|---|---|---|---|
| #5 | M5 SVG parity (Konpeito) | 1 | border dots smaller than art (renderer + slight undersize; sew-out call) |
| #6 | M2 organic + M1 follow-ups | 2 | bench not idempotent (+dirty key); direction headline counted self-derived tiles; forgeable field angles; rule 3 ungated |
| #7 | M6 puff/chenille/chain | 2 | puff guards only in the swatch; base fill under puff (decided: knock out, rule 6) |
| #8 | M4g threads/sequencing/review | 2 | reach cut stripped 1 mm seam underlap (decided: keep 1 mm, report cost); +foam counted as a needle |
| #9 | M3a buildings | 2 | dangling seq_after ids; windows/members dropped to avoid a 3rd layer (decided: fidelity first, keep + suggest); 22 mm tuned on the crop → relative 0.75 |
| #10 | M3b trees/florets | 2 | HintError with M4g; radial guard hole; blossom 8.6 mm/mm² (fixed: 0.3 mm floret seam → 6.6) |

## Decisions made by the coordinator (founder may overrule)
- Puff: knock out the base under puff, keep 1 mm (rule 6). Puff capped at 7 mm (dst2 splits > 7.4 mm).
- Seam underlap: keep 1 mm even though it costs stack/density (gaps from push-pull matter more).
- Building details: keep at underlaps, report cost; only rule-9 minimums become suggestions.
- Gates are never loosened to pass; scope changes (radial exemption, part-based stack) need their own PR with red proofs.
- Merge order for parallel PRs: whoever is approved first; later PRs merge main in (not rebase) and the coordinator numbers LESSONS.

## Process lessons
- Parallel builders in separate worktrees worked; conflicts stayed in LESSONS/BENCH/SCOREBOARD/yaml when builders kept to
  new files + appended blocks. Reviewers must use their OWN scratch worktree (one reviewer reused a builder's worktree and
  another reviewer's checkout was moved under it).
- SCOREBOARD.json is a JSON array: a textual union merge breaks it; run_bk_crop.yaml can end up with two separate_kinds keys.

## State and next
See HANDOFF.md "ENGINE WORK — state 2026-10-20 evening".
