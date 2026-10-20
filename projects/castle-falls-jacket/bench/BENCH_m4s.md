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
| limit_stack PARTIAL, current main (fresh mutation run, `sequence.max_layers: 3`, see note) | b0906325a2cc15a5 | 17.62 cm2 | 6 / 30.56 | 811.9 mm2 | 320.6 mm2 | 80.27 | **FAIL** |
| M4g alone (known good) | 239edce864f8fdd3 | 0.00 cm2 (max 2) | 4 / 4.41 | 21.1 mm2 | 0 | 0.00 | **PASS** |
| current main crop | 1963d24fc2d3d862 | 0.02 cm2 (max 3) | 5 / 19.78 | 94.2 mm2 | 4.3 mm2 (1) | 1.08 | **PASS** |

**Mutation note.** The fresh run with limit_stack fully OFF (`sequence.max_layers: 99`) on current main never finished:
it sat 3.5 h in the plan stage (CPU 2:57 h, killed by PID) because, with nothing cut, the rule-6 stack checks enumerate
k-part combinations over the many overlapping village / crown parts. So the fresh real-file mutation is a PARTIAL cut,
`max_layers: 3` (limit_stack still runs but allows 3 layers and cuts only 4+ deep): plan geometry goes 0.02 -> 17.62 cm2
three deep and the part gate goes 1.08 -> 80.27 /100 cm2 (FAIL, 32x the cap). The full-off mutation is represented by the
older run on M4g code (`BK_M_crop_nostack`, limit_stack off, 3.84 cm2 three deep: FAIL at 6.19).

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

### The 4 mm2 floor and the 2.5 /100 cm2 cap, justified WITHOUT the main crop
**Floor 4 mm2.** Two independent reasons, neither uses a crop file:
1. It is the strict gate's own flag size (`qa.stack_map(min_flag_mm2=4.0)`, set in M0, before M4s).
2. Derived from the house rules on synthetic junctions (scratchpad `m4s/junction.py`): parts built with keep_mm 1.0
   underlap, cut by the REAL `sequence.limit_stack` (reach 1.0, keep_band 1.0), every part sewn with pull comp, rows 0.35-0.45
   mm. The largest over-2 speck a CORRECT junction leaves on the file:

   | junction | plan geometry >= 3 deep | pull comp 0.15 | 0.30 | 0.45 mm |
   |---|---|---|---|---|
   | 3-part T (two lower parts under a top one) | 0 | 0 | 0.56 mm2 | 1.00 mm2 |
   | 4-part cross | 0 | - | 0 | 0.88 mm2 |
   | 5-part fan | 0 | - | 0.06 mm2 | 1.00 mm2 (2.06 raw in 3 specks) |

   A correct junction leaves <= 1.0 mm2 per speck even at 0.45 mm pull comp; 4 mm2 is 4x that.

**Cap 2.5 mm2 per 100 cm2.** Set from the KNOWN files only: known-good M4g file = 0; known-bad M2 = 5.88, limit_stack off
(M4g code) = 6.19, limit_stack partial (current main) = 80.27. Any cap in (0, 5.88) separates them; 2.5 is < half of the
smallest known-bad value, so a file with HALF of M2's stacked area still fails, and it equals ONE floor-sized (4 mm2) region
per 160 cm2. Sensitivity, stated plainly: the main crop (1.08 = one 4.3 mm2 region in 400 cm2, at a village junction
whose plan depth is 2: wall / canopy / window / roof) passes for any cap >= 1.08 and FAILS at cap 0 ("not a single region")
or with the floor lowered to 2 mm2 (then 3.05 /100 cm2: four village regions 2.3-4.3 mm2, plan depth 2 in all). Main was
not used to set either number, but its verdict is not robust to them: the founder sets both if the strict gate is retired.

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
| M5 Konpeito wb (svgrun, DST 449c14f6e8f693b6) | 15 | 14.9 mm | 336 mm (44 cm2 covered) | 0 | M5's own gate `exposed_stitches`: 0 | FAIL (report only: wb is not in the crop verdict) |

