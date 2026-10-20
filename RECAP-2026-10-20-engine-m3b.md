# RECAP 2026-10-20: ENGINE_PLAN M3b (trees, crowns, florets)

Branch `engine-m3b-trees` (off origin/main dbd0b0f; origin/main 182a82b = M6 merged in). Builder worktree.
Command: `PYTHONPATH=engine python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api`.
Full write-up and crop table: `projects/castle-falls-jacket/bench/BENCH_m3b.md`.

## What was built
| file | role |
|---|---|
| extract/splitters/blossom.py (new) | canopy per mass (deep tone, field-mean, florets + beads knocked out, sewn last); floret centres = lightness peaks; whole 5-petal notched outline per Voronoi cell -> `floret` (radial, mode "radial"); `knot` bead per centre; `radial_adherence` gate |
| extract/splitters/crown.py (new) | clumps seeded by lit highlights; `crown_clump_lit` sewn first, knocked out of `crown_clump_dark`; fan along the clump's long axis from its attachment end (bark pixel within 3 mm, else the mass base) |
| extract/splitters/trunk.py (new) | bark components held by blossom (>= 35 % of a 2 mm ring); `limbs` (skeleton cut at forks, spurs pruned); limb <= 3 mm wide -> `branch` (split-satin column across the centreline, mode contour); wider -> segments at bends -> `trunk_strip`s along the axis (+-10 deg on same-thread neighbours); `column_adherence` gate |
| extract/splitters/construct.py (new) | construction rules axis / column / fan / radial / between_petals; `basis()` rebuilds the angle for the audit; OUTLINE_RULES = fan |
| shared, additive | audit (splitter basis + why, `bucket_of`), schema (DIR_MODES + radial), direction (`NO_SINGLE_ANGLE` contour + radial), sequence (KEEP_SMALL + M3b kinds, KEEP_TINY knot: no underlap growth, 0.5 mm2 floor), run.py (dispatch, NO_FILL_DIRECTION dot out of coherence, `florets_by_part_map`, radial + column adherence into the coherence verdict, splitter_stats in plan meta), review.py colours, house.yaml `# --- M3b ---` kinds, zones_BK (blossom -> blossom, foliage -> crown, new `trunks` zone), run_bk_crop.yaml (label, separate_kinds, M3b blocks) |
| tests/test_digitize_m3b.py | 13 tests |

## Decisions (and why)
- **Florets radial, whole, fitted to their Voronoi cell** (r = 1.35 x distance to the cell edge, 1.5-3.2 mm): clipped
  radials read back as satin blobs; the playbook says radial florets. Petals as 5 separate turning-satin parts were tried
  first: each petal shows < 12 visible stitches -> 787 `no-visible-stitches` flags (A22). One floret = one part.
- **Details first, knocked out** (florets/beads before the canopy, lit before dark): 196 -> 118 trims (B2 / B14).
  Branches before the canopy (playbook lists them last): seam-only difference, fewer trims.
- **Canopy angle = field mean** (rule 45 deg matched 0 % of its area). **Clump fan = long axis** (61 % vs 38 % for
  base->centre); chosen against the reference, so bucketed "outline" (A24 honesty).
- **Bead thread** never the thread around it (deep inside a floret; floret thread when alone): +18 trims, but visible.
- **Trunk zone** = whole crop window + blossom support test instead of hand-drawn tree windows; rock tan / timber fall
  back to the zones below (79 of 96 components).
- M4g hint contract set on the new parts: `knockout_of` (florets, knots -> canopy; lit -> dark) and `group` (mass / tree).

## Crop result (bench row at the merge-with-main commit; DST 62b6a2306a19cb49)
2/9 gates (M2: 3/9): satin + cords, colours. Lost: chaos 4.2 -> 14.2 % (23 floret tiles are radial by construction,
23 crown tiles). Stub area 60.4 -> 27.4 % (blossom + foliage 0). Separation 46 -> 43 close pairs (the M3b zones' share
8 -> 8; village owns 27). Trims 26.5 -> 34.0 / 100 cm2. Floret count: 216 petalled + 83 bead-only vs 339 LoG blobs in
the reference (64 % / 88 %, 48 % matched one-to-one). Radial adherence 99.3 %, column 84.9 %, field 93.8 %.

## Default-preserving
dst2.py / qa.py untouched. scripts/identity_check.sh after merging main: probe dst 84ff50ea74938675 / pes
1ecd8f657db3f53a, M5 wb 449c14f6e8f693b6 (both unchanged); crop DST changed on purpose (0d86f00be8e9f8fa ->
62b6a2306a19cb49). pytest 168 passed.

## Red -> green (scratchpad m3b/mutate.py, 18 mutations, all RED then restored GREEN)
audit trusts the declared splitter angle; OUTLINE_RULES empty; fan support distance unchecked; floret centres 4x apart;
florets not knocked out of the canopy; florets sewn after the canopy; radial adherence vs 0 deg; trunk support off;
skeleton spurs kept; segment axis from the wiggly medial axis; column adherence along; lit not knocked out; lit after
dark; every satin flag re-filed; beads grow in underlap; beads dropped as fragments; radial counted for rule 3; bead
falls back to the floret's thread.

## Gotcha (this session)
`git checkout <file>` to undo a scratch mutation reverted uncommitted work on trunk.py; rebuilt from the edit scripts.
Mutate scripts restore from an in-memory copy; never use checkout to undo.

## Left / next
- Chaos gate vs radial florets: needs a call (exempt radial tiles, judged by radial adherence, or florets at one angle).
- Floret count 64 % and floret size (smaller than the reference domes); overlapping florets back-to-front.
- Blossom pale thread merged away by the 12-needle plan (importance trade-off).
- Crown chaos / coherence (51 crown fails): clumps smaller than an 8 mm tile at different angles.
- Pines show no trunk: clumps attach to dark "bark" pixels that are often shadow.
- Density / stack 5 where branch, canopy, floret and bead meet: M4.
