# Forestball — engine notes for the coordinator (problem → proposed fix → check)

1. **Palette is hard-wired to plum + pine.** `motifs2.PAL/HEX`, `tech.COLOUR_ORDER/LAYER_NAMES`, `specbase.TH` (computed at
   import), `dst2.PULL` (computed at import from `tech.RULES`), `dst2.COL_MERGE` are global. Forestball swaps them in place from
   `fbcore.py`, which must be imported first in every script.
   → Proposed fix: a `palette.load(project)` hook (project.yaml) that every module reads lazily; `dst2.PULL` computed on use.
   → Check: a test that builds a 3-region file with a non-plum palette and asserts the PES thread list matches it.

2. **`sheet.header()` footer hard-codes "plum + pine work jacket".** Forestball uses `specbase.header` + `SB.FOOT`.
   → Fix: footer from project config. → Check: grep the rendered page text for the style name.

3. **Licensed elements need a first-class placeholder.** Forestball adds a `"PH"` region (basting outline, own first stop, layer 0)
   and a *void* polygon that knocks out every other region (`back.build(voids=...)`); `pattern_fb.emb_marks` adds the box to DXF layer 8.
   → Fix: `motifs.placeholder()` + `build(voids=)` + `pattern_out.emb_marks` support in the engine (Moon needs the same).
   → Check: test that no stitch of any non-basting stop falls inside the box (DST read-back), and that the box is on layer 8.

4. **LESSONS A1 automated ("nothing floats"):** `fmotifs.drop_floating()` clusters tree parts (bark, twigs, leaves, moss) after the
   keep-out clip and drops clusters with < 150 mm² of limb bark (sprays whose twig was clipped away). Red-then-green: the first
   back build dropped 245 pieces because rock moss shared the limb-moss code (rocks lost their caps) → rock moss got its own code `RM`.
   → Fix: move to engine `qa.py` with a `support_codes` argument. → Check: count of floating pieces printed by each art build;
   proposed LESSONS row A8: "clip can orphan sprays — run drop_floating after every clip; support codes per motif family".

5. **Front keep-outs must use the PATTERN shoulder, not the block's.** The pattern moves the front shoulder seam 10 mm down (chart P,
   `pattern.FWD`); clipping against `drum.Block.front_shoulder_line` leaves art only ~5 mm from the real seam. Forestball's `front.py`
   reads shoulder/armhole/side from `pattern.draft("M")["F01"]`.
   → Fix: Drum Island `front.py` has the same issue (02 near the shoulder) — re-check its T13 shoulder clearance; engine helper
   `pattern.keepout_lines(size, piece)`. → Check: `emb_place.clearances()` shoulder ≥ 15 on every size (it measures on the pattern).

6. **New motifs for the library** (`projects/forestball/fmotifs.py`): `moss_regions/moss_finish` (raised moss clumps, mottled lump
   runs), `mossy_limb`, `mossy_rock`, `leaf_spray` (pinnate), `light_ray` (sheer serpentine run, one object per tone), `stream`,
   `grass_tuft`, `hanging_moss`, `placeholder`. Each needs a render test before moving to `engine/`.

7. **Sheer fills:** the engine has one tatami density. Light rays are done as serpentine runs (rows 1.9 mm) — works, but a
   per-region `density` override on tatami would be the cleaner primitive. → Check: stitches/mm² of `LR` vs `WA`.

8. **`split_clip` "fits" and the section-file "fits" disagree (LESSONS B12 follow-up).** Forestball grade B: `split_clip` reported
   all sections fit, but S2/S4 came out 348.4 mm wide with their basting crosses (> 344 = 360 − 16). The build loop in
   `build_dst3.py`/`build_size.py` only retries smaller `whole_max` when `split_clip` says no.
   → Fix: return the cross positions from `split_clip` and measure fit on art + crosses (as the files are measured); Forestball's
   `build_dst.py` re-checks with the file measure and retries (70 → 55 → 40 → 30 → 20). Root cause: when the best split sits at
   its frame limit, the crosses ON the split line add their 6 mm arm beyond `ext`; Forestball passes the frame − 8 mm to `split_clip`. → Check: `fits` in `dst_splits_<G>.json`.

9. **Leaves-first stop order (LESSONS B2 applied to leaf sprays):** sewing leaf halves before the twigs/bark cut front trims
   249 → 166 (02R) and 257 → 123 (02L). → Proposed LESSONS row: "small detail motifs that touch a later fill (leaves on twigs) sew
   before it". → Check: trims from the DST read-back before/after.
