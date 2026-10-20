# RECAP 2026-10-20: ENGINE_PLAN M4c (chaos: radial-floret exemption + crown clumps)

Branch `engine-m4c-chaos` (off origin/main 89a16e8). Builder worktree. Parallel builders: M4s (stack + travel gates), KOI.
Write-up with all numbers: projects/castle-falls-jacket/bench/BENCH_m4c.md.

## 1. Radial-floret exemption
- `engine/digitize/gates_radial.py` (new): `exempt()` reads the real chaos tiles from `qa.direction_match`. A tile is let
  out only if >= 70 % of its visible stitch length (>= 0.6 mm) belongs to FLORET-SIZE radial parts (mode radial, meta
  centre, farthest outline point <= 4 mm from it) AND >= 85 % of those parts' visible stitches in the tile are within
  15 deg of their ray. `rebucket` moves exempt tiles into a "radial" bucket.
- Numbers: `rules/house.yaml` `chaos_radial_exemption` (appended `# --- M4c ---` block). The 5 % threshold in
  bench.json is untouched (pinned by a test).
- Hooks (small, appended): run.gates (`row["radial_exemption"]`, `direction_by_source_raw`); bench.verdict
  (direction_chaos reads `pct_chaos_after` when present); bench.md_row (chaos cell "raw; after"); panel (exempt
  tiles orange, heat title shows raw and after).
- **Crop result: 0 tiles exempt.** The radial share in chaotic tiles is at most 0.56: canopy and travel carry most of
  the thread. The gate stays honest. The rest of the chaos is canopy, travel and village.
- Decision: exempted tiles leave their source bucket entirely (a partition). That would raise the source bucket's
  pct_ok, so `direction_by_source_raw` keeps the unmoved figures. Flagged in the PR.

## 2. Crown clumps (crown.py + construct rule fan_smooth)
- Small lit pieces are grown to a visible size (never dropped). Dark slivers join the lit piece. One angle per clump.
  The fan is smoothed across touching clumps. Where rule 3 cannot separate a clump after smoothing, the clump keeps
  its own axis.
- Audit: `fan_smooth` is rebuilt from the stored axes. A dark clump's own axis is checked against the dark part plus
  its own lit pieces (peers via lit_of). This was the r1 bug: foliage.216 counted as a random angle.
- Crop: unseen lit 27 -> 0, crown chaos 25 -> 15, crown off-grain 16 -> 28, coherence 110 -> 78, chaos 24.8 -> 23.4 %.
  Gates 2/9 -> 1/9: one satin blob from a block-join zig-zag in a small clump on the crop edge (shared dst2/compile).

## Runs (scratchpad m4c/)
base = main; r1 = first crown version (sep 28, 1 random angle); r2 = final (scored row).

## Tests / guards
tests/test_digitize_m4c.py: 16 tests. scratchpad m4c/mutate.py + extra_mut.py: 24 mutations, all RED, restored green,
git clean. Full suite 218 passed. Identity: dst2 probe 84ff50ea74938675 / 1ecd8f657db3f53a, M5 wb 449c14f6e8f693b6.

## PR #14 review fixes (CHANGES -> this push)
1. Denominator loophole: `rebucket` used to drop exempt tiles from their source bucket's denominator, raising the
   independent pct_ok that direction_ok reads (99/194 -> 99/184 with 10 exempt). Now the source buckets are untouched
   (gain only a `radial_exempt` count) and "radial" is a view. Red test: `test_exemption_cannot_raise_the_direction_ok_inputs`
   (3 mutations red: counted OK, denominator shrink, pct_ok-only shrink through bench.verdict).
2. LESSONS numbered A31 / B38 / B39 (after the merge of PR #13/#18/#19: main took A30, still ends B37). B39 = the block-join satin blob.
3. SEAM_MM["crown_clump_lit"] = 0.3 (sequence.py, appended). r2 -> r3: density flags 181 -> 174, p95 9.84 -> 9.65,
   area > 7: 62.0 -> 56.8 cm2; no bare cluster at any lit seam (0 of 83 clusters >= 0.1 mm2 within 0.5 mm of a lit
   outline). Cost: trims 144 -> 152, unseen florets 7 -> 10, chaos 146 -> 149 tiles.
4. Lit growth per part: crown lit parts carry meta `lit_growth` (traced_mm2, grow_mm, added_mm2, pieces), written to
   parts_summary.json per part + a total (73 pieces, 44 grown, traced 2,209 mm2, added 509 mm2, max 1.5 mm).
Merged origin/main f8acc64 in (family-tee only, no conflict). Crop DST r3 b0fcbbf67618a2d3. 28 mutations red, 238 passed.

## Left
- Blossom chaos: canopy broken around the florets, and travel over the canopy (M4s travel gate).
- Satin blob from the block join (dst2 / compile), LESSONS B39: two tatami blocks of one part joined by a 3.8 mm stitch
  instead of a trim at garment (-56.4, 369.3). Fix + unit test in dst2 / compile in a SEPARATE PR.
- Density still 174 flags vs 167 on main; trims 152 after the seam change (route order in the crown stop).
- Smoothing trades chaos for off-grain in crowns. A grain-aware fan would need the reference (self-derived, A24).
