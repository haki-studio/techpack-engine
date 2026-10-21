# Konpeito jeans — engine notes (for the coordinator to merge)

1. **Satin columns + "no travel over sewn satin" live in two projects now.** kjsatin.py is a verbatim copy of
   keep-clean's kcsatin.py and kjcore._patch_make_pattern copies kccore's patch (keep-clean ENGINE_NOTES 11).
   Proposed fix: move kcsatin into engine/ (column regions `ang="col"` handled in dst2.build_object) and fold the
   per-object count raster into make_pattern. Check: keep-clean + konpeito DSTs byte-identical after the move.
2. **dst2.turning_satin crashes on an empty perpendicular intersection** (`sg.coords[0]` IndexError on traced, thin,
   curved pieces). Proposed fix: skip segments with < 2 coords (kjcore.turning does this). Check: unit test with a
   C-shaped 0.8 mm stroke whose centreline overshoots the outline.
3. **qa.motif_match over-merges touching motifs.** It takes every DST component overlapping the traced motif, so
   neighbouring letters / overlapping candies merge into one DST blob and IoU drops to ~0.3 for a correct file.
   kjcompare.gate() restricts the DST mask to the stitches of the family's stop(s) within 1.5 mm of each traced motif.
   Proposed fix: `motif_match(..., near_mm=1.5, out_stops=...)` in the engine. Check: red-then-green on two touching
   squares (stitched exactly) -> IoU >= 0.9.
4. **Lesson candidate (A16): thin line art (< 1 mm) and dense small lettering cannot pass IoU >= 0.70 from a
   ~18 px/mm AI close-up**: a 0.2 mm registration error on a 0.7 mm line is ~30 % IoU. Face lines on the waistband
   patch: mean IoU 0.42; black lettering 0.66; 理砂 0.64. Proposed rule: for strokes < 1.2 mm compare centrelines
   (Chamfer distance <= 0.3 mm + length ratio >= 0.85) instead of area IoU. Check: synthetic 0.7 mm line shifted
   0.2 mm passes the centreline gate and fails area IoU.
5. **Factory F1 page says "size-M files"** — jeans use waist sizes (24–40). Proposed fix: `requests_page(..., base_size="32")`.
6. **No CJK font in fontconfig** (Noto Sans CJK JP missing on this box): sheet.FONT falls back to Zen Maru Gothic
   (copied to ~/.local/share/fonts). `≥ ≤` are missing in Zen Maru Gothic — pages use ">=" / "<=".
7. **Column satin density was half what the rule table said (fix pass, 19 Oct).** kjsatin.column_pts puts ONE needle point
   per row on alternating sides, so the same-side spacing is 2 x `sp`: Rev A's 0.30 sewed lettering at 0.60 mm same-side,
   which read as comb-like, open satin. Proposed fix: when kcsatin moves into the engine, name the parameter
   `same_side` (0.40 for 40wt, 0.28 for 60wt) and halve it internally. Check: read-back stitches per mm of a 10 mm column.
8. **Lettering and line art: digitise from centrelines, gate on centrelines.** Satin on traced AI-render outlines is ragged
   by construction. What worked: half-max masks of the mockup (edge halfway between thread and ground, so the measured
   width is the visible width); the mockup's glyph components segmented into characters (contiguous groups along the
   baseline, sized against the font's ink widths, with penalties for overlap between neighbours and gaps inside one
   character); a font glyph's skeleton fitted to ITS OWN components (chamfer distance, scale held within 20 %); loops
   kept as one closed column with the counter held >= 0.7 mm; one needle width per string = visible width - 0.15 mm.
   Gate: skeleton-to-skeleton mean distance <= 0.5 mm + width within 20 % (kjletter.cl_gate). Lesson candidate A16,
   with ENGINE_NOTES 4. Check: red-then-green with a 0.7 mm line shifted 0.6 mm (fails) vs 0.2 mm (passes).
