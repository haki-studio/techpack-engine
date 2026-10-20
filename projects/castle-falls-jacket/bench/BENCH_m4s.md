# BENCH M4s: part-based stack gate + travel-on-sewn-fill gate (2026-10-20)

Two NEW gates on the LABELLED written file (`compile.labelled_dst`: the plan's part id on every DST segment, None on
dst2's hidden travel and the writer's ties). Module: `engine/digitize/gates_stack.py`. Both are new verdict lines, so
the crop verdict is now **x/11**; the old 9 lines are unchanged and printed next to it (`x/11 (old 9: y/9)`), so every
earlier row stays comparable. **The strict run-based stack gate is NOT retired or loosened.**

## 1. Part-based stack gate (`stack_parts`)

Rule 6 (never more than 2 stacked layers) counted by PARTS. A layer = one part (its underlay + top + edge together)
whose own thread reaches 1.5 mm/mm2 (60 % of a 0.4 mm tatami layer, the strict gate's `layer_min`) in a 1 mm window;
travel (None) and line parts (run / bean) are never layers. Each part's layer mask is eroded by one 0.25 mm cell (a
part is a layer where it is SOLID). Measured: the area of connected regions >= 4 mm2 where >= 3 parts are layers,
per 100 cm2 of covered area. Gate: <= 2.5.

### Proof (prove-the-guard): known-bad must FAIL, known-good must PASS
The independent side is the PLAN geometry (`gates_stack.plan_stack_area`: exact shapely area covered by >= 3 fill
parts, no stitches involved).

| file | DST sha | plan geometry >= 3 deep | strict gate (runs / 1 mm cell): max / cm2 > 2 | part gate: raw cells > 2 | part gate: regions >= 4 mm2 | per 100 cm2 | verdict |
|---|---|---|---|---|---|---|---|
| M2 crop (known bad) | 0d86f00be8e9f8fa | 3.84 cm2 (max 4) | 4 / 9.07 | 142.6 mm2 | 23.5 mm2 (3 regions) | 5.88 | **FAIL** |
| limit_stack off, M4g code (old run, `BK_M_crop_nostack`) | 9db212085de09b6d | 3.84 cm2 (max 4) | 5 / 8.67 | 134.6 mm2 | 24.8 mm2 (3) | 6.19 | **FAIL** |
| limit_stack off, current main (fresh mutation run, `sequence.max_layers: 99`) | MUT_SHA | MUT_PLAN | MUT_STRICT | MUT_RAW | MUT_OVER | MUT_PER | **MUT_V** |
| M4g alone (known good) | 239edce864f8fdd3 | 0.00 cm2 (max 2) | 4 / 4.41 | 21.1 mm2 | 0 | 0.00 | **PASS** |
| current main crop | 1963d24fc2d3d862 | 0.02 cm2 (max 3) | 5 / 19.78 | 94.2 mm2 | 4.3 mm2 (1) | 1.08 | **PASS** |

The M4g file is truly <= 2 deep in plan geometry (exact area 0.00 cm2, `sequence.stack_count` 2), so it must pass, and it
does. The strict gate fails ALL five files (max 4-5), including the one that is <= 2 deep in plan geometry: that is
the junction-cell / crossing-travel problem the reviewer of PR #8 described.

### How the parameters were chosen (sweep on the four existing files)
| variant | M2 | old limit_stack-off | M4g (good) | main | why rejected / kept |
|---|---|---|---|---|---|
| reviewer's literal recipe: 0.5 mm cells, 1 mm window, no erosion, all area | 696 mm2 (1.74 %) | 656 (1.64 %) | 383 (0.96 %) | 1,480 (3.70 %) | M4g flags 1,532 cells of which only 67 are 3 deep in plan geometry: a 1 mm window straddling a seam sees three parts. Does not separate good from bad. |
| 0.5 mm cells + erode 1 cell | 9.8 | 9.0 | 0.3 | 5.3 | erosion of 0.5 mm deletes the 1 mm bands that ARE 3 deep (M2 3.84 cm2 -> 0.1) |
| 0.25 mm cells, 0.75 mm window, erode 1, all area | 100 (0.26 %) | 95 | 11 | 40 | 93 % of M2's flagged cells really 3 deep, but a 0.75 mm window ALIASES: it holds 1 or 2 rows of a 0.4 mm fill, so half of a real layer drops out (a 10 x 10 mm triple overlap measured 48 mm2) |
| 0.25 mm cells, 1 mm window, erode 1, all area | 143 (0.36 %) | 135 | 21 | 94 | main's 94 mm2 is 1,403 cells at plan depth 2 with the third outline within 0.25-0.5 mm (village member + roof + wall, crowns): pull comp of three parts meeting at a junction |
| **same, regions >= 4 mm2 (kept)** | **23.5** | **24.8** | **0** | **4.3** | 94 % of M2's area in regions >= 2 mm2 is >= 3 deep in plan geometry, 0 % of main's. 4 mm2 = the strict gate's own flag size (`qa.stack_map` min_flag_mm2) |

