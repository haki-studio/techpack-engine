# RECAP 2026-10-20: ENGINE_PLAN M4s (part-based stack gate + travel-on-sewn-fill gate)

Branch `engine-m4s-gates` (off origin/main 89a16e8), builder worktree. Parallel with M4c (chaos) and KOI.
Write-up with every number: `projects/castle-falls-jacket/bench/BENCH_m4s.md`.

## What was built
| file | what |
|---|---|
| engine/digitize/gates_stack.py (new) | `part_stack` (rule 6 counted by PARTS on the labelled file), `travel_on_fill` (travel on fill sewn earlier, not buried later), `travel_segment_index` (planned role "travel" blocks on the file), `plan_stack_area` (independent plan-geometry side for proofs), `run_hook`, `verdict_lines`, `summary` |
| engine/digitize/bench.py (2 small blocks, tagged `# --- M4s ---`) | `verdict` appends `stack_parts` + `travel_on_fill` when the row has them (old rows keep 8 / 9 lines); `md_row` adds "old 9: y/9" next to x/11 |
| engine/digitize/run.py (2 small edits, tagged `# --- M4s ---`) | gates stage calls `gates_stack.run_hook` before the verdict; the print line shows `x/11 (old 9: y/9)` + both new numbers |
| tests/test_digitize_m4s.py (new) | 14 tests; scratchpad `m4s/mutate_m4s.py`: 20/20 mutations RED, restored green |

## Decisions (and why)
- **The reviewer's literal recipe (0.5 mm cells, 1 mm window) does not discriminate.** On the M4g file (0 cm2 three deep in
  plan geometry) it flags 3.8 cm2, on M2 7.0 cm2; of M4g's 1,532 flagged cells only 67 are really 3 deep: a 1 mm window
  straddling a seam sees three parts. Eroding on 0.5 mm cells deletes the 1 mm bands that ARE 3 deep.
- **Final: 0.25 mm cells, 1 mm window, part mask eroded by 1 cell, regions >= 4 mm2, cap 2.5 mm2 per 100 cm2.** Window 1 mm
  because one row of thread = 1.0 mm/mm2 (< layer 1.5) and rows <= 0.5 mm apart always give >= 2.0 (0.75 mm aliased: a
  10 x 10 mm triple overlap measured 48 mm2). Region >= 4 mm2 = the strict gate's own flag size; junction spill is a speck.
  On M2, 94 % of the area in regions >= 2 mm2 is >= 3 deep in plan geometry; on main 0 %.
- **The gate under-counts thin 3-deep bands** (M2: 23.5 mm2 flagged of 3.84 cm2 three deep in plan geometry). That is why
  the strict run-based gate stays; retiring it needs the founder (BENCH_m4s.md "what retiring the strict gate needs").
- **Travel gate on a raster timeline**, not shapely: per 0.5 mm cell the sew index where earlier fill reaches layer density and
  the last index where later fill still does. Cross-checked against exact plan geometry (independent): M2 5.6 m raster vs
  5.1 m geometry, M4g 4.6 vs 3.8, main 5.4 vs 5.8 (None-labelled travel). Target 0 exposed stitches (the M5 house standard).
- Travel = label None (dst2 hidden travel + writer ties) + planned role "travel" blocks (found on the file from plan.blocks).

## Crop numbers
See BENCH_m4s.md (proof table + gates x/11 and x/9).

## Left / next
- Founder: approve (or not) retiring the strict run-based stack gate in favour of the part gate (BENCH_m4s.md).
- The travel gate fails every crop file (~2,000 exposed stitches, ~5 m): the fix is in dst2's travel mask (it counts this
  stop's already-SEWN fills as cover: MERGE_LATER) or M5's `exact_travel unsewn_only` for the crop; not in this PR.
