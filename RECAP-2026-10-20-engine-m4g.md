# RECAP 2026-10-20: ENGINE_PLAN M4g (thread planner, full sequencing, review step; M4 minus the crop sign-off)

Branch `engine-m4g-sequencing` (off origin/main dbd0b0f), builder worktree. Parallel with M3a, M3b, M6.
Crop: `PYTHONPATH=engine python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api`
(`--answers <answers.json>` = the review step's answers to the previous run's questions). Write-up: `bench/BENCH_m4g.md`.

## What was built
| file | what |
|---|---|
| sequence.py (M4g block) | `apply_hints`, `dag_v1` (z-DAG + hint edges + the M6 foam rule), `limit_stack` (rule 6, + `reach`), `stack_count`, `order_v1` (colour batching, greedy key + rollout look-ahead), `orient_part` (planned entry / exit), `InnerRouter` / `plan_inner_travel`, `sequence_blocks`, `travel_mm`, `budget`, `report`, `plan_sequence`; `SEQ_DEFAULTS` |
| threads.py | `plan(keep=, saliency=, mix=)` (default-preserving), `optical_mix`, `salience`, `alternatives`, `plan_from_config` (`threads.choice`) |
| review.py | `questions` with STABLE ids + `effect`; `load_answers`, `apply_answers`, `apply_extract`, `apply_plan`, `AnswerError` |
| run.py (small, tagged `# M4g`) | `--answers` / `answers:` / `questions:`; thread planner call; sequence block in make_plan; `planner: m1` keeps the old path |
| tests/test_digitize_m4g.py | 12 tests; scratchpad `m4g/mutate_m4g.py`: 26/26 mutations RED, restored green |

## Sequencing hint CONTRACT (for M3a / M3b splitters: all optional, in Part.meta)
- `z` float: replaces part.z for sequencing.
- `seq_after` / `seq_before`: [selector], selector = part id | `kind:<k>` | `zone:<z>` | `group:<g>`. Hard DAG edges,
  touching or not; a hint WINS over a contradicting z edge. Unknown part id -> HintError; a hint cycle -> HintError.
- `knockout_of`: fill id(s): the fill gets a hole (minus the detail), the detail's z is set just below the fill's: it
  sews first and the fill covers its edge by the 1 mm underlap (rule 5).
- `group`: inside a stop, parts of the current group get a 3 mm bonus (finish a building / tree while one is free).
- `entry`: (x, y) the needle position used to plan that part's first block.
- `confidence` (0..1, review): < 0.5 asks a `confidence:<zone>:<kind>` question (keep / drop).
- M6 puff: a thread key ending in `+foam` (specialty.FOAM) is its own stop (batching is by exact key) and every flat part
  touching a puff part sews before it, whatever its z.

## Decisions (and why)
- **Density was travel, not underlap.** Planned blocks give 7 flags, the M2 file 113. Fix = planned entry / exit inside
  parts. Top cells are NEVER re-ordered (first try: coherence 61 -> 113, travel on sewn rows); chains reverse whole.
- **Stack**: lowest of 3 loses the area (no visible change, no gap, proven by induction and the test). `stack_reach_mm: 1`
  also removes the lower band under the seam of two higher parts (the file gate counts per 1 mm cell).
- **Inner travel only for underlay moves** (also through necks < 0.6 mm on a 5 px/mm raster). Top-to-top paths through
  the unsewn area were tried and dropped (no trim change, coherence worse, 150 s).
- **Long-travel trimming (dst2 opt-in) dropped**: +40 / +95 trims for no stack change. dst2.py is untouched.
- **Stop look-ahead ON** (22 -> 20 stops) though it costs 8 trims + 7 density flags on this crop: rule "colour stops
  minimised"; `sequence.stop_lookahead: false` if the factory prefers fewer trims.
- **Thread trade-off NOT decided**: default = M2's choice; the alternatives + optical mixes are a review question.
  Alternatives keep BOTH tones of a visible merge (keeping one only just flips the merge). Accents are never offered as
  mixing threads. Salience motifs count a zone only where its own tones list the tone (windows overlap).
- Answers apply where they belong: thread choice + "leave out" at extract, angles / technique / drop at plan. An answer
  cannot enable a technique the run disables (raises).

## Crop numbers (BENCH_m4g.md has the ablation table)
M2 -> M4g: trims 26.5 -> 22.2 /100 cm2 (PASS), density flags 113 -> 40, stack area > 2 9.07 -> 1.0 cm2 (max still 4:
63 junction cells / 23 travel / 10 truly 3-deep), stops 22 -> 20, coherence fails 61 -> 50, separation 46 -> 42, chaos
4.2 -> 4.6 (OK), gates 3/9 -> 4/9. DST f4a6545a46672615. `{planner: m1}` reproduces M2 byte-identically (0d86f00be8e9f8fa).

## Default-preserving
dst2.py untouched: 28-region probe dst 84ff50ea74938675 / pes 1ecd8f657db3f53a. M5 wb svgrun DST 449c14f6e8f693b6
(15,069 st, 161 trims), centreline 6/6, motifs 76/76, exposed 0, uncovered 0. pytest 144 passed.

## Left / next
- Stack max <= 2 on the FILE: the 63 junction cells need either an edge-run change at 3-part junctions (techniques) or a
  stack gate that measures layers by area, not runs per 1 mm cell (gate change = coordinator / founder call, not made).
- Same-colour travel lying ON sewn fill is visible in the live view (both M2 and M4g); no gate measures it yet (M5 noted
  the same). split_satin cords jump inside their own cell walk (fall_left.216: 73 mm moves).
- Optical mixes are reported, not sewn (a per-motif open layer would need a rulebook kind + stack budget).
- Re-run the crop after M3a / M3b merge (hints contract above); then the founder's live-view sign-off.