Why a 1 mm window: one row of thread gives 1.0 mm/mm2 (< 1.5, so a lone row or an edge run is not a layer) and a fill
with rows <= 0.5 mm apart gives >= 2.0 in every window.

### Limits (stated, not hidden)
- **It under-counts thin 3-deep bands.** On the M2 file it flags 23.5 mm2 of the 384 mm2 that is 3 deep in plan geometry:
  most of that is 1 mm underlap bands three deep, which the erosion removes. It catches 3-deep AREAS, not bands.
- The cap (2.5 mm2 per 100 cm2) was chosen from these five files: M4g 0, main 1.08, M2 5.88, limit_stack-off 6.19.
  Main passes on one 4.3 mm2 region at a village junction (wall / canopy / window / roof near (-62.9, 501.6)) whose
  plan depth is 2: the third part's pull comp, not a stacked area.

### What retiring the strict run-based gate would need (founder decision, NOT made here)
1. Accept that "max 2 layers" is judged by parts and by AREA: thin junction / underlap bands where three parts' thread
   meets (pull comp, 1 mm underlap) are tolerated, thick 3-deep areas >= 4 mm2 are not.
2. Accept the cap 2.5 mm2 per 100 cm2 (or set another: bench.json `targets.stack_parts_per_100cm2_max`).
3. Accept the blind spot above (thin 3-deep bands), or ask for a follow-up that measures band LENGTH as well.
4. Then: replace the `stack` verdict line by `stack_parts` (one line in bench.verdict), keep `qa.stack_map` reported.
Until then both are shown; the crop keeps failing `stack`.

## 2. Travel on sewn fill (`travel_on_fill`)

Travel = file segments labelled None (dst2's hidden travel + the writer's ties) plus planned role "travel" blocks
(`sequence.plan_inner_travel`, found on the file from plan.blocks). Fill = every other labelled segment of a non-line
part. Per 0.5 mm cell (1 mm window) a timeline: the sew index at which the fill sewn so far reaches layer density, and
the last index after which the fill still to come does. A travel sample is exposed when fill was sewn there BEFORE it and
nothing sewn AFTER buries it. A stitch >= 0.5 mm with > 0.3 mm exposed counts (the M5 patch thresholds of
`qa.exposed_stitches`). Metric: exposed travel mm per 100 cm2 of covered area. Gate: 0 exposed stitches (target 0, the
M5 house standard; bench.json `targets.travel_on_fill_exposed_max` to change it).

| file | exposed stitches | exposed travel | per 100 cm2 | of which planned "travel" blocks | independent check: exact plan geometry (None travel only) | verdict |
|---|---|---|---|---|---|---|
| M2 crop | 1,937 | 5.64 m | 1,410 mm | 0 | 2,079 st / 5.14 m | FAIL |
| M4g alone | 1,800 | 4.79 m | 1,197 mm | 214 st | 1,510 st / 3.75 m (None only: raster 1,586 / 4.58 m) | FAIL |
| current main crop | 2,487 | 5.82 m | 1,457 mm | 376 st | 2,494 st / 5.83 m (None only: raster 2,111 / 5.43 m) | FAIL |
| M5 Konpeito wb (svgrun) | WB_N | WB_MM | WB_PER | WB_PL | M5's own gate `exposed_stitches`: WB_M5 | WB_V |

The independent check uses no raster: for each travel stitch, its length inside the union of fill parts FULLY sewn
before it minus the parts whose first stitch comes after it. It agrees with the raster to within ~20 % (the PR #8
reviewer measured M2 4.9 m, M4g 3.3 m on the first M4g file f4a6545a46672615). Looked at: the live view zoom at
(-110, 432) on main shows a faint same-colour diagonal across the blue fill where the gate draws the stitch
(scratchpad m4s/zoom_main_travel2.png).

Why the crop has so much: dst2's hidden-travel mask counts ALL of the current stop's own fills as cover, sewn or not
("travel under an object that is about to be sewn over"); once those fills are sewn, travel across them lies on top.
M5's `exact_travel: {unsewn_only: true}` is the existing fix (used on patches); not switched on for the crop here.

WB_NOTE

## 3. Crop verdict (current main code + M4s gates)
GATES_TABLE

## Mutations (scratchpad m4s/mutate_m4s.py): 20/20 RED, restored green
max_parts 2 -> 3; erosion off by default; region filter dropped; region filter inverted; travel (None) counted as a part;
line parts counted as layers; stack: empty raises nothing; stack: window 0.75 (aliasing); travel: 'sewn before' test
dropped; travel: burial test dropped; travel: min_ex raised past the stitch; travel: planned travel ignored; travel:
index returns nothing; travel: empty raises nothing; run_hook: line parts not passed; run_hook: planned travel not
passed; verdict: stack cap ignored; verdict: exposed target ignored; verdict: M4s lines not called; summary: old 9 not
separated. Plus the real-file mutation: limit_stack off (`sequence.max_layers: 99`) on current main -> part gate FAIL.
