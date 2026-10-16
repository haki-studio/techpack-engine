# Lessons — every problem we hit, the fix, and the check that keeps it fixed

Read this before starting any tech pack. Each entry is a rule. Where a check exists in code, it is named; a rule
without a check is a review item for the person/agent running the pipeline. Add to this file whenever a new
problem is found and solved — the point is that no mistake happens twice.

Numbers in brackets are from the first garment (Drum Island jacket, plum + pine, Oct 2026) so the size of each
effect is on record.

## A. Artwork (recreating the mockup as stitchable regions)

| # | Problem | Rule / fix | Check |
|---|---|---|---|
| A1 | Leaves faced the wrong way; leaf clusters and bamboo floated in empty fabric. | Every motif is attached to its support: leaves grow from bark on a petiole, fans point away from the limb; bamboo culms rise from ground / a snow drift. | Review the render zoomed per cluster. TODO: automate "every motif touches its parent". |
| A2 | First pass was far less dense than the mockup; client asked twice for "closer to the mockup". | Count motifs per area in the mockup (blossoms, buds, twigs) and match it; put shading tones in from the first pass. | Side-by-side mockup vs stitch render on the spec page. |
| A3 | Art drawn over seams, rib and collar. | Keep-outs (mm from the sew line): side seams 15, CF/zip 15, front armhole + shoulder 15, hem-rib seam 10, welt box 6, collar lying flat 6. Rib knit is never embroidered. | `emb_place.clearances()` per size, MIN table. |
| A4 | Branches wrap from the back onto the sleeve. | Split into back piece + sleeve piece, 3 mm short of the seam on each side, limb crossings exported as match marks (notches on the cap). | `spec2.match_marks()`; per-size: `back_size.py` marks. |
| A5 | Wrap art on graded sizes: scaling the art doesn't scale the armhole; only 0–2 of 7 limbs met the seam on non-M sizes. | One 01 back + sleeve file **per size**: grade the unclipped scene, anchor it on that size's armhole, re-clip to that size's keep-outs; the overflow becomes that size's sleeve file. | `emb_place` wrap check (aligned / total marks): 6/7 on S–XXL, 4/4 XS, 6/6 3XL. Art anchored on the right armhole (`back_size.py`). |
| A6 | Thin knockout slivers between regions — unstitchable and they create trims. | `back2.absorb_slivers()` at build time; `dst2.clean_vis()` before stitching (close 0.3 mm, drop fills < 1.5 mm² or < 0.7 mm wide, lines < 0.8 mm²). [9,099 → 4,179 fragments, 0.7 % area] | fragment count printed by the build. |
| A7 | Copyrighted characters in AI mockups (e.g. soot sprites). | Decline that element, offer an original; never draw a lookalike. | Inventory step. |
| A8 | Keep-out clipping orphaned leaf sprays (their twig was clipped away) and they floated on bare fabric (Forestball, Oct 2026). | After every clip, cluster the tree parts and drop clusters with no limb bark under them; give each motif family its own support codes (rock moss ≠ limb moss, or rocks lose their caps). | `projects/forestball/fmotifs.drop_floating()` prints the dropped count. TODO: move to `qa.py` with a `support_codes` argument + test. |
| A9 | Licensed elements (a character on a pole, an orb in a stream) must not be drawn by us. | Reserve the area as a marked placeholder box: knocked out of our art, a removable basting outline as its own stop, the box on the pattern (DXF layer 8); each hoop section bastes its own part of the outline. | Moon + Forestball builds: 0 stitches inside the box (DST read-back), basting stitches on the outline. TODO: engine `placeholder=` support. |
| A10 | No originals: mockups are AI renders ~1–1.5k px for the whole garment, so art was redrawn, not traced; moss/leaf density came out lighter than the mockup (Forestball, Grand Line, Oct 2026). | A bigger frame doesn't help (it changes hoopings, not detail). Ask for per-panel close-ups from the same image tool (prompt in `techpack-pipeline` §0b), match motif counts (A2), upscale only to read shapes; say on the spec page which reference the art came from. | `inputs/closeup_request.md` written at intake; reviewer compares motif counts vs mockup. |

## B. Stitch engine (`engine/dst2.py`)

