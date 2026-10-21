# ENGINE_NOTES — pixel-sky-fleece (proposals for the coordinator; engine/ untouched)

## 1. svgrun: `gates.exposed` override crashes
Problem: `gate_file` builds `dict(halo=0.25, min_mm=0.5, min_ex=0.3, **G.get("exposed", {}))`; any run.yaml that sets
`gates: {exposed: {halo: ...}}` raises `TypeError: dict() got multiple values for keyword argument 'halo'`.
Fix: `EX = {**dict(halo=0.25, min_mm=0.5, min_ex=0.3), **G.get("exposed", {})}`.
Check: unit test that a run with `gates.exposed.halo: 0.35` reaches the exposed-stitch gate with halo 0.35.

## 2. Exposed-stitch halo must follow the fill's pull compensation
Problem: on sherpa we sew tatami with pull comp 0.30 (pile pulls more than duck). The exposed-stitch gate's fixed halo
0.25 then flags the pull-comp overshoot at staircase (pixel-art) corners as "exposed" (E2: 3 stitches 0.35-0.44 mm,
E1B: 1 stitch 0.53 mm). Proven: the same E2 art at pull 0.20 gives 0 exposed stitches.
Fix: halo = max(0.25, part pull_comp + 0.05) per stop (read from the plan's StitchSpec), not a constant.
Check: red-then-green test — a 1 mm float between two motifs stays red at pull 0.30; a pull-comp corner at 0.30 is green.
Project workaround: `gates_fl.py` runs `qa.exposed_stitches(halo=0.35)` on every DST and reports both numbers.

## 3. New product type: engineered jacquard sherpa
Problem: no engine support for knitted / jacquard panels (cell maps per pattern piece and size); built in project code
(`jacquard.py`: trace on a fixed cell grid anchored at CF / hem, detail fill, reflection for hidden areas, indexed PNG/BMP
per panel + size). Proposal: move the grid tracer + panel rasteriser into `engine/jacquard.py` once a mill confirms the
file format (BMP indexed, 1 px = 1 cell, palette = yarn colours) — ask in F1.
Check: test that a panel map's cell count == knit area / cell² ± edge cells, and the hem row is anchored on every size.

## 4. Derived blocks by chart deltas
Problem: `fleece.py` swaps `drum.POM_CM` inside a context manager to add pile ease, because `pattern.draft` reads the
module-level chart. Proposal: `pattern.draft(size, chart=None, rib=None)` taking an explicit chart dict + rib heights.
Check: `test_fleece_inherits_jacket_shape` (same seam walks, chart deltas only).

## 5. Colour of a small motif must be read from its CORE pixels, and checked on the file (PR #28 review)
Problem: a 7 mm gold sparkle's anti-aliased rim blends in the sky; sky raises g/r, so the region's majority class read
yellow and it was sewn yellow. A14 motif_match scores shape only, so the file still passed 10/10. Against the black
bird the opposite happens: the yellow/black blend rim reads gold and inflates a reference.
Fix: colour by the core pixels (blue < 110, red > 195, g/r < 0.93 = gold); split a component whose core holds two
colours (nearest core pixel, then 1 px opening to drop rim strands). Gate: per render motif region, expected colour vs
the stop covering most of it in the DST (`gates_fl.render_motifs` + colour rows). Proposal: `qa.motif_colour(ref_regions,
stop_masks, stop_threads)` in the engine, run next to motif_match.
Check: `gates_selftest.py` — yellow<->gold swapped on the stops -> 10 colour rows red; shipped file 0.

## 6. Small pixel-art motifs on a low-res render: fit a blur model, not a hard trace (PR #28 review)
Problem: at 0.6 mm/px a 6 mm 4-arm sparkle is ~10 blurred px. A 0.5-coverage staircase fills the corners (plus ->
square); any IoU fit on blurred data rewards blobs.
Fix (project `star_fit.py`): family exemplars = the well-resolved members (>= 16 mm) made D4-symmetric; a small motif
is the exemplar resampled to N cells whose GAUSSIAN-BLURRED raster best matches the render's soft motif map (rmse).
Proposal: engine primitive `digitize.extract.pixelart.fit_family(blobs, exemplars, psf)` for any pixel-art family
(sparkles, stars, hearts), not per motif.
Check: test that a synthetic 3x3 plus, blurred sigma 0.8 px at 0.6 mm/px, comes back as the plus (not the 3x3 square).

## 7. Gates named on R1 must be run, and R1 must read their result (PR #28 BLOCKER)
Problem: R1 printed PASS for A15/A16/A17 from hard-coded True; the gates were never called.
Fix: gates_fl runs qa.uncovered, qa.angle_coherence (visible stitches per part, stitch_parts.npz) and the chaos half of
qa.direction_match on every file; R1 reads gates_fl.json; "vs reference" is printed NOT RUN when there is no close-up.
Proposal: `sheet.r1_row(name, result)` that refuses a literal bool; a lint test that greps pack builders for
`, True),` in R1 rows.
Check: gates_selftest.py (red on planted defects, green on the shipped files).

## 8. Jacquard trace grid = the knit cell, never a multiple of it on an irregular render grid
Problem: tracing in 2 x 2 cell blocks with one global phase lost the checker edges and cream cut-outs (band 91.8 %).
Fix: trace per 2.5 mm cell (band 94.4 %, sleeves 97.7 %), mirror-fill cells under garment details row by row, and force
sky under embroidered motifs (+3 px rim). J3 shows a per-pixel diff map.
Check: agreement.json band >= 94 % and a diff-map image on J3.
