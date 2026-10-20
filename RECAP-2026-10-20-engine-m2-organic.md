# RECAP 2026-10-20: ENGINE_PLAN M2 (organic parts) + M1 review follow-ups

Branch `engine-m2-organic` (off origin/main 755faf6), builder worktree. Command:
`PYTHONPATH=engine python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api`

## Part A: M1 review follow-ups (done first, commits dc6de1a..772081f)
| # | what | where |
|---|---|---|
| 1 | `random_angles` derived: `audit.angle_audit` re-derives every declared angle from its source (rule number, measured field angle, answer, depth rule) + recorded adjustments within house limits; anything else counts | audit.py |
| 2 | split-satin cord gate from the DST: `qa.split_satin_rows` (rows, pieces <= 7.1 mm incl. 0.1 mm grid, aligned split fraction > 0.5 = seam, column width); folded into the satin_shape verdict | qa.py, run.gates |
| 3 | direction tiles by source: independent (rule/answer/depth) vs self-derived (field-mean/field) vs outline (contour) | audit.direction_by_source |
| 4 | gates read the WRITTEN DST: `compile.labelled_dst` matches the plan's labelled segments onto `qa.dst_segments(dst)` in sew order; a missing planned stitch raises | compile.py, run.gates |
| 5 | thread `importance` (x area in the merge cost); Castle crop: `{cf_skylt: 3, cf_rose: 3}` | threads.py, run_bk_crop.yaml |
| 6 | bench idempotent: same label + git sha replaces its json row and BENCH.md line | bench.append |
| 7 | LESSONS A19 (no-visible-stitches: flag, never pass; fix upstream) and A20 (gates on the file, audited angles) | LESSONS.md |
| LOW | split_row docstring no longer promises "never aligned"; stub raises instead of a silent 0 deg; column.py jitter fenced (legacy only, test) | |

Re-scoring M1's plan with the file-based gates gives the same numbers (89.0 % OK / 7.0 % chaos, coherence 109 fails):
the file and the plan agree (84,467 file segments, 83,883 planned matched, 584 writer-added ties, 23 sub-grid).
M1 by source: independent 95.8 % of 71 tiles, self-derived (field-mean stubs) 88.0 % of 552.

