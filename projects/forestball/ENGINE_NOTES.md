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

## Rev B additions
10. **Registration crosses force a separate thread.** `dst2.make_pattern(reg_marks=...)` emits its own `#00A3FF` basting thread,
    which now counts against the factory's 12-colour limit. Forestball's `build_dst.crosses_in_first_colour()` removes that
    thread + the colour change so the crosses sew in the file's first thread. → Fix: `make_pattern(reg_colour=None)` (None = first
    stop's thread). → Check: `factory.check_threads()` on every split file; stops = colour stops (no extra basting stop).
11. **Split balance + overhangs.** `split_clip` minimises cut length only (S4 136k vs S1 44k stitches) and whole motifs can
    overhang the split line by ~50 mm. Forestball wraps `dst2.cut_length` (cut + 2 mm per 1,000 st of imbalance) and cuts any
    overhang > 8 mm at the line (`trim_protrusions`). → Fix: `split_clip(balance=, max_overhang=)`. → Check: per-section stitches in
    G5/G6; max overhang per section.
12. **Chain-stitch vocabulary motifs** (`fmotifs.chain_limb`, `loop_chain`, `hanging_ropes`): braided strands of oval links
    (each strand its own thread, spiralling), loop chains for free moss strands. Thousands of small regions: the knockout in
    `build()` becomes the slowest step (~16 min per piece). → Fix: build the knockout with an STRtree per z-band.
13. **Close-up labels can be wrong:** `inputs/closeups/closeup_front_right_a.png` shows the BACK scene (stream, rocks, rays, even a
    placeholder box); b + c are the wearer's-right front. → Check: compare each close-up to its mockup crop before tracing.
14. **Parallel `git pull --rebase --autostash` from another session silently reverted this project's uncommitted work**
    (16 Oct 20:13: grand-line's commit_project autostash; the re-apply dropped 9 forestball files back to HEAD). Recovered from the
    dangling autostash commit (`git fsck --lost-found`). → Fix: commit_project.sh should `git add` only its own project and never
    autostash other projects' files (or each builder works in its own worktree). → Check: `git stash list` / fsck after every pull.
