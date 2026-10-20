# Koi Blossom: engine trial vs the delivered Rev B file (re-run 2026-10-20, tag koi)

**The founder's question:** is the engine's embroidery better than what we delivered?

**Founder ruling for this re-run (2026-10-20):** the GARMENT MOCKUP governs; the AI close-up only informs. Every fish, lily,
leaf, petal and the vine is placed, posed, sized, counted, outlined and coloured from `inputs/front.png`. The close-up may
only add interior detail (petal structure, shading) inside a motif the mockup already has, and only where the mockup has
it. Every gate is graded against MOCKUP pixels.

## Short answer
On the mockup's own terms, **the engine's file now matches the design better than Rev B**:
- It follows the mockup's layout. The flora matches on 23 of 34 motifs against Rev B's 12; the bare area the mockup
  shows as embroidered is 239 mm² against 741 mm².
- It has far fewer satin blobs (3 against 90).
- It puts far less stitching where the mockup shows bare duck: 109 mm² against 1,934 mm².

**The fish are now close.** Both files place 4 of the 5 mockup fish within tolerance. The engine's fish have a crisp white
tail, a visible eye, a red band and a neon line. Rev B's tetras are still a little cleaner: whiter body, longer fin rays.

**The vine is still the engine's weak spot.** Neither file passes the house gates: Rev B passes 1 of 8, the engine 1 of 8.
Do not ship the engine's file yet (see "What still blocks").