### Thread trade-off (decision)
12 needles, 18 candidate tones, red + gold protected. Options measured on the crop's evidence weights:
- importance {skylt 3, rose 3}: keeps sky light (falls' blue streaks) + blossom deep; merges mist grey -> sky light (dE 14.9). CHOSEN.
- {sky 3, skylt 3}: both blues kept but blossom deep -> pink (dE 18.6) and mist -> sky light.
- {sky 3, rose 3}: sky blue kept, but cloud cream -> mist (the cloud whites go grey).
Founder can move it with the numbers in run_bk_crop.yaml.

### Red -> green (scratchpad mutate_m2.py), follow-ups: 8/8 red, restored green
audit skips comparison; split PHASES (0,0,0); cord gate ignores seam; labelled_dst no missing check; field-mean
bucketed as independent; importance ignored; bench always appends; satin via column_pts (jitter).

## Part B: M2 organic parts (commits 99af6e1..4dae159, bench row at 4dae159)
| module | role |
|---|---|
| direction.py | `Field` (structure tensor of the input pixels; thread = gradient + 90; smoothed 4 mm, weak grain < 0.25 filled from 10 mm), `grid()` stored in part.meta["field"], `phase()` / `solve_phase()` (least-squares phase field: rows = level sets), `separate()` (rule 3, turn <= 25 deg off the evidence), `separation_report()`, `depth_angle()` |
| techniques/guided_fill.py | tatami along the field: phase-field rows, cell walk like dst2.chain_rows (stop at splits / merging runs, hop <= 1.5 mm), brick stagger, split_short |
| techniques/contour_fill.py | rings inset from the outline, outside in |
| techniques/blend.py | feather (two-colour accordion, golden-ratio reach, from meta blend_from) / open layer (chain_rows); no underlay; stype run (does not hide travel); `open_layer` -> nothing cut under it |
| sequence.py | `is_open` (cut_under skips open layers), `merge_specks` (traced parts < 20 mm2 merge into the neighbour with the longest border; cracks / wisps / shades exempt) |
| splitters/stratum.py | per rock mass: field, phase across the bedding, bands at tone changes (4-16 mm), band x thread parts (>= 30 mm2), +-10 deg alternation, cracks (black top-hat, thin, >= 8 mm) as run on top |
| splitters/cloud.py | silhouette, wisps (what a 3 mm opening removes), lobes (watershed of the distance transform), back lobes first, lit thread per lobe, darker tones as open shade layers |
| rules/house.yaml v1 | stratum_band, stratum_crack, cloud_lobe (guided -> contour -> split satin 80 -> tatami 80), cloud_shade (blend open, no underlay), cloud_wisp (0 deg, 0.9 spacing); sky_blend -> blend feather; `dir: field / contour`, `alt_dir`, `dir_by_technique`, kind `params` |
| zones | `except` (cut other zones' windows), `close_mm` (claim enclosed specks) |
| run.py gates | coherence on FIXED-angle fills only; guided parts judged by field adherence (>= 85 % of visible stitches within 15 deg of their planned field); stub area; separation report |

### Decisions
- **Cloud lobes use the turning (guided) fill**, not contour fill: contour rings on the cloud scored 33 % of 6 tiles and
  read as fingerprints; guided rows along the lobe's grain look like the reference's horizontal rows (83 %). contour_fill
  stays a tested plugin (toggle guided_fill off to use it).
- **Field smoothing 4 mm** (not 2.5): stratum tiles 90.9 -> 92.7-93.5 %; also keeps the plan field from being the gate's
  own 2.7 mm tensor.
- **merge_specks** (rule 1, A19): 326 of 693 traced parts were specks; merging them cut parts 823 -> 367, no-visible
  fails 412 -> 12 and trims 283 -> 111. Applied to every zone (village / blossom stubs too).
- **Open layers cut nothing under them** (M1 bug: the sky band was cut away under its own blend).
- **Coherence scope**: angle-spread is a rule for fixed-angle parts; a guided part varies on purpose and is checked
  against its own field instead. Line parts (run / bean) are excluded.
- **Separation limit**: the first run turned 12 parts up to 30 deg off their evidence; the audit flagged them as
  unexplained; turns are now capped at sep[1] = 25 deg (unresolved clashes recorded).
- **Cracks** at top-hat depth 35: 19 found on the crop (depth 25 gives 27). A founder-eye threshold.

### Crop table (BENCH.md "M2 organic parts"; first PR at 4dae159, after the review fixes at 9d0c4cf)
| | M1 | M2 first PR (4dae159) | M2 after review (9d0c4cf) |
|---|---|---|---|
| direction gate: INDEPENDENT tiles | 95.8 % of 71 | 97.3 % of 73 | 98.6 % of 73 = 11.7 % coverage -> FAIL (needs >= 50 %) |
| (combined, info) | 89.0 | 90.1 | 91.7 |
| chaos, all tiles | 7.0 | 6.2 | 4.2 -> OK |
| organic tiles (same 164) OK / chaos | 90.9 / 8.5 | 92.7 / 6.7 | 93.3 / 6.1 |
| parts / under 20 mm2 | 381 / 18.4 % | 367 / 11.2 % | 367 / 11.2 % |
| random angles | (constant 0) | 0 (basis read from meta) | 0 (basis recomputed from the stored grids) |
| coherence fails | 109 | 53 | 61 + field adherence 94.4 % |
| separation (rule 3) close pairs | - | 29 of 118 (not a gate) | 46 of 118 -> FAIL |
| density flags / max stack | 78 / 5 | 112 / 5 | 113 / 4 (102 flags where >= 2 zones meet) |
| trims per 100 cm2 | 33.0 | 27.5 | 26.5 |
| colours | 12, red + gold, no water blue | 12, red + gold, sky light | same |
| gates | 3/8 | 3/8 (combined direction counted) | 3/9: chaos, satin + cords, colours |
| stub area | - | 60.4 % | 60.4 % |

## Part C: PR #6 review fixes (commits 04c6c3f, 9d0c4cf)
| # | review finding | fix | guard (red -> green) |
|---|---|---|---|
| 1 | re-run on the same commit added a `+dirty` row: the first bench run dirtied the tracked BENCH.md / SCOREBOARD.json | `bench.git_sha`: sha = last commit outside `bench/` folders (a bench-only commit is not a new engine), and changes under `bench/` do not count as dirty | `test_bench_rerun_on_same_commit_through_real_git` (real git repo in tmp): mutations "dirty check counts bench/" and "sha includes bench-only commits" -> red. On the branch: two `bench` runs at 9d0c4cf -> one M2 row |
| 2 | headline direction counted 545 self-derived tiles | `verdict.direction_ok` = independent tiles >= 85 % AND >= 50 % coverage; chaos stays on all tiles (DST only); BENCH row shows "indep. (n of N); all" | `test_direction_verdict_gates_on_independent_tiles`: mutation "gate on the combined rate" -> red |
| 3 | random_angles could be forged via meta field_mean / field_angle | `audit.field_basis` recomputes `direction.grid_mean(meta["field"], geom)` (0.5 deg tol for the 1 micron WKT rounding); stubs + cloud shades store their grid; `direction.refresh_field_basis` re-measures on the final geometry in the plan stage, then separation runs again | `test_field_basis_is_recomputed_not_trusted`: mutation "basis read from meta" -> red |
| 4 | rule 3 unmet on 29/118 pairs, unflagged | verdict line `separation` (close <= 0, stubs included), BENCH section documents it | same verdict test: mutation "separation line dropped" -> red |
| + | density 78 -> 112 explanation | `density.flags_by_zones_meeting`: 1 zone 11, 2 zones 69, 3 zones 27, 4+ 6 (so mostly 2-zone boundaries; my "3-zone" wording was wrong) | info |

Side effect, measured: stub angles now come from the filled 4 mm field grid (not the raw tensor sum): stub tiles
87.5 -> 89.6 % OK, chaos 6.8 -> 3.9 %, which is what moved overall chaos under 5 %. Those tiles are self-derived.
PR #5 (M5) was still OPEN when these fixes were pushed, so main was not merged in.

Default-preserving: `dst2.py` untouched; `make_pattern` default output on a 28-region motif is byte-identical to
origin/main (dst 84ff50ea74938675, pes 1ecd8f657db3f53a, both checkouts; scratchpad byteid.py).

### Red -> green, M2 (scratchpad mutate_m2.py; with the review fixes 27/27 red, all restored green)
field drops +90; guided rows straight (field ignored); guided offset ignored; guided hop (chain limit AND the stitcher's
1.6 mm split, doubly guarded: either alone stays green); contour rings at double spacing; open layer cuts under;
feather not turned to source (first version of the test missed it: source on the hatch's start side; fixed with both
edges); separation threshold 0; merge_specks keep_small ignored; zones except ignored; adherence vs mean angle;
house.yaml band offset 15; stratum sign never alternates; cloud lobes front first. pytest: 114 passed.

## Next (M2b / M3 / M4)
- Stubs are 60 % of the part area: village (buildings), blossoms (florets), foliage crowns, trunks = M3.
- Chaos left on organic tiles = band / stub junctions and weak reference grain; crowns (M3) and junction sequencing (M4).
- Density / stack at part edges (underlap + edge run where 3 zones meet): M4 cut-under / sequencing.
- depth_angle is implemented and audited but no zone on this crop uses it (the cliffs have a clear grain).
- Sky blend (feather) is in the plan but the crop has only 2 sky tiles; judge on a crop with sky.
- Thread trade-off (sky blue vs blossom deep vs cloud cream) needs the founder's call.
