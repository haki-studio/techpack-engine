# RECAP 2026-10-20: ENGINE_PLAN M3a (constructed parts: buildings)

Branch `engine-m3a-buildings` (off origin/main dbd0b0f; origin/main 182a82b with M6 merged in at fdc02d8), builder
worktree. Command: `PYTHONPATH=engine python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api`.
Bench write-up: `projects/castle-falls-jacket/bench/BENCH_m3a.md` (crop table, variant table, gaps).

## What was built
| file | role |
|---|---|
| `engine/digitize/extract/building_fit.py` (new) | template fitter: `fit_line` (trimmed TLS), `split_tiers` (cut stacked tiers joined by a frame), `fit_roof` (eave on the UNOCCLUDED bottom edge, ridge, hips from unoccluded top + side edges, tier height), `eave_band`, `tile_lines` (serpentine with steps along the plane edge), `rect_axis`; rule angles as pure functions of stored points: `roof_angle`, `course_angle`, `across_angle`, `is_far`; `rule_basis(part, rb)` for the audit |
| `engine/digitize/extract/splitters/building.py` (new) | one zone window = one building: roles from `building.roles`, roofs -> planes, walls (lightest thread >= 25 %), features -> window bands / members, ornaments -> studs, leftovers join planes, satin features clipped clear of underlaps, rule-3 separation among its walls / roofs; z offsets walls < roofs (bottom tier first) < eaves < tile lines < windows / members < studs |
| `rules/house.yaml` `# --- M3a ---` | kinds wall, roof (params hip_min_sep 20, hip_max_sep 45, near_tier_mm 22), eave, roof_tile_line, window, member (column_satin first), stud (dot, 1-1.5 mm, no cross underlay); `dir: construct` + `construct:` rule name |
| `audit.py` (3 lines) | source "rule" with `dir: construct` -> `building_fit.rule_basis` (re-derived from stored fit points) |
| `sequence.py` (2 hooks, flagged for M4g) | `merge_specks` skips parts with `meta.keep_small`; `absorb_fragments` reads `meta.min_fragment_mm2` (default unchanged) |
| `run.py` (2 lines) | splitter dispatch `building` |
| `zones_BK.json` | village zone: splitter `building`, five windows (temple, pagoda, castle centre, houses right, bottom roof line) |
| M4g hints (meta only) | `group` = building, `seq_after` = plane ids for tile lines / eaves (coordinator contract; M1 sequencer ignores them) |
| `run_bk_crop.yaml` | label, `building:` roles block, `separate_kinds` + wall / roof |
| `tests/test_digitize_m3a.py` | 12 tests on synthetic buildings / pure functions |

## Decisions (and why)
- **Depth by tier (rule 3) on top of "roofs down the slope" (rule 2).** Measured on the crop: playbook-only gives
  independent 44.1 % OK / chaos 16 %; `near_tier_mm` 15 -> 75.0 % / 5.4 %; 22 -> 79.9 % / 4.3 %. 22 was picked on this
  crop (temple 26 mm near; castle tiers 5-14, one merged pair 20) -> founder question.
- **Far tiers are one plane, no eave satin, no tile lines** (rule 9: too small to read; and an across-satin eave on a
  horizontal band is chaos).
- **Walls square to the eave above** (along under far, across under near): the temple wall reference is vertical, the
  castle walls horizontal; "courses only" scored worse on the temple.
- **Occlusion:** an outline pixel whose outside neighbour (2 px) is not this zone's claim is occluded (blossom crown,
  window / crop edge) and never fitted; eave hidden -> the ridge gives the course line and the tier is treated as near.
- **Satin features clear of underlaps** (rule 6): only 3 more windows survive without it and the stack is unchanged,
  so it stays (`seam_keep_mm` 1.0). Window bands need length >= 3 x (w + 0.25) (sewn width) -> 0 blobs.
- **Studs never touch** (chain pitch >= max_d + 0.5) -> no same-thread 0-deg pairs in separation.
- **Wall ground = lightest thread with >= 25 % share** (the dark outline tone is the commonest pixel but is detail).
- Did NOT change sequence ordering, gates or dst2. Studs flag `no-visible-stitches` (6): kept (A22), gate scope for M4.