## Pictures
They are in this folder and copied to `C:\Users\devin\Desktop\koi-trial\`.

| file | what it shows |
|---|---|
| `trial_side_by_side.png` | the whole crop at the same scale (4 px/mm): MOCKUP, then Rev B, then the engine |
| `trial_zoom_lily.png`, `trial_zoom_fish.png`, `trial_zoom_leaves.png` | 10 px/mm, four columns: mockup, Rev B, engine, and the detail source (the close-up inside the mockup's motif, colour-matched to the mockup) |
| `engine_panel.png` (desktop copy of the git-ignored engine panel) | mockup, part map, live view, direction heat-map, density |

**Note:** the mockup column is the mockup upscaled. It holds only about 0.9 px/mm of real detail, so it looks soft.

## How the close-up informs, motif by motif
This is `engine/digitize/extract/inform.py` together with `bench/inform_fit.py`.

**The fit.** Each close-up motif is fitted to its mockup motif on its own (a rotation, scale and shift per motif; no
global warp). A motif is informed only when its fitted silhouette overlaps the mockup's silhouette with IoU of at least
0.5.

**Inside a fitted motif:**
- Only pixels inside the mockup's own silhouette (the largest one in the window) take close-up detail.
- A pixel takes detail only where the close-up shows embroidery.
- Colours are shifted to the mockup motif's mean colour.
- The close-up adds light and dark pattern only, never shape, position or hue.

| motif | fit IoU | informed? |
|---|---|---|
| upper pale lily | 0.66 | **yes**: petal structure and shading inside the mockup's lily, mockup colours |
| lower dark flower | 0.41 | **no**: the close-up's lower lily (mid-blue, a different shape) is not this mockup flower, so the mockup wins |
| lower leaves | 0.40 | **no**: the close-up's leaves do not line up with the mockup's |
| fish (all) | n/a | **no**: the close-up shows koi; the founder's fish are tetras (`inputs/reference_fish.png`), placed at the MOCKUP poses × 0.82 |
| floating petals | n/a | **no**: a few mockup pixels each, and their close-up counterparts sit elsewhere |

**Where the close-up disagrees with the mockup (the mockup won every time):**
1. It shows 4 koi; the mockup shows 5 fish in this crop, the fifth at the right edge, and every fish sits about 13 mm
   (up to 30 mm) away from its mockup position.
2. Its lower lily is mid-blue with cream stamens. The mockup's lower flower is a dark navy flower of a different shape.
3. Its floating petals and lower leaves sit in different places.
4. It shows koi markings, not the founder's tetras.

## Same gates on both written files

**Crop:** FR, size M, x -220 to -50, y 30 to 300 mm.

**Gate reference: mockup pixels only** (`bench.json` uses `registration_mockup.json`, with no close-up).
- **Fish reference:** `refmask.fish_ref`, the founder's tetra at the MOCKUP poses × 0.82. It is the Rev C code, and it
  runs with the art modules blocked.
- **Flora reference:** a colour test on the mockup crop, with the mockup's fish removed.
- **Source of every number:** `trial_gates.json`.

| gate | Rev B delivered | Engine | better |
|---|---|---|---|
| stitches in the crop | 21,937 | 24,812 | reported, not a target |
| thread colours (red present) | 11 (yes) | 11 (yes) | = |
| **fish motif_match vs the mockup poses (ok of 5, mean IoU)** | 4 (0.71) | 4 (0.73) | = |
| **flora motif_match vs the mockup (ok of 34, mean IoU)** | 12 (0.59) | **23 (0.66)** | engine |
| **uncovered: mockup embroidery left bare (gaps ≥ 25 mm²)** | 9 / 741 mm² | **4 / 239 mm²** | engine |
| stitched where the mockup shows bare duck | 1,934 mm² | **109 mm²** | engine |
| direction OK vs MOCKUP pixels (all visible tiles) | 21.8 % of 275 | 61.8 % of 249 | engine* |
| direction OK vs informed reference (info only) | 22.2 % | 64.3 % | engine* |
| independent-angle tiles (engine only, needs part ids) | n/a | 68.9 % of 45 tiles (coverage 18 %, FAIL) | |
| chaos | 20.4 % | 14.9 % | engine (target ≤ 5 %: both fail) |
| satin blobs / fans / too narrow | 90 / 10 / 19 | 3 / 1 / 0 | engine |
| density mean / p95 / flags > 7 | 3.56 / 7.43 / 19 | 4.08 / 8.15 / 29 | Rev B |
| max stack (cm² > 2 layers) | 3 (0.57) | 3 (0.84) | about = |
| trims per 100 cm² covered | 107.8 (148) | 98.1 (111) | engine (both far over 25) |
| exposed stitches (DST-only proxy) | 263 (447 mm) | 97 (140 mm) | engine |
| bench gates passed | 1 / 8 (colours) | 1 / 8 (colours) | = |

\* The mockup holds about 0.9 px/mm of real detail, so its "grain" is mostly the AI render's shading. Read these two rows
as "the engine's stitch directions are smoother and consistent", not as proof of a correct grain.

**From the engine's plan:**
- 196 parts, 0 % zone stubs.
- 2 unexplained angles: crown clumps whose fan no longer rebuilds after the cut-under.
- Angle coherence fails: 30 parts with no visible stitches, 31 with angle spread.
- Rule-3 separation: 1 close pair.

## What changed since the first trial
| what changed | before → after |
|---|---|
| positions and silhouettes | close-up (TPS) → **mockup**; the close-up informs the upper lily's interior only |
| fish body | cornflower (nearest-thread blues of an anti-aliased image) → **silver / lavender bands** (the reference tetra read against silver white, lavender grey, ice blue only) |
| tail | sewn as body along the axis → cut at the peduncle and sewn as **satin along the rays** (radial from the root; fins too) |
| eye | lost (merged as a speck) → **bead in eye black** (protected thread) |
| red stripe | 6 mm satin column (a slab) → a **band of the body**, tatami along the axis; the cyan line (< 2 mm) is a light satin column at 0.55 mm |
| tone seams | 1 mm underlap between abutting tone pieces → **0.3 mm seam** within one motif (`meta tone_group`, `sequence.TONE_SEAM_MM`); density flags 31 → 29, max stack 4 → 3 |
| vine | 1 branch (8 of 9 components rejected) → 21 branch columns + 3 strips, traced from the mockup; still broken up (below) |

## Verdict, in plain words
**Where the engine is better:**
- **Layout.** It follows the mockup: lily, dark flower, petals and leaves sit where the mockup has them. Rev B's lilies
  were rotated templates and its leaves were typed by hand.
- **Lily rendering.** The upper lily reads as the mockup's pale lily with a blue heart. It has long rows along each petal
  and close-up shading inside, but no radial streaks.
- **File cleanliness.** Fewer satin blobs, fewer floats, slightly fewer trims, and almost nothing stitched on bare duck.

**Where Rev B is still better:**
- **Fish finish.** Rev B's tetras read whiter, with longer and cleaner fin rays. The engine's body reads lavender-grey
  and its dorsal and pelvic fins are small.
- **Stems.** Rev B has long continuous satin stems (hand-typed, not traced). The engine's vine is traced but broken into
  short pieces, because the mockup draws the stems faintly at about 1 px/mm.
- **Density.** 29 flags against 19.

**Weak in both:** the lower dark flower. The engine finds only 2 petals and renders the rest as dark leaf clumps. Rev B
drew a template lily there.

## What still blocks a full Koi rebuild
1. **Vine continuity.** The engine needs a stem tracer that follows a faint 2 mm stroke across leaves (a centreline
   through gaps), or a founder vector stem.
2. **Fish finish.** The body needs a brighter silver base, and the dorsal and pelvic fins need to be enlarged to the
   reference's ray length.
3. **Lower dark flower.** The petal fan fails on a dark flower against dark leaves (2 petals found). It needs either a
   better close-up of that flower or tone separation.
4. **Gates.**
   - There is no independent rule for organic motifs (independent coverage 18 %).
   - Coherence fails on buried tone pieces.
   - Chaos is 15 %.
   - Density is still over target.
   - The trims target of 25 per 100 cm² does not fit a design of separate motifs on bare duck; the founder needs to set
     a Koi value.
5. **Only one close-up**, and only one of its three motifs informs. FL, the hem flowers and the sleeves would be
   mockup-only.
6. **Pack path (M7).** Per-size placement, splits and pages for an engine-built design.

## Re-run
```bash
PYTHONPATH=engine python3 projects/koi-blossom-hoodie/bench/inform_fit.py       # per-motif close-up fits -> registration.json
PYTHONPATH=engine python3 -m digitize.run projects/koi-blossom-hoodie/bench/run_fr_crop.yaml --stages extract,plan,review,compile,gates,panel --no-api
PYTHONPATH=engine python3 projects/koi-blossom-hoodie/bench/trial_compare.py
```
- **Rev B file:** a git-ignored copy of the delivered `HAKI_KOIB_01_front-fish_FR_M.dst`. Its origin is (-146.775, 247.30),
  aligned on the Rev C build's recorded origin; the delivered files were not touched.
- **Bench stage:** not run, so there is no SCOREBOARD row.
