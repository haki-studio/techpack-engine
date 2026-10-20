# Bench: M4g (thread planner, full sequencing, review step), Castle BK M crop, 20 Oct 2026

Run with the M2 parts (M3a / M3b not merged; numbers move again when they are). Command:
`PYTHONPATH=engine python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api`
(scored through a scratchpad copy of that yaml with label "M4g sequencing + thread planner + review step"; the
engine commit key is the last commit outside bench/). Every number below is from `gates.json` / `plan.json` of that run;
DST sha256 f4a6545a46672615. Reproduce the M2 sequence with `sequence: {planner: m1}` in the yaml.

![M4g panel](panel_2026-10-20_m4g-sequencing---thread-planner---review.png)

| check | M2 (40357b5 / 71f0097) | M4g | target | |
|---|---|---|---|---|
| direction, INDEPENDENT tiles (gate) | 98.6 % of 73 (11.7 % coverage) | 98.6 % of 73 (same parts) | >= 85 % on >= 50 % | FAIL (not evidenced; M3) |
| (combined, info) | 91.7 | 91.4 | | |
| chaos, all tiles | 4.2 | 4.6 | <= 5 % | OK |
| parts / under 20 mm2 | 367 / 11.2 % | 367 / 11.4 % | <= 400, < 25 % | OK |
| angle_coherence fails (fixed fills) / field adherence | 61 / 94.4 % | 50 (14 buried + 36 spread) / 94.2 % | 0 | FAIL (stubs: M3) |
| separation close pairs | 46 | 42 | 0 | FAIL (stubs: M3) |
| density flags / mean / p95 | 113 / 4.57 / 8.41 | **40 / 4.33 / 7.63** | 0 | FAIL (fewer) |
| ... flags by zones meeting (1 / 2 / 3 / 4+) | 11 / 69 / 27 / 6 | 7 / 29 / 4 / 0 | | |
| max stack / area over 2 | 4 / 9.07 cm2 | **4 / 1.0 cm2**, 0 flagged regions; plan geometry max 2 | <= 2 | FAIL (see below) |
| trims per 100 cm2 | 26.5 (106) | **22.2 (89)** | <= 25 | **OK** |
| colour stops (12 threads) | 22 | **20** (0 z-DAG violations) | min 12 | |
| stitches file / planned travel | 93,036 / 11,132 travel st | 90,922 / 8,920 travel st | | |
| colours | 12, red + gold | same threads (choice "default") | <= 12, red + gold | OK |
| gates | 3/9 | **4/9** (+ trims) | | |

## What moved it, measured (ablations on the same parts, scratchpad m4g/)
| step | trims /100 cm2 | density flags | stack max / cm2 > 2 | coherence fails |
|---|---|---|---|---|
| M2 | 26.5 | 113 | 4 / 9.07 | 61 |
| order_v1 + stack cut (no orientation) | 20.8 | 127 | 6 / 10.48 | 53 |
| + orientation, blocks re-ordered nearest-next (first try) | 19.5 | 49 | 4 / 5.89 | 113 (travel on sewn rows) |
| + orientation keeping the technique's cell walk (chains) | 21.2 | 74 | 4 / 7.21 | 52 |
| + stack reach 1 mm | 21.2 | 29 | 4 / 3.53 | 50 |
| + inner travel (underlay paths, narrow-neck fallback) | 20.2 | 33 | 4 / 0.96 | 53 |
| + stop lookahead (22 -> 20 stops) = M4g | 22.2 | 40 | 4 / 1.0 | 50 |
Tried and dropped: trimming hidden travel over 30 / 15 mm (dst2 opt-in): trims 36.5 / 50.2, stack unchanged (4 / 3.5).
Planning travel between TOP cells through the unsewn area: trims unchanged, coherence 50 -> 56, plan stage 150 s.

**Density.** The planned blocks alone (top + underlay) give 7 flags; the M2 file gave 113: the excess was the
router's TRAVEL, not underlap. 31 m of the 44 m of straight-line moves were inside parts, block to block (an edge-run
ring ending opposite where the lattice starts, the lattice ending opposite the top's first row). Planned entry / exit
(rings start at the vertex nearest the needle, chains sewn forwards or whole-backwards by a small dynamic programme,
underlay units nearest-next) cut the moves 53 -> 32 m.

**Stack.** At plan level the part geometry is now at most 2 deep everywhere (`limit_stack`: the lowest of 3 loses the
area, nothing visible changes). The file gate counts sewn RUNS per 1 mm cell; of the 96 cells still over 2: 63 are
junction cells where three parts meet in one 1 mm cell but no point is 3 deep (each part's edge run + partial fill
reaches the 1.5 mm/mm2 layer threshold), 23 are cells where a run's hidden travel crosses, 10 are 3 deep. The gate was not
changed. Before the inner travel, 149 cells were ONE part split into 2-4 runs by trims inside it (the underlay of
blossom.015 / foliage.266 counted as its own layer).

**Stops vs trims.** The stop look-ahead saves 2 colour changes (22 -> 20) and costs 8 trims and 7 density flags on this
crop (`sequence.stop_lookahead: false` gives 20.2 trims / 33 flags at 22 stops).

## Thread trade-off (a QUESTION, not decided): `threads.choice` in run.yaml, or answer `threads.tradeoff`
| option | what it costs instead (merges vs the default) | worst dE |
|---|---|---|
| default (importance {skylt 3, rose 3}) | mist grey -> sky light (14.9) | 16.5 |
| keep_cf_mist (mist AND sky light) | cloud cream -> mist grey (15.0): the cloud whites go grey | 16.5 |
| keep_cf_pinklt | cloud cream -> blossom pale (19.7) | 19.7 |
| keep_cf_sky (sky blue AND slate) | sky light -> sky blue (18.7), mist grey -> cloud cream (15.0) | 18.7 |
| keep_cf_grnlt | cloud cream -> moss light (20.2) | 20.2 |
| saliency (contrast x motifs) | leaf green -> pine dark (18.6) | 18.6 |
Optical mixes the question lists (not sewn; a mix is a second layer): mist grey as 50 % cream + 50 % slate dE 5.2 (vs 14.9
merged); sky blue as 50 % sky light + 50 % navy dE 6.1; blossom pale as 50 % cream + 50 % pink dE 6.7.

## Review round trip on the crop (scratchpad m4g/answers_crop.json)
Answers `threads.tradeoff: keep_cf_mist`, `direction:low_grain:village: 0 deg`, `zone_stub:ground: accept stub`, plus an
unknown `q001`: the next run reported 3 answered, 10 left at their default (listed), 1 unknown; its threads hold cf_mist
and not cf_cream; the 6 low-grain village parts sew at 0 deg with source "answer"; random angles 0.