9. **The router hides travel under narrow not-yet-sewn columns it can overshoot.** Raster hiding (kjcore "unsewn objects
   of this stop hide travel") let travel runs cross bare cream between face strokes and glyphs. Fix here:
   kjstitch.trim_exposed turns any run > 0.5 mm off its stop's art (+0.3) and later cover into TRIM + JUMP (27 runs on 03,
   9 on 01), and kjletter.exposed_stitches re-checks the DST. Proposed engine fix: check routed travel against the exact
   geometry (shapely) before accepting it. Check: exposed_stitches == [] on every file.
10. **Preview renderer exaggerated satin teeth.** A darker rim on every stitch plus flat line ends drew satin edges as
   scallops. Flat thread colour + round ends + a 1 px shade line looks like the sew-out. Proposed: the same in
   stitchrender. Check: by eye on a 2 mm column.
11. **Round dots: dst2's auto-angle satin fans on circles.** Bead dots (tiny cross underlay + dense satin at one angle,
   kjletter.knot_points) sew clean round dots and knot clusters. Proposed: `st="dot"` in the engine.
12. **Founder vector art beats any trace (founder change, 19 Oct evening).** With inputs/svg (true-size, layer per
   thread in stitch order) the lettering gates went from "pass after a lot of fitting" to mean centreline distance
   0.05-0.14 mm on every string. Proposed: `engine/svgart.py` = kjsvg's parser (M L H V Q C Z, rotate/translate,
   evenodd), layer -> thread by fill, and `layer_mask()` (cairosvg per layer) as the gate reference; techpack-pipeline
   §0: ask for the vector art first, mockups are placement/colour reference only. Check: a parse-vs-cairosvg IoU test
   per layer (>= 0.98).
13. **Bead dots: needle diameter = art diameter - 0.2 mm** (gate-calibrated on the DST read-back, 01 + 03); art dots
   under the house-minimum satin dot (Ø1.1) sew at the minimum and are reported as "house-min" rows, not hidden.
14. **qa.direction_match on small patches:** 8 mm tiles on an 80 mm patch mix the 0° field tatami, border and
   lettering, so most tiles read "chaotic" by construction (03: 11 % OK, 01: 26 % OK on the trace build). Proposed:
   evaluate per OBJECT layer (mask the tile to one family) or allow tile_mm ~3 for patches.

## Status after ENGINE_PLAN M5 (branch engine-m5-svg, 20 Oct 2026)
Engine runs: `bench/run_{wb,coin,spill,starP,starY}_svg.yaml` -> `out/engine_m5/`; parity table `bench/PARITY_M5.md`.
- 1 column satin: in the engine as `column_satin` (same_side density); the kccore/kjcore make_pattern patch is native as
  `make_pattern(exact_travel=dict(unsewn_only=True))`. The delivered Rev A build is unchanged (byte-identical DSTs).
- 2 done (dst2.turning_satin skips empty perpendiculars, LESSONS B25). 3 done (`qa.motif_match(near_mm, out_stops)`, A21).
- 4 + 8 done (`qa.centreline_match`, A19). 7 done (`same_side`, B26). 9 done (`dst2.ExactCover` + `qa.exposed_stitches`, B27).
- 11 + 13 done (`dot` technique, house-min reported, B28). 12 done (`engine/svgart.py`, `extract/svg.py`, A20).
- 14: `qa.direction_match(groups=...)` (per object layer) + the existing `tile_mm`; not wired into svgrun yet (an SVG
  source has no thread-grain reference).
- 5, 6, 10 not in M5 (pages / fonts / stitchrender).

## Rev B (20 Oct 2026)
15. **F1 chenille section on a product without chenille** (LESSONS D5 again): `factory.requests_page` prints section 5
   "Chenille machine + file format" on Konpeito; the project's own section had to move to 6 (F1_Y 158 -> 176).
   Proposed: `requests_page(..., chenille=False)` + test that a non-chenille product has no chenille section.
