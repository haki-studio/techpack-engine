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
