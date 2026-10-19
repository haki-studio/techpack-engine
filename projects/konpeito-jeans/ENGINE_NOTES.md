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