## Crop: M2 -> M3a (gates.json at 49aebb8, DST acf15572ac4d0e32; same DST at the merge fdc02d8)
independent tiles 73 (98.6 %) -> **204 (79.9 %)**, coverage 11.7 -> 32.6 % (gate needs 50 %: FAIL); chaos 4.2 -> 4.3 (OK);
trims 26.5 -> **23.3 (OK, new)**; parts 367 -> 324; coherence fails 61 -> 42; separation close 46 -> 24; density flags
113 -> 163; max stack 4 -> 5; satin 0 blobs; colours 12 + red + gold; gates 3/9 -> **4/9**. Village stub area 11,389 -> 0.

## Default-preserving (scripts/identity_check.sh after the merge)
dst2 84ff50ea74938675 / 1ecd8f657db3f53a; wb 449c14f6e8f693b6; crop changes (intended) 0d86f00be8e9f8fa -> acf15572ac4d0e32;
this engine with main's zones_BK.json reproduces 0d86f00be8e9f8fa.

## Red -> green (scratchpad m3a/mutate_m3a.py): 14/14 red, all restored green
front plane along the eave; hips not fanned; wall along the courses under a near roof; studs below windows; old stud
chain count; depth rule ignored; occlusion ignored at the eave; split_tiers never cuts; audit trusts the declared
construct angle; far / near swapped in the basis; no sewn-width allowance; no clearance from lower borders; keep_small
hook removed; min_fragment hook removed. pytest after merging main: 167 passed.

## Left / next
- Temple roof fans in perspective (11 off-grain tiles); hips cannot be fitted when both side edges are hidden.
- Windows: 28 single windows too small for a band, 17 bands dropped at underlaps -> live view loses window rows.
- Plaster walls read tan (evidence classification), not cream.
- Independent coverage cannot reach 50 % from buildings alone on this crop (cliff 160 and stub 245 tiles take field-derived angles).
- Conflict points: sequence.py hooks (M4g), house.yaml / run.py / zones_BK.json / run_bk_crop.yaml appends.

## Part B: PR #9 review fixes (commit cef3c8d, bench row re-scored there; supersedes the numbers above)
| # | review item | fix | guard (red -> green) |
|---|---|---|---|
| 1 | seq_after plane ids could be merged away by merge_specks (M4g raises HintError) | `protect_referenced`: planes named in any seq_after get keep_small | `test_referenced_plane_survives_merge_specks` (a referenced hip shrunk to a 9 mm2 speck touching the wall) |
| 2 | fidelity first: 17 window bands + 7 members dropped at underlaps, far eaves skipped | `seam_keep_mm` off by default (opt-in); every visible eave sewn (trim colour when the edge has no second roof tone); rule-9 minimums listed in plan meta `building_suggest` (run.py, 2 lines) | `test_details_are_kept_at_underlaps_and_small_ones_are_suggested` (2 mutations) |
| 3 | near_tier_mm 22 circular / absolute | `near_tier_rel` 0.75 x the zone's largest tier; audit recomputes h_ref from the zone's roof parts (audit.basis gets the plan's parts) | `test_far_tier_is_relative_to_the_largest_tier_and_runs_along_its_eave` (scene at 1x and 0.5x; mutations: depth ignored, absolute 22 mm) |
| 4 | walls tan, temple wall a red slab | ground = brightest 15 % of the face -> nearest thread; details = role pixels or 60 darker; frames split into rails / posts; dark non-compact outline stays wall | `test_wall_ground_is_the_plaster_not_the_frame` (2 mutations) |

Mutations now 20/20 red -> green (scratchpad m3a/mutate_m3a.py). pytest 170 passed.

Crop at cef3c8d (DST b759f3d3b9a4611e): independent 62.6 % of 203 (32.5 % coverage); chaos 10.7 % (FAIL, was 4.3);
trims 28.8 (FAIL, was 23.3); stack 5 / 17.44 cm2; density 160; separation 25; coherence 48; satin 45 / 0 blobs; 2/9.
The detail (14 window bands, 15 members, 11 eaves) costs chaos and trims; the decision is fidelity first, cost reported.
Stack / density to be re-scored once M4g (PR #8) merges. Variants (scratch): depth off 43.3 %; rel 0.6 = 0.75; rel 0.9
65.5 %; clearance on 67.0 % with 2 windows. 15 of 21 walls cream (2 before), 17 suggestions (7 windows, 10 members).
