# BENCH M3b: trees, crowns and florets on the Castle BK crop (20 Oct 2026, PR #10 after review)

Command: `PYTHONPATH=engine python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api`
(label "M3b trees, crowns, florets"), on the tree merged with origin/main after PR #8 (M4g sequencer) and PR #9 (M3a
buildings). Every number is read from `out/digitize/BK_M_crop/gates.json` / `plan.json` of the bench run at the commit in
the SCOREBOARD row (engine 563f4bd); crop DST sha256 `1963d24fc2d3d862`.

![M3b panel](panel_2026-10-20_m3b-trees--crowns--florets.png)

## What M3b adds to the crop
| zone (zones_BK.json) | before M3b (main after #9) | M3b |
|---|---|---|
| blossom (z 7) | zone stubs | `blossom` splitter: 12 canopies (deep tone, florets and beads knocked out, sewn last), 216 radial 5-petal florets, 299 bead knots (83 alone where the floret would be under 1.5 mm radius) |
| foliage (z 2) | zone stubs | `crown` splitter: 84 clumps (seeded by the lit highlights; 67 dark parts survive merge_specks), 77 lit pieces sewn first and knocked out of the dark; 18 `knockout_of` hints re-pointed after merges (incl. the review's foliage.173 -> foliage.172, now -> cliffs.342) |
| trunks (new, z 6.5, bark tones, whole-crop window) | inside the ground stub | `trunk` splitter: 96 bark components, 17 held by blossom (>= 35 % blossom pixels in a 2 mm ring), 49 limbs -> 46 branch columns + 7 trunk strips; the other 79 go back to the zones below |

Florets are **generated, not traced** (A14): the splitter places a whole 5-petal outline at each detected centre; it does
not trace each reference floret's silhouette. It finds 64 % of the reference count (below).

## Crop table: main after #9 (the M3a row) vs M3b merged
| | main after #9 (M3a row, 218d24b, DST c95bbbc796459e7b) | M3b merged (563f4bd, DST 1963d24fc2d3d862) | target |
|---|---|---|---|
| direction, INDEPENDENT tiles (gate) | 62.1 % of 203 (M3a far tiers counted independent) | 49.5 % of 194 (32 % coverage; M3a far tiers now "outline", see below) | >= 85 % on >= 50 % |
| (combined, info) | 80.2 % | 65.3 % | |
| chaos, all 625 tiles | 11.2 % | **24.8 %** (22.2 % without the 39 floret tiles) | <= 5 % |
| parts / under 20 mm2 | 364 / - | 992 / 59.1 % | per kind, below |
| random angles (recomputed) | 0 | 0 (every splitter and M3a angle rebuilt through construct.basis) | 0 |
| angle_coherence fails | 49 | 110 (crowns 60, zone stubs 20, florets unseen 7, buildings 9, canopy 7, trunk 2, ...) | 0 |
| field / radial / column adherence | - | 93.5 % / 96.7 % (7 florets unseen, flagged) / 85.2 % | >= 85 % |
| separation close pairs | 22 | 23 of 244 (M3b zones: blossom 1, foliage 4, ground 5 + ground/village 2) | 0 |
| satin shape + cords | 0 / 0 | 0 / 0 (floret and bead runs re-filed by the part map) | 0 blobs |
| density flags / mean / p95 | 118 / 4.76 / 9.05 | 167 / 5.36 / 9.92 | 0 |
| max stack / cm2 over 2 | 4 / 8.15 | 5 / 19.78 | <= 2 |
| trims per 100 cm2 (trims) | 26.3 (105) | 36.8 (147) | <= 25 |
| colours | 12, red + gold | 12, red + gold | |
| stub area | 38.6 % | 6.9 % (ground only: 3,457 mm2) | 0 |
| stitches (file) / stops | 97,928 / 28 | 125,086 / 32 | |
| gates | 2/9 | 2/9 (satin + cords, colours) | 9/9 |

M2 row for history: independent 98.6 % of 73, chaos 4.2 %, separation 46, stub 60.4 %, trims 26.5, 3/9.

Where the chaos comes from (tiles whose top part is M3b's): canopy 26 of 62, crown dark 21 of 81, crown lit 4 of 28,
florets 25 of 39, branches 5 of 6, trunk strips 2 of 2 = 83 of the 155 chaotic tiles. Building tiles (M3a) also read
more chaotic here than on the M3a row (walls 32.6 -> 44.2 %), because the neighbouring blossom / trunk parts now meet them.

## Parts target, restated per kind (PR #10 review)
"<= 400 parts, < 25 % under 20 mm2" was written for fills. Florets (216, median 12.5 mm2) and beads (299, median 1.8 mm2) are
small BY DESIGN (a floret is one ~5 mm motif, a bead a 1.5 mm stud, rule 9), as are branches. Proposed per-kind target:
fills (stratum bands, cloud lobes, canopy, dark clumps, walls, roofs, pools, sky, stubs, fall cords) <= 400 parts and < 25 % under
20 mm2; motif / detail kinds (floret, knot, branch, trunk_strip, lit clump, window, member, stud, eave, tile line, crack,
wisp, shade) counted against the REFERENCE motif count (A2), not against size. On this run: 275 fill parts, 3.6 % under
20 mm2 (target met); 717 motif / detail parts.

## Floret count (A2 / A14): generated, 64 % of the reference
Splitter: 299 centres (lightness peaks >= 1.5 mm apart in the blossom silhouette, 4 ppm evidence) -> 216 petalled florets
+ 83 bead-only. Independent recall check on the 12 ppm reference (Laplacian-of-Gaussian blobs, radius 1.5-3.5 mm, inside
the same silhouette; scratchpad m3b/count.py): **339 blobs** (344 / 332 at LoG threshold 0.03 / 0.05). 216 petalled
florets = 64 % of the count; 163 blobs (48 %) have a floret centred within 2 mm, 216 (64 %) a bead. Weaknesses (review):
same luminance channel, and the silhouette is the splitter's own; a recall check, not a per-motif trace. The undercount
makes the deep canopy show more than in the reference. **M3c gate:** petalled florets >= 80 % of the reference count.

## Blossom density on the written file (PR #10 review item 3)
`scratchpad m3b/bdens.py`: qa.density_map on all DST stitches, split by the traced blossom parts (parts.json).

| area (cm2) | M3b first PR (1 mm underlap, florets 0.36) | after fix, M1 sequencer (0.3 mm seam, florets 0.45) | after fix, merged with M4g | final (M4g + M3a) |
|---|---|---|---|---|
| florets + beads (43.9): mean / share > 7 | 9.31 / 90 % | 7.25 / 45 % | 6.92 / 35 % | 7.01 / 37 % |
| canopy between florets (28.6) | 7.00 / 45 % | 5.92 / 22 % | 5.74 / 16 % | 5.86 / 20 % |
| blossom silhouette (72.5) | **8.40 / 73 %** | 6.72 / 36 % | 6.46 / 28 % | **6.55 / 30 %** |
| rest of crop | 4.88 / 11 % | 4.87 / 11 % | 4.64 / 7 % | 5.10 / 14 % |

Cause: knocked-out florets still grew the 1 mm underlap into the canopy that already had a hole for them (a second-layer
ring), plus radial convergence at the Konpeito patch spacing 0.36. Fix: a knocked-out floret overlaps its canopy by a
**0.3 mm seam** (`sequence.SEAM_MM`), and jacket florets sew at 0.45 (`run_bk_crop.yaml` rule_overrides; M5 untouched).
Seams checked (`scratchpad m3b/seam.py`, stitches drawn at 0.42 mm on a 20 ppm raster, bare clusters >= 0.1 mm2 inside the
blossom silhouette eroded 0.3 mm): **no underlap at all** left 9 gaps at floret edges; the **0.3 mm seam** 1-2 (5 on the
final merged run, largest 0.73 mm2); the 1 mm underlap 0. Live-view zoom (scratchpad m3b/seam_live_*.png): no visible
ring of fabric at the floret edges. Florets still average 7.0: radial rows converge to the bead hole. A further cut is a
sequencing / density question for M4.

## Direction evidence: what is independent (A24), one basis for M3a and M3b
Since this PR, `extract/splitters/construct.py` is the ONE place a constructed angle is rebuilt (M3b `meta.construct`
rules AND M3a's `course` / `down_slope` / `across` via building_fit.rule_basis) and bucketed (`bucket_of`):
| constructed angle | bucket | why |
|---|---|---|
| trunk strip axis, branch column, floret centre, bead | independent | positions of traced strokes / centres, not the grain (caveat: a thin trunk's edges run along its axis too) |
| crown clump fan (long axis from the attachment end) | outline | picked over "base -> centre" after comparing both with the reference grain (61 % vs 38 %) |
| M3a near roof tiers, members, walls under near roofs | independent | playbook rule on fitted geometry |
| M3a FAR tiers and walls under them (depth rule, near_tier_rel) | **outline** | the far / near choice moved the gate 43 -> 63 % on this render (BENCH_m3a.md "partly grain-informed") |
| canopy | self-derived (field mean) | a rule 45 deg matched 0 % of the canopy area |

## Trims
Details first and knocked out of their fill (florets / beads before the canopy, lit before dark): 196 -> 118 on the M1
sequencer. Visible beads (not the floret's own thread) +18. Merged with M4g and M3a: 147 (36.8 / 100 cm2).

## Satin-shape gate and the part map
qa.satin_shape cannot tell a floret from a fan in a window; `run.florets_by_part_map` re-files flagged runs mostly
labelled with a RADIAL part (and < 1.5 mm runs inside a bead: the dot plugin's cross underlay); counts in gates.json.

## Chaos gate and radial florets (open, separate PR)
Florets are radial by the playbook; an 8 mm tile over two of them holds rays in every direction. The gate is NOT changed
here. Agreed follow-up (review): exempt a tile only when >= 70 % of its visible stitch length is radial-mode floret-size
parts AND those stitches' radial adherence in that tile is >= 85 %; report raw and exempted chaos; red tests.

## What's left
- **Stitch budget:** the crop is 125,086 stitches / 399.9 cm2 = 313 st/cm2. The full back (2,857 cm2) at that density is
  ~890k, at half of it ~450k: over the 250-350k house budget (rule 6). The crop is the richest part of the back, so this
  is an upper bound, but nothing yet shows the budget is reachable: M4 budget step before M3 is done.
- Florets: 64 % of the reference count, smaller than the reference domes; overlapping florets back-to-front (M3c, gate
  >= 80 %).
- Chaos: canopy and crown clumps (47 chaos tiles) + the radial exemption PR.
- Coherence: 27 lit clump pieces show < 12 visible stitches (flagged, A22) and 30 dark clumps spread.
- Pale blossom thread merged into pink by the 12-thread plan (beads therefore deep inside florets).
- Pines show no trunk: 75 of 84 clumps attach to dark "bark" pixels (often shadow), 9 to the crown base.
- Branch columns are one width; the traced branches taper.
