# RECAP 2026-10-19/20: ENGINE_PLAN M1 (parts-based digitizing skeleton) + M0 review follow-ups

Branch `engine-m1-skeleton` (off 73ae3dd). Command:
`PYTHONPATH=engine python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api`
-> `projects/castle-falls-jacket/out/digitize/BK_M_crop/` (git-ignored) + one SCOREBOARD/BENCH row + panel PNG.

## Part A: M0 follow-ups
- **wave-jacket/gates.py**: at PPM 4 the direction gate now stops with a readable SystemExit (why + how to fix); `--art`
  still skips the DST gates. Minimal on purpose (Wave is paused, M8).
- **Reference quality**: `register.reference` returns `closeup_weight` and `source_ppm` per pixel + `source_ppm_median`
  (2.58 px/mm in the crop: 12 ppm is a sampling grid, not detail). `qa.direction_match(weight=, min_weight=0.6)` masks
  tiles (count in `masked`); bench passes the weight.
- **Thresholds now tested**: stack_map `layer_min` (travel line), satin_runs `turn_deg` (100-degree zig-zag),
  `len_ratio` (1.0/0.3 back-stitch walk), bean (doubly guarded: reversal AND advance; only removing both goes red).
- **angle_coherence**: `no-visible-stitches` flag; `seg_parts=` attributes stitches by part id (a neighbour's 1 mm
  cut-under overlap no longer counts against a part). `qa.visible_segments(return_index=True)` carries ids through.
- **BENCH.md**: baseline angle_coherence FAIL = plumbing note; trims labelled per 100 cm2 of covered area; reference
  quality note. bench.py panel titles come from `bench.json` `panel_labels` (`digitize/panel.py`).

## Part B: what was built (engine/digitize/)
| module | role |
|---|---|
| schema.py | Part / Layer / DirSpec (raises on "auto"/None) / StitchSpec / Block / ObjectPlan, JSON + WKT |
| config.py | run.yaml (PyYAML; JSON fallback; clear error if YAML without PyYAML) |
| rules/house.yaml + rulebook.py | kinds sky_band, sky_blend, fall_cord, pool, zone_stub; first enabled technique wins, none = RulebookError; founder numbers pinned against the principles doc text |
| techniques/ | registry; tatami (staggered, short rows get a penetration), satin (column, promoted kjsatin -> column.py), split_satin (staggered, direction-invariant phase; fixed-angle or column), run, bean |
| extract/evidence.py | tone trace (CIEDE2000 to the run palette + mode filter) + structure-tensor grain: evidence only |
| extract/zones.py + bench/zones_BK.json | windows + tone families; sequential claim-and-split (unused pixels go back to lower zones) |
| splitters/ | sky (row-vote bands + blends), fall (silhouette -> medial-axis cords, alternating tones, 90 deg), stub (tone components >= 20 mm2, absorb smaller, field-mean angle), pool (same partition at 0 deg) |
| sequence.py | underlap (traced neighbours get 1 mm under the higher one), cut_under (keep 1 mm), absorb_fragments, z-DAG + colour batching |
| threads.py | <= factory needles, CIEDE2000 x min(weight) greedy merge, protected never merge |
| compile.py + dst2 hooks | `make_pattern(builder=, keep_order=, threads=)`; stats["labels"] = part id per STITCH |
| review.py / panel.py / run.py | part_map.png, questions.json, 5-column panel, CLI stages |

## Decisions
- **Fall cords sew with VERTICAL stitches** (split satin at 90 deg, rows down the water). Stitches across a vertical
  cord would be 90 deg off the reference grain (the structure tensor sees the cords' vertical stripes).
- **Zone stubs split by thread tone** inside the zone (a zone = window + tone family), not one blob per zone: keeps
  red/gold accents as their own parts (protected minimum 4 mm2) and colour fidelity, while every part has one angle.
- **Thread palette** = cfcore.CF_PAL (18 proposed tones) in run.yaml; merged to 12 by area-weighted dE. Side effect:
  `cf_skylt` and `cf_sky` merge away (small area), so the falls lose their light-blue streaks (cream / mist cords only).
  M4's importance weighting should keep a water blue.
- **Short-row rule**: a tatami / split-satin row shorter than a stitch is one stitch; a run of them IS a satin on the
  file (31 blob satins on the first crop run). Every such row now gets a staggered penetration -> 0 satins/blobs.
- **Split stagger bug found by the test**: phases measured from the sewing direction re-aligned every other row in a
  zig-zag; phase is now measured from the same side regardless of direction.

## Red -> green (mutation proofs, scratchpad mutate.py; all 20 RED, restored 20 green)
stack_map layer_min 1.5->0.5; satin_runs turn_deg 120->90; satin pair without reversal+advance; len_ratio 2.5->4;
no-visible flag dropped; seg_parts ignored; weight mask ignored; split PHASES (0,0,0); flip=False; cut_under keep 0;
protected ignored in threads; rulebook returns first technique; house.yaml satin max 8; principles doc keep ~2 mm;
dst2 builder ignored; keep_order regs sort; keep_order router; tatami split_short off; split_satin min_pieces=1;
DirSpec accepts "auto". Default make_pattern output is byte-identical to 73ae3dd on a 28-region motif.

## Crop numbers
BENCH.md section "M1 skeleton" + scoreboard row. Direction 11.7 -> 89.0 % OK (falls 98.4 %, sky 100 % of 2 tiles,
stubs 88.0 %), chaos 77.9 -> 7.0 %; 381 parts, 0 undeclared/random angles; 0 satins/blobs (was 1159 blobs); red + gold
sewn; 12 threads; trims 113.1 -> 33.0 per 100 cm2 covered; density flags 194 -> 78; max stack 6 -> 5; 3/8 gates
(was 0/8). Coherence fails (109) are all stubs/pool.

## Next (M2+)
- Stubs are the weak part: chaos tiles sit in village/ground stubs; coherence fails = small buried parts
  (no-visible-stitches) and large stub parts whose visible stitches spread (edge hops, multi-polygon parts).
- Density / stacking flags concentrate where 3+ zones meet (underlap grows a part under every higher neighbour).
- Trims ~33 / 100 cm2 covered (target 25): stops are colour-batched across the crop; M4 sequencing.
- Sky is tiny in this crop (2 tiles); the sky splitter needs a crop with real sky to be judged.