| # | Problem | Rule / fix | Check |
|---|---|---|---|
| B1 | Thousands of trims [v1 back: 4,462]. | Travel runs hidden under fill that sews later, under same-colour fill already sewn, or under the object about to sew (underpath). Order objects inside one hidden connected area before jumping. One object per connected piece. Forgive 0.8 mm at pull-comp endpoints; allow ≤ 0.6 mm exposed at abutting edges. [→ 1,411 v2, 1,338 v3] | trims read back from the DST (`verify`, DST reader). |
| B2 | Small detail colours sewn last can't hide their travel. | Sew detail colours that are knocked out of a later fill *before* that fill (bud highlights before bud bodies). [BD-hl trims −60 %] | `by` trim histogram per code. |
| B3 | Stitch count inflated by dense outline vertices (every polygon vertex became a 0.3 mm stitch). | Simplify paths (0.2 mm) before resampling runs, edge runs and travel. [−22 %] | stitches per mm² by code (`bycode` script). |
| B4 | Too dense for 12 oz duck [back 437k stitches, ~10 h/head]. | Production density: tatami 0.45, satin 0.42, radial 0.40 mm; padding 1 layer and only under snow > 3 mm wide; 90° lattice underlay only under fills > 60 mm²; hidden travel 7 mm; blend rows 1.0 mm. [→ 293k] | stitch count + run time on G4/G5. |
| B5 | 16 threads > a 15-needle head. | ≤ 15 threads per file: merge the closest ΔE2000 pair (`COL_MERGE`, vermilion → plum red, ΔE 8.5). | thread count per file in the build log. |
| B6 | Same colour came up many times (snow cream ×7). | `merge_stops()`: move a region to the earliest same-colour stop if nothing sewn in between is within 1 mm. [42 → 37 stops] | stops before/after merge in results json. |
| B7 | Stitch > 7 mm (DST limit 12.1, machines prefer ≤ 7). | Split satin/fill stitches > 7 mm; travel ≤ 7 mm; never a sewn stitch > 7.5 mm. | `verify()` max_stitch. |
| B8 | Trim counts disagreed (PES read triples them). | Always count trims by reading the **DST** back. | `postdst.py` / `verify`. |
| B9 | Estimated stitch counts (area × density) were 2.5× off the real file [175k vs 437k]. | Every number in a document comes from the generated file, never from estimates. | spec pages read `dst*_results*.json`. |
| B10 | Hoop splits cut blossoms in half (motif clusters chained through snow into one huge cluster). | Split lines placed where they cut the least art; objects < 70 mm go whole to one section; blossoms/buds cluster only with themselves; fills overlap 1.2 mm across the split; basting crosses on bare fabric on the split lines; each section ≤ frame − 16 mm. | `split_clip` fits, preview of every section. |
| B11 | `TopologyException` after scaling/clipping. | `buffer(0)` after every affine transform; fall back to `make_valid`. | — |
| B12 | XXL/3XL bottom split sections came out 359–363 mm tall: the frame check ignored the registration crosses placed 12 mm beyond the art. | Split candidates must fit the frame *including* the outer crosses (`split_clip(ext=18.5)`: crosses 12 mm out + 6 mm arms), then a frame pass moves overhanging whole motifs to the neighbour that can hold them (or cuts them at the frame limit with overlap). | `fits` per section in each size's result.json. |
| B13 | Back builds took 9–13 min per size; 74 % was polygon unions, not routing: `unary_union` of all earlier fills re-done at every colour stop (265 s of 454 s on XS) and a whole-design union only to read its bounds (58 s, also in every split search). | Never union the whole design: `bounds_of()` for extents, `Tones` (STRtree, local clip) for blend zones, `cut_length()` (1-D interval merge) for split search. Profile with cProfile before optimising — the suspected hot spot (routing, 44 s) was not the real one. [XS back 454 s → 100 s; split choice identical on XS/M/XXL; stitches −0.04 %, trims −7] | `test_fast_geometry_matches_union`; build time per file in the log. |
| B14 | 625 trims on one front piece of a patchwork design (sea dashes, cloud lobes split by fabric gaps, dashed rays) (Grand Line, Oct 2026). | Design the colour order for hidden travel: details first, the darkest connected tone last; lines over fills are overlays that don't knock the fill into islands; no fabric gaps between same-tone neighbours; dashed lines → continuous bean lines. Count islands per colour before stitching: every unhidden island is a trim. [625 → ~240] | trims from the DST read-back per piece. |
| B15 | Leaf halves sewn after their twigs could not hide their travel. | Small detail motifs that touch a later fill (leaves on twigs) sew before it (B2 applied to sprays). [front trims 249 → 166, 257 → 123] | trims from the DST read-back before/after. |
| B16 | `split_clip` said a section fits, but the written file was 348 mm wide (> 344): the cross arm ON the split line (6 mm) was not counted (Forestball, Oct 2026). | Section fit = art + outer crosses + the cross arm on each split line, measured the same way the file is. | `test_split_fit_counts_cross_arm_on_split_line`; `fits` per section. |
| B17 | A 7.52 mm stitch read back from XXL/3XL files: stitches were split at > 7.5 mm before rounding to the 0.1 mm grid. | Split sewn stitches at > 7.4 mm in `make_pattern`. | `verify()` max_stitch ≤ 7.5 on every file (could not reproduce on a synthetic design, so no unit test yet). |
| B18 | `tech.stops()` silently dropped every region whose colour was not in `COLOUR_ORDER` (a new palette lost art without an error). | `tech.stops()` raises on an unknown colour; `dst2.pull_for()` reads pull comp from `tech.RULES` at call time, so project rules count. | `test_stops_raises_on_unknown_colour`, `test_pull_reads_rules_added_after_import`. |
| B19 | Sliver cleanup gave a wire's end sliver to the neighbouring crossarm fill, which then sat 12 mm from the side seam (keep-out 15) on XL (Moon, Oct 2026). | Line regions (bean/run) keep their own slivers; only fills absorb fill slivers. | `emb_place.clearances()` side ≥ 15 on every size. TODO: move `absorb_slivers` into the engine with that rule. |

