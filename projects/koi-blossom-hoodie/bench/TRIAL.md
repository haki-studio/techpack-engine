# Koi Blossom: engine trial vs the delivered Rev B file (2026-10-20, tag koi)

**The question:** is the parts-based engine's embroidery better than what we delivered?

**Short answer:** it is better on the **flowers and leaves**. It is worse on the **fish**. Neither file passes the house
gates (Rev B passes 1 of 8, the engine 2 of 8, plus separation). The engine is **not ready for a full Koi rebuild**.
The reasons are listed under "What blocks a full Koi rebuild".

## Pictures (look at these first)
| file | what it shows |
|---|---|
| `trial_side_by_side.png` | the whole crop at the same scale (4 px/mm): reference, then Rev B, then the engine |
| `trial_zoom_lily.png` | the big upper lily at 10 px/mm |
| `trial_zoom_fish.png` | one fish at 10 px/mm |
| `trial_zoom_leaves.png` | leaves and the vine at 10 px/mm |
| `../out/digitize/KOI_FR_M_crop/panel.png` (git-ignored) | the engine's own panel: reference, part map, live view, direction heat-map, density |

"Live view" means the engine's thread-sheen render (dstlive) of each WRITTEN DST. Neither image is the art.

## The crop
- **Piece and size:** FR (the wearer's right front), size M.
- **Box:** x -220 to -50 mm, y 30 to 300 mm. That is 170 × 270 mm, in garment mm with x measured from CF and y from the
  CF neck seam.
- **Why this box:** it is the largest box inside the close-up's registered area (close-up feather weight at least 0.797).
  A 200 × 200 square does not fit, because the close-up's frame is rotated relative to the garment.
- **What it holds:** both close-up lilies, their leaves, the floating petals, and the four close-up fish. The fish at the
  bottom right has its snout on the crop edge.
- **Registration:** `registration.json`. The flat image is `inputs/front.png`, mapped with the mockmap constants. The
  close-up is bent onto the mockup by a thin-plate spline through the 10 tie points in `trace/closeup_reg.json`.
- **Rev B file:** `out/revB/` holds a copy of the delivered `HAKI_KOIB_01_front-fish_FR_M.dst`. The delivered files were
  not touched. Its origin is (-146.775, 247.30). I got this by aligning it on the Rev C build's recorded origin; the
  residual is 0 mm at 5 px/mm. Both DSTs are centred on their art box.

## Same gates on both written files

**Sources.** `trial_gates.json` holds every number; `trial_compare.py` re-makes them. Every number is read from the DST,
and the thread colours from its PES.

**The two motif references.** Both are built from input pixels only:
- **(a) `refmask.py`:** the Rev C module. It cannot import any art. It uses the mockup positions plus the close-up lilies
  pasted in their discs, and it builds fish from the founder's tetra at the mockup poses × 0.82.
- **(b) the close-up as registered here:** a plain colour test on the same reference the engine traced from. It shows
  the flora only.

| gate (crop) | Rev B delivered | Engine | better |
|---|---|---|---|
| stitches in the crop (whole file) | 21,937 (40,325) | 30,257 (33,369; the file is the crop only) | reported, not a target |
| thread colours (red present) | 11 (yes) | 11 (yes) | = |
| direction OK, all visible tiles vs the reference grain | 34.2 % of 275 | 66.7 % of 258 | engine |
| direction from **independent** angles | n/a (a DST has no part ids) | 34.3 % of 35 tiles (coverage 14 %, FAIL) | neither passes |
| direction from **self-derived / outline** angles | n/a | outline bucket 73.4 % of 124 (lily rays, leaf fans: not independent, A24) | (not a pass) |
| chaos (tiles with no single grain) | 20.4 % | 15.1 % | engine (target ≤ 5 %: both fail) |
| satin blobs / fans / too narrow | 90 / 10 / 19 | 0 / 0 / 0 | engine |
| density mean / p95 mm/mm² / flags > 7 | 3.56 / 7.43 / 19 | 4.48 / 9.08 / 31 | Rev B |
| max stacked layers (cm² > 2) | 3 (0.57) | 4 (2.86) | Rev B |
| trims per 100 cm² covered (trims) | 107.8 (148) | 100.0 (121) | engine (both far over 25: sparse motifs on bare duck) |
| exposed stitches (DST-only proxy: > 1 mm over bare cells) | 263 (447 mm) | 94 (127 mm) | engine |
| angle coherence per part | cannot be judged (no part ids) | fails: 46 parts with no visible stitches, 42 angle-spread | neither |
| rule-3 separation (same thread, < 15°) | n/a | 0 close pairs | engine |
| random / unexplained angles | not knowable from a DST | 2 (crown clumps whose fan no longer rebuilds after the cut-under) | |
| **(a) fish** motif_match, ok of 5 (mean IoU) | **4 (0.71)** | 2 (0.54) | **Rev B** |
| **(a) flora** motif_match, ok of 28 (mean IoU) | **9 (0.54)** | 0 (0.13) | **Rev B** |
| **(a)** uncovered gaps ≥ 25 mm² | 18 / 2,193 mm² | 39 / 5,234 mm² | Rev B |
| **(b) flora** motif_match, ok of 32 (mean IoU) | 0 (0.28) | **16 (0.63)** | **engine** |
| **(b)** uncovered gaps ≥ 25 mm² | 37 / 3,480 mm² | 15 / 903 mm² | engine |
| bench gates passed | 1 / 8 (colours) | 2 / 8 (colours, satin shape) + separation | |
| zone-stub area | n/a | 0 % (every part came from a real splitter) | |

**References (a) and (b) disagree because the two INPUT images disagree about where things are.** The close-up drifts
13 mm on average (up to 30 mm) from the mockup (`trace/closeup_reg.json`). Rev B took its positions from the mockup.
The engine took them from the registered close-up. Each file therefore wins on the reference that matches its own
choice. This is a registration decision for the founder, not a digitizing result: should petal and leaf positions come
from the mockup or from the close-up?

## Verdict, in plain words
**Where the engine is better:**
- **Lilies.** The petals are mid-blue with pale highlights, as in the close-up. Each petal is sewn as long rows along
  that petal (one angle per petal, from the flower's heart to the petal tip). Rev B is pale ice/white radial streak fans,
  which is REVIEW_OPEN item 3. The engine also matches the close-up's petal layout: it traced each lily's own petals
  (7 petals on the upper lily, 6 on the lower), with no template copies.
- **Clean satin.** There are no satin blobs or fans: 0 against Rev B's 90 blobs and 10 fans.
- **Fewer floats and trims.** There are fewer exposed stitches and slightly fewer trims for the area.
- **Leaves.** They are traced leaf by leaf from the close-up and read as solid blue (REVIEW_OPEN items 3 and 4). Rev B's
  leaves are white-streaked and their positions were hand-typed.

**Where the engine is worse:**
- **Fish.** Rev B's tetras are crisp: silver body, clear fins and tail, red and cyan stripes and the eye. The engine's
  fish read muddy blue. The body takes the reference tetra's flank blue (cornflower). The fins and tail are small,
  blobby pieces that barely show. The stripes are heavy satin columns. The eye is a bead that is hard to see. The
  engine places the fish at the close-up poses, which are not the mockup poses, so on reference (a) it scores 2 of 5
  against Rev B's 4.
- **Edges and density.** The lily tone pieces have jagged, pixel-traced edges. The abutting tone pieces with 1 mm
  underlaps push density up (31 flags against 19) and stack to 4 layers.
- **The vine.** The deep-navy stem along the bottom is mostly lost: the trunk splitter kept 2 short branches, 38 mm².
  Rev B has clean satin stems, but they were typed by hand.

**Overall:** I would not send the engine file instead of Rev B today. The fish alone rule it out. For the flowers, the
engine's output is the better starting point, and it fixes the review's main flora findings.

## What blocks a full Koi rebuild
1. **Fish quality.** The new `fish.py` places the founder's tetra correctly (head, dorsal side up the garment, 0.82 ×
   length). It still needs:
   - (a) a body tone plan: silver / lavender bands, not nearest-colour pieces of an anti-aliased image;
   - (b) fins and tail as satin along the fin rays, sized up to the reference;
   - (c) lighter stripes (satin at 0.42 mm on a 6 mm stripe reads as a slab);
   - (d) a decision on pose source: mockup poses (as delivered) or close-up poses (as the engine does).
2. **Registration choice.** Mockup positions or close-up positions? The founder decides (see the table). The engine can
   do either: give it the mockup positions as tie points.
3. **Close-up coverage.** Only the FR upper panel has a close-up. FL, the hem lilies and both sleeves would be traced
   from the ~1 px/mm mockup, which is the same limit Rev B had (A10 / A12).
4. **Lily splitter.** The sector cut between two petals is a straight line from the heart. Overlapping petals become one
   sector; on the upper lily, the left and bottom petals are partly merged. Tone pieces need smoothing (long-and-short
   edges, not pixel steps).
5. **Gates still red.** Angle coherence fails because 46 parts have no visible stitches (small tone pieces buried under
   later ones). Direction independence is 14 % of tiles, because organic motifs are outline-derived (A24); the gate
   cannot pass on a flowers-and-fish design without an independent rule for petals. Density and stack are over target
   (underlaps between tone pieces), and chaos is 15 % (stripe satin across a body fill in every fish tile). Trims per
   100 cm² cannot reach 25 on a design of separate motifs on bare duck: the target is calibrated for full-coverage
   scenes and needs a Koi value from the founder.
6. **Pack path (M7).** The engine writes a crop DST. Per-size placement, keep-outs, hoop splits and the pack pages for an
   engine-built design do not exist yet.

## What the trial added to the engine
| file | change |
|---|---|
| `engine/digitize/extract/splitters/lily.py` | new: petal fan from the heart, one ray angle per petal across its tones |
| `engine/digitize/extract/splitters/fish.py` | new: founder tetra template placed at each fish pose |
| `construct.py` | rule `ray`, in the outline bucket |
| `run.py` | `threads.bare`: tones that are bare shell are never threads; splitter dispatch |
| `bench.py` | `targets.accents`, because Koi has no gold |
| `splitters/__init__.py` | `Ctx.tone_thread` |
| `rules/house.yaml` | KOI kinds: `lily_petal`, `fish_body`, `fish_stripe`, `fish_fin`, `fish_eye` |

Every change is default-preserving. Tests are in `tests/test_digitize_koi.py`, each proven red by a mutation.

## Re-run
```bash
PYTHONPATH=engine python3 -m digitize.run projects/koi-blossom-hoodie/bench/run_fr_crop.yaml --stages extract,plan,review,compile,gates,panel --no-api
PYTHONPATH=engine python3 projects/koi-blossom-hoodie/bench/trial_compare.py
```
The bench stage is deliberately not run for this trial: it would add a Castle-style scoreboard row. This file is the
record.