The independent check uses no raster: for each travel stitch, its length inside the union of fill parts FULLY sewn
before it minus the parts whose first stitch comes after it. It agrees with the raster to within ~20 % (the PR #8
reviewer measured M2 4.9 m, M4g 3.3 m on the first M4g file f4a6545a46672615). Looked at: the live view zoom at
(-110, 432) on main shows a faint same-colour diagonal across the blue fill where the gate draws the stitch
(scratchpad m4s/zoom_main_travel2.png).

Why the crop has so much: dst2's hidden-travel mask counts ALL of the current stop's own fills as cover, sewn or not
("travel under an object that is about to be sewn over"); once those fills are sewn, travel across them lies on top.
M5's `exact_travel: {unsewn_only: true}` is the existing fix (used on patches); not switched on for the crop here.

**The new gate DISAGREES with M5's on the wb patch (15 vs 0), and why.** `qa.exposed_stitches` accepts any stitch of a
stop that lies on that stop's OWN art (+0.25 mm halo) or under later art: by construction it cannot see travel on top of
art of the same stop that is already sewn. The 15 are: 12 dst2 travel hops of 0.9-2.5 mm (0.36-1.48 mm of each on sewn
fill) between consecutive petals / letters / line-art parts of one stop (petal 06.006 -> 06.007, lettering 15.008 ->
15.009, ...), each lying on the part just sewn, and 3 writer tie stitches (0.50-0.58 mm) on line art sewn just before. M5's `unsewn_only` routing keeps longer travel off sewn art; these short straight hops are not routed. They are
real thread on top of a sewn satin (short, same colour). The tie stitches are the writer's lock stitches (standard, buried
in the satin texture); a follow-up could drop writer-added segments from "travel" (labelled_dst counts them:
writer_added 670 on wb). Nothing is changed in M5 or the wb file by this PR (DST still 449c14f6e8f693b6).

## 3. Crop verdict (current main code + M4s gates)
Re-run on this branch after merging origin/main (crop DST 1963d24fc2d3d862, unchanged: the M4s gates read the file, they
change nothing in it). Scored only, no SCOREBOARD row added (the file is the M3b row's file; a new row would duplicate it).

| gate | main crop | limit_stack partial (mutation) |
|---|---|---|
| direction_ok (independent 49.5 % of 194) | FAIL | FAIL |
| direction_chaos (24.8 %) | FAIL | FAIL |
| angle_coherence | FAIL | FAIL |
| density (167 flags) | FAIL | FAIL |
| trims (36.8 /100 cm2) | FAIL | FAIL |
| satin_shape | PASS | PASS |
| stack (strict, runs per 1 mm cell: max 5) | FAIL | FAIL |
| colours | PASS | PASS |
| separation | FAIL | FAIL |
| **stack_parts (NEW)** | **PASS (1.08)** | **FAIL (80.27)** |
| **travel_on_fill (NEW)** | **FAIL (2,487 st, 5.82 m)** | **FAIL (2,490 st, 5.81 m)** |
| **total** | **3/11 (old 9: 2/9)** | **2/11 (old 9: 2/9)** |

The old 9 are unchanged (2/9 on main, as before M4s).

## Mutations (scratchpad m4s/mutate_m4s.py): 20/20 RED, restored green
max_parts 2 -> 3; erosion off by default; region filter dropped; region filter inverted; travel (None) counted as a part;
line parts counted as layers; stack: empty raises nothing; stack: window 0.75 (aliasing); travel: 'sewn before' test
dropped; travel: burial test dropped; travel: min_ex raised past the stitch; travel: planned travel ignored; travel:
index returns nothing; travel: empty raises nothing; run_hook: line parts not passed; run_hook: planned travel not
passed; verdict: stack cap ignored; verdict: exposed target ignored; verdict: M4s lines not called; summary: old 9 not
separated. Plus the real-file mutation: limit_stack off (`sequence.max_layers: 99`) on current main -> part gate FAIL.
