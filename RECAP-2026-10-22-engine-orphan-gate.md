# RECAP 2026-10-22: orphan-fragment prod gate (engine)

Builder session a62e8d0f for lead `lead-eng-techpack-engine-m2` (mission techpack-engine-m2). Branch `engine-orphan-gate`
off origin/main cc515e5, worktree `~/te-orphan-gate`. No product pack was rebuilt or shipped (packs paused).

## What was built
| piece | where |
|---|---|
| Gate logic: `blocks()` (stitch blocks per stop from the WRITTEN PES; DST needs `colours=`), `orphan_fragments()` (hits, exempt hook, raises on a file it cannot judge) | `engine/digitize/gates_orphan.py` |
| Production-file selection per product (`product_files`: skips pkg copies, `old*`, `_*`, `before*`, `*backup*`, `*superseded*`, gate_cal, digitize, engine_m*, revc; falls back to the pkg copy when that is all a product has, e.g. moon) | same |
| Ratchet (lead 22 Oct): products at 0 fail on any orphan; others fail only above their baseline; `--update-baseline` only lowers | same + `engine/digitize/orphan_baseline.json` |
| Thin CLI: files, or `--products [slug]` = the prod gate (exit 1 fail, 2 unjudgeable) | `scripts/orphan_fragments.py` |
| Fixtures: KCOS Rev H FL M + FR M (red), Rev I FL M (green), copied byte-identical from the tp-keep-clean-our-space-hoodie worktree | `tests/fixtures/orphan/` |
| Tests (21) | `tests/test_orphan_gate.py` |
| Gate named in the pipeline (step 3 "Gates") | `.claude/skills/techpack-pipeline/SKILL.md` |
| One zoom crop per flagged product | `docs/orphan_gate/*.png` |

## Key findings / decisions
- **The HANDOFF's "0 on Konpeito/Grand Line/Forestball/Red Beast/Koi/Comet" was wrong.** The coordinator's audit output
  (scratchpad 9487d766, bjqp4agtw) was the top ~60 of 502 files sorted by count; the six products were just not in it.
  Measured on every production PES in the main checkout (same thresholds):

  | product | files | orphans | baseline |
  |---|---|---|---|
  | comet-city-hoodie | 84 | 0 | 0 (blocks) |
  | red-beast-hoodie | 70 | 0 | 0 (blocks) |
  | keep-clean-our-space-hoodie (Rev I) | 112 | 0 | 0 (blocks) |
  | moon (pkg copy) | 98 | 0 | 0 (blocks) |
  | konpeito-jeans | 8 | 20 (coin pocket 10, waistband 10) | 20 |
  | koi-blossom-hoodie | 75 | 537 | 537 |
  | forestball | 21 | 610 | 610 |
  | grand-line-jacket | 42 | 828 | 828 |
  | castle-falls-jacket | 149 | 2,291 | 2,291 |
  | wave-jacket | 132 | 15,945 | 15,945 |
- KCOS: Rev H FL M = 8 hits, the same stops (7 x1, 8 x7) as the project's own glyph frag gate on the founder's spots; FR M 21; Rev I 0.
- **Wave: no exemption.** Wave hits are small foam-white / blue blocks in a later stop touching a big same-thread fill.
  The candidate exemption, "the fragment lies on top of other-colour stitches sewn earlier (layering)", measures 0.77
  median on Wave, but also 0.53 on the KCOS FL founder spots (6 of 8 > 0.5), so it would hide the defect the gate exists
  for. Wave is built by project code (only `chenille.py` imports two engine techniques, never the planner), so there is no
  Part.meta foam/stack hint to key an exemption on. Wave's own ENGINE_NOTES §22 rule is
  "nothing tiny is sewn alone". So Wave is reported as a real finding (ratcheted), not exempted.
- Konpeito hits are a small red detail sewn on a cream ground, beside the big red block of stop 1 (100 % on top of
  another colour). It may need its stop order for the layering, but it can still sew in the red stop's pass if the
  ground goes first. Listed for TD review, not exempted.
- PES gotcha: pyembroidery merges two consecutive stops of one thread on write, so a real orphan always has another stop
  between it and its block (the synthetic tests put one there).

## Verification
- `pytest tests/test_orphan_gate.py`: 21 passed. Mutations: 16 gate/ratchet/selection mutations all RED (scratch
  script), plus the CLI exit code forced to 0 → `test_cli_prod_gate_end_to_end` RED; all restored → green.
- identity_check.sh + full suite: see the PR body (run after heavy-jobs = 0).

## Pending / next
- Fixes per product queue when packs resume (coordinator): each fix lowers its baseline in the same PR.
- The gate needs the product's `out/` (git-ignored), so it runs in the pipeline (skill step 3) and by hand, not in pytest
  over products; pytest covers it on committed fixtures.
- Engine copy `engine/digitize/techniques/column.py` still carries the copied code; the gate catches its output, but the
  source was not changed here (out of scope).
