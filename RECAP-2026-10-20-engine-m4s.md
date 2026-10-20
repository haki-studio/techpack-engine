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

## Crop numbers (BENCH_m4s.md has all of them)
| file | plan >= 3 deep | strict stack | part gate /100 cm2 | travel on fill |
|---|---|---|---|---|
| M2 0d86f00be8e9f8fa | 3.84 cm2 | 4 / 9.07 | 5.88 FAIL | 1,937 st / 5.64 m |
| limit_stack off (M4g code) 9db212085de09b6d | 3.84 cm2 | 5 / 8.67 | 6.19 FAIL | 1,761 st / 4.82 m |
| limit_stack partial, max_layers 3 (current main) b0906325a2cc15a5 | 17.62 cm2 | 6 / 30.56 | 80.27 FAIL | 2,490 st / 5.81 m |
| M4g 239edce864f8fdd3 | 0.00 cm2 | 4 / 4.41 | 0.00 PASS | 1,800 st / 4.79 m |
| main 1963d24fc2d3d862 | 0.02 cm2 | 5 / 19.78 | 1.08 PASS | 2,487 st / 5.82 m |
Main crop gates: 3/11 (old 9: 2/9). The full limit_stack-off run on current main hung 3.5 h in plan (killed by PID);
the partial cut (max_layers 3) is the fresh real-file mutation.

## Left / next
- Founder: approve (or not) retiring the strict run-based stack gate in favour of the part gate (BENCH_m4s.md "what
  retiring the strict gate needs": floor, cap, the thin-band blind spot).
- The travel gate fails every crop file (~2,000 exposed stitches, ~5 m): dst2's hidden-travel mask counts all of the
  current stop's own fills as cover, sewn or not; M5's `exact_travel: {unsewn_only: true}` is the existing fix (patches).
  Switching it on for the crop (trim cost to measure) is the next PR, not this one.