16. **Flat construction lines drawn by eye can misplace embroidery relative to garment features** (founder: "the top stars
   look like they sit INSIDE the front pocket"): the stars were traced correctly, but the flat's scoop line was a guessed
   bezier ~60 mm too low. Proposed rule (LESSONS D/A): every construction line that embroidery is placed against
   (pocket openings, seams) is traced from the mockup and stored as data, and a check reports each motif's distance to
   it (kjfront.py `below_opening_mm`, page C5). Check: a test that a star above a traced opening is flagged.
17. **env.sh run from the wrong directory** creates a symlink literally named `*` in the repo root (the `inputs/*` glob does
   not match). Proposed: `shopt -s nullglob` in env.sh. (One such `*` is left untracked in this worktree: not committed.)

## Rev B2 (20 Oct 2026, founder + PR #29 review)
18. **F1 sections must follow the product** (founder: "F1 keeps only what applies to Konpeito"): `factory.requests_page`
   prints chenille (section 5) and quote basis (section 4) and "size-M files" on every product. Konpeito has no chenille,
   prices are asked separately, and sizes are waist numbers (strike-off = 32). Project workaround (kjpages.F1): pass
   `prof=dict(factory.load(), chenille=False)`, cut every text at/after "4  Quote basis" and the price clause, rename
   size-M -> size-32. Proposed: `requests_page(..., techniques=set(), quote=False, strike_size="M")`; each section only
   when the product uses it. Check: a test that a non-chenille page has no "Chenille", and strike_size="32" prints "size-32".
19. **A14 per motif, not per merged blob, for overlapping candies** (PR #29 item 6, A21 again): the per-layer cairosvg mask
   merges touching candies (02: "3 motifs" for 9 candies). kjsvg.candy_masks renders each candy (body + tint + specks, in
   document order) alone; kjcompare.candy_gate scores each against its OWN stops (back row: KPB codes). Proposed:
   `qa.motif_match(refs=[...])` taking a list of per-object masks from svgart. Check: spill reports 9 rows.
20. **IoU >= 0.70 cannot tell a 5-point star from a konpeito** (red test 20 Oct: the old star scored IoU 0.85 against the
   konpeito DST and PASSED). Added an outline gate: p90 distance between the reference outline and the DST outline, both
   ways, <= 0.7 mm (konpeito 0.3-0.4 mm, star 1.3-1.5 mm). Proposed: `qa.outline_match` in motif_match for every
   shape motif. Check: the star-vs-konpeito red test fails, the konpeito passes.
21. **stitch check counts the rim of round bead dots as 'thin area'** (G3 white 4.9 % CHECK, a thread with only Ø0.9 beads).
   Proposed: the engine's stitch check measures `knots` regions as dots (needle span >= 0.9 = visible >= house-min Ø1.1)
   and strokes separately. Check: a beads-only layer reports "dots only", PASS.
22. **Flat line colours**: construction lines + topstitch in near-black on dark denim are invisible (PR #29 item 7). On
   dark garments draw seams light grey (#D2D3D7) and topstitch mid grey, with a "drawing only" note. Proposed: flat
   palette chosen by garment luminance in the engine's flat helper.

## Rev B3 (20 Oct 2026, PR #30 review)
23. **Round dots cannot be judged by IoU on a thread-width coverage mask** (border dots Ø1.5: the DST mask drawn at
   0.35 mm line width reads Ø1.9-2.0, IoU 0.63, "fail" on a correct dot). Project fix: `kjcompare.dot_rows` measures
   each SVG circle against its DST needle RUN (stitches between jumps/trims): span vs art Ø (-0.1/+0.35 mm) and centre
   <= 0.3 mm. Red test: a dot 0.6 mm off first PASSED with a fixed search window (window clipped it) -> runs fixed it.
   Proposed: `qa.dot_match(svg_circles, dst, stops)` in the engine for every `dot`/bead technique. Check:
   tests/test_konpeito_gates.py::test_dot_rows_red_green.
24. **A15 must cover the base areas, not only the motif layers** (band / field / edge of a patch were never gated).
   Project fix: `kjsvg.border_refs` + `kjcompare.area_gates`: coverage % by the area's own stop + no bare blob >= 1 mm2;
   the outer 0.15 mm (the heat-cut line itself) is excluded. Proposed: svgart gates every filled layer as an area.
   Check: test_area_gates_red_green (2 x 2 mm bare square in the band fails).
25. **Placement gates must use an independent centre** (04-06 took the reference centre from the DST-side regions:
   circular). Project fix: `kjcompare.indep_centres` (T8 point = file centre for 05/06; 04 pink offset from the mockup
   pixels; 07 = C5 map) + `candy_position` (unclipped bbox centre of the body stops). Proposed: `qa.position_match(ref_xy,
   dst, stops)`. Check: test_candy_position_red_green (2 mm shift fails).
26. **Red tests must fail ONLY on the guard under test**: the first synthetic star failed on IoU, so deleting the
   outline clause left the test green (prove-the-guard). The star is now tuned so IoU + extents pass and only the
   outline fails; a source mutation (outline clause removed) turns the test red.
27. **Reviewer orientation check**: a back view is seen from behind, so image right = wearer's right (PR #30 review
   item 1 read it the other way). Pages now say so explicitly on T2 / T8 / G4-G6. Proposed: the reviewer prompt states
   the convention (CLAUDE.md "back = x from CB, + = wearer's right on a back view").

## Rev B4 (21 Oct 2026, PR #34 review)
28. **Touching motifs of different colours were traced as one blob** (07 front leg: a pink + a yellow konpeito on one soot
   sprite -> one "yellow" star of 15 px, the pink was missing from every page and file). Cause: the colour mask was the
   union of all hues, labelled once. Project fix: `kjfront.trace` labels each colour class on its own;
   `kjfront.check_merges` stops the build when a blob is > 1.3 x the median size (possible merge). Proposed: the engine's
   motif tracer labels per colour family and runs the merge guard on every traced motif set. Check:
   tests/test_konpeito_gates.py::test_front_trace_splits_the_touching_pair_and_guard_catches_the_old_way (the B3
   all-hue labelling of the real mockup must trip the guard; the per-colour trace returns pink + yellow there).
29. **A position gate whose reference comes from the same trace cannot catch a missing motif** (C5 "independent" 07
   centre = the same map, 0.0 mm by construction). The count needs its own check: merge guard (28) + an explicit count
   in the test. Proposed: motif_match reports "mockup motifs found vs file motifs" from two different readers.
30. **Overlapping motifs in one file**: the motif sewn later lies on top. Bead specks are sewn last, so specks of the
   motif underneath that fall under a later motif's body must be dropped (`kjfront.section_vis`). Proposed: dst2 /
   stop planner drops covered top-layer details generically.
31. **Page date typed by hand went stale** (stamp said 20 Oct, the build ran 21 Oct): DATE = build date (kjcore).

## Rev B5 (21 Oct 2026, PR #34 round 2)
32. **Motifs clipped by the garment edge on a mockup were dropped by the size floor** (07: 3 candies run off the side
   seam and show only as 2-9 px slivers on the cut edge; the 6 px / saturation 0.45 floor kept 1 of the 3, so the map
   was inconsistent). Project fix: `kjfront.edge_slivers` searches a +-3 px band along the traced side seam with a lower
   saturation floor (0.12, >= 3 px), skips slivers already covered by a main blob, and flags every edge motif
   `clipped`; clipped motifs are moved in to the keep-out and counted separately on G7/C5 ("14 whole + 3 clipped").
   Proposed: the engine's motif tracer runs an edge pass on every silhouette and reports whole vs clipped counts.
   Check: tests/test_konpeito_gates.py::test_clipped_side_seam_candies_mapped (green: all 3 found; red: without the
   edge pass only 1; mutation EDGE_MIN_PX=99 turns it red).
33. **dispatch: `review` then `--drain` left two reviewer sessions on one scratch worktree** (21 Oct, PR #34 round 3:
   `dispatch.sh review konpeito-jeans 34` started c95ec030 (busy); the following `--drain` then showed a second
   `tp-review-konpeito-jeans` f9aa136d, idle, in the same worktree, with an empty queue). A worker cannot stop it (auto
   mode denies kill). Proposed: `launch` refuses when a session of the same name exists in any state, and `drain` never
   starts a role/slug that already has a live session. Check: dispatch dry-run test, review + drain, gives exactly one
   session per name in `claude agents --json`.