## C. Pattern (`engine/pattern.py`)

| # | Problem | Rule / fix | Check |
|---|---|---|---|
| C1 | Front neck drawn convex (bulging out) instead of scooped. | Neck curves must lie *below* their chord (into the body). | `pattern_out.shape_checks()` (neck chord midpoint must lie outside the piece). |
| C2 | Shell sleeve opening came out half size — POM charts give **half** measurements (1/2 chest, 1/2 opening). | Always convert half-measures explicitly; pattern half-width ≠ half-circumference. | seam walk: cuff rib / sleeve opening ratio 0.75–0.85. |
| C3 | Seam-allowance offset picked the inside of rectangles (endpoint test tied). | Pick the offset side by testing points along the middle of the offset line. | `pattern_out.shape_checks()`: cut line encloses sew line on every piece. |
| C4 | Welt pocket spec (1.6 × 14) clashed with embroidery 03/04. | Garment details and embroidery are checked together on every size; welt 1.4 × 13. | `emb_place.clearances()` welt ≥ 6. |
| C5 | 108 % art outgrew the XL shoulder; 04 boxed in by welt + hem on XXL/3XL. | Grade per element with overrides; XL uses B (100 %); 04 stays 100 % on XXL/3XL; per-size nudge solver (smallest move that restores every keep-out). | T13 table "all pass". |
| C6 | Values not on the fit chart (shoulder slope, rib heights, cap ease, facing widths). | Mark as PROPOSED everywhere they appear; list on the open-questions page. | `pattern.PROPOSED`. |
| C7 | Pattern is drafted, not fitted. | Say so on the pattern pages; first sample in M before cutting the size set. | T11 footer. |
| C8 | Front art clipped against the block's shoulder line sat ~5 mm from the real seam: the pattern moves the front shoulder 10 mm forward (Forestball, Oct 2026). | Take keep-out lines (shoulder, armhole, side) from the drafted pattern piece, never from the block. | `emb_place.clearances()` measures on the pattern pieces; shoulder ≥ 15 on every size. |

## D. Documents

| # | Problem | Rule / fix | Check |
|---|---|---|---|
| D1 | `&` in SVG text broke rendering; overlapping labels. | Escape `&`; render every page to PNG and look at it before merging. | preview PNGs (`prev_*.png`). |
| D2 | 85 MB PDF. | Recompress embedded images (`shrink.py`, max 3000 px, q82) → ~12 MB. | file size before delivery. |
| D3 | Pages referenced stale numbers after a rebuild. | Rebuild order: stitch files → results json → specs → embroidery pack → garment pack → merge. Never hand-type a count. | `build_all.py`. |

## E. Process

| # | Problem | Rule / fix |
|---|---|---|
| E1 | Long jobs (10–25 min each on 2 cores). | Run in the background, two at a time on the cloud box, all cores locally; queue with `xargs -P`. |
| E2 | `pkill -f <pattern>` killed the calling shell (its own command line matched). | Kill by PID from `ps -eo pid,args` with an exact argv match. |
| E3 | Fixing one thing at a time cost four rounds. | Run every check in this file before the first delivery; deliver with the check table. |
| E4 | Embroidery placement solid-filled on 1:1 plots (8-digit hex alpha unsupported by cairosvg). | Use `fill-opacity`; outlines only on plot PDFs. |
| E5 | Builders found no Python with the engine deps (the system python has no shapely) and each made a private venv. | `scripts/env.sh` activates `.venv` or `~/.venvs/techpack` and warns if the deps are missing; one shared venv per machine. |
| E6 | E2 hit again in a parallel build (Moon). | Never `pkill -f`; kill by PID with an exact argv match. |
| E7 | First batch packs were checked only by the agent that built them; nothing had been sewn; frame size, thread match and factory pricing were assumptions. | Every pack: independent reviewer before it is `reviewed`; F1 Factory requests page (strike-off size M, frames, thread card, quote basis) from `engine/factory.py` + `factory.json`; strike-off results fed back as LESSONS rows with measured numbers. | `tests/test_factory.py`; status stages `review` → `reviewed`. |
