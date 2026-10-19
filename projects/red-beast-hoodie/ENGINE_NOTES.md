# Engine notes from the Red Beast hoodie (16 Oct 2026)

Each: problem → proposed fix → check.

## 1. Tracing pipeline (new, project code: `trace.py`, `scene.py`, `mockmap.py`)
- **Problem:** hand-composed motif scenes can't follow a hand-drawn AI render (hair strokes, forked lightning, teeth). Tracing colour classes
  and vectorising them per class gave a much closer match (compare sheets).
- **What works:** (a) register a detail render onto the full mockup with SIFT on red/cream feature images + RANSAC homography (skimage, no cv2)
  — 114 inliers, 1.3 mm median residual; (b) classify per pixel at 4 px/mm; (c) "black thread" only inside an envelope grown from the red strokes
  (closing + hole fill), never in gaps between lines on bare fabric; (d) per class: thick core (opening 4.6 mm) → tatami cells at the structure-
  tensor stroke angle, thin rest → skeleton split at every fork, each pixel to its nearest branch → one turning-satin column per branch;
  (e) min width: grow thin strands along their skeleton to ≥ 1.0 mm (width check 11 % → < 1 %).
- **Proposed fix:** move to `engine/trace.py` (`register(detail, mockup)`, `classify(rgb, thresholds)`, `vectorize(labels, codes)`), with a test on a
  synthetic image (forked line → n branches, each satin; a 10 mm blob → tatami cells).
- **Check:** compare sheet + width check < 1 % per code.

## 2. Sleeve mapping from a front-view render (project code: `mockmap.sleeve_to_img / img_to_sleeve`)
- Outer silhouette = sleeve top line, inner edge = front underarm seam, normalised arc length along, cylinder unwrap (asin) across.
- **Proposed:** engine helper for any garment with art on the sleeves seen in a front view.

## 3. Parallel builders: my all-size build job was killed from outside (exit 144) while koi-blossom + moon were starting their builds
- **Problem:** two of seven sizes (XXL, 3XL) were left half-built, no error in my logs. Likely another builder killing by pattern (LESSONS E2/E6).
- **Proposed fix:** `heavy.sh` records the PID + project of every job in /tmp/techpack-slot-N.info; a `scripts/kill_project.sh <slug>` that
  kills only that project's PIDs (exact cwd match), and builders never use `pkill`. Builders also write a `.done` marker per file so a rerun
  can resume.
- **Check:** start two projects' builds, kill one project, the other finishes.

## 4. `tech.stops` / colour order still patched in place (ROADMAP step 1) — same as Grand Line ENGINE_NOTES 1 (`rbcore.py`).

## 5. split_clip search range — same as Grand Line ENGINE_NOTES 8 (build_size.py patches xs + ys to 12–88 %).

# Rev B additions (19 Oct 2026, independent review of Rev A)

## 6. Satin ALONG a stroke (long-and-short hair) is not reachable through `build_object`
- **Problem:** every elongated satin is turned across its centreline (`is_elongated` → `turning_satin`), so a hair stroke
  can only be a cord; `fixed_satin` (stitches along a fixed angle) is used only for non-elongated shapes and zig-zags row to
  row in hatch-list order — on a shape with a hole or a concave bay one row's end jumps to the next row's start ACROSS the
  gap (found on Rev B teeth: 25 mm cream stitches across the black mouth in the DST read-back).
- **Project fix:** `rbcore.patch_dst2()` wraps `build_object`: regions with `fixed=True` sew satin rows along `ang`, ordered
  with `chain_rows` (cell by cell), split at ≤ 6 mm when > 7, + a centre-run underlay along the stroke when ≥ 1.8 mm wide.
- **Proposed engine fix:** `st="satin"` + numeric `ang` + `r["along"]=True` → that path in `build_object`; and make
  `fixed_satin` use `chain_rows` too.
- **Check:** a 20 × 10 mm ring sewn as fixed satin: no read-back stitch longer than the ring's own width crosses the hole.

## 7. Stroke tiling + cords + streaks (`strokes.py`) — candidates for `engine/trace.py`
- `stroke_tiles` (evenly spaced streamlines of a structure-tensor flow field, random lengths, nearest-line tiles) turned
  tone regions into stroke objects (LESSONS A13); `cords` (skeleton, spur pruning + width law, geodesic tip taper) turned
  4–5 mm flat ribbons into 2.5–3 mm cords; `streaks` (bundle PCA + across-profile peaks) gives one tapered column per streak.
- **Check proposal:** synthetic tests — a 40 × 20 mm blob with a 30° field → tiles 1.5–3 mm wide, angles 30 ± 5°; a
  Y-shaped 4 mm ribbon → 3 branches ≤ 3 mm wide; 10 parallel 1.5 mm lines → 10 streaks.

## 8. Split search should weight outline colours
- **Problem:** the split line crossed 28–56 mm of cream cord (a visible step where the two hoopings meet).
- **Project fix:** `build_size.split_clip_wide` counts the cut through cream ×40 (`CREAM_W`). **Engine:** `split_clip(weights={col: w})`.
- **Check:** cream crossed per split in the result json (`cream_cut_mm`), shown on G6.

## 9. Registration crosses must never sew in an art thread that shows (cream)
- Rev A sewed them "in stop 1's thread"; Rev B sews them as their own first stop in Deep crimson (already in every file, so the
  12-colour count is unchanged). **Engine:** `make_pattern(reg_marks=..., reg_col=...)` instead of a WSB thread.

## 10. `pattern.py` now places the welt from block data only (`drum.WELT_L_M`, commit c026934)
- **Problem:** a project that moves the welt (here: PROPOSED 45 out / 27.5 down so it clears the beast's jaw) no longer gets
  it on the pattern: `keep_geoms()` read the block welt and the keep-out cut a 6 mm slot through the throat (found on the
  Rev B compare sheet). The DXF welt will also be at the block position.
- **Project fix:** `front.welt_for()` = the project welt shifted by the block's own size grading of the welt position.
- **Proposed engine fix:** `pattern.draft(size, welt=<polygon at M>)` (or read `front.WELT_L` when the project defines it),
  graded the same way; the DXF welt box + drills follow it.
- **Check:** `emb_place.clearances()` welt ≥ 6 on every size AND the DXF welt box == the keep-out welt.

## 11. `hoodie.Variant` has no `ORDER` (pattern_out.write_dxf / plot_pdf read `blk.ORDER`)
- **Problem:** `plot_pdf(..., blk=hoodie.Variant(welt=...))` raises AttributeError; write_dxf only works with `pieces=`.
- **Project fix:** `garment.Block(HD.Variant)` with `ORDER = HD.ORDER` and `__getattr__` delegating to the module.
- **Proposed engine fix:** `Variant.ORDER = ORDER` (and delegate `measure`, `shape_checks`, `chart`). **Check:** plot_pdf with a Variant.

## 12. A14/A15 gates: how the stitched mask is built decides the verdict
- **Found:** (a) drawing every DST stitch of a colour counts its hidden travel (runs under later fills) as visible thread
  and merges motifs; (b) a 0.6 mm line + 0.5 mm closing + the file's pull comp grows thin cords ~0.5 mm a side, so a
  correct 2 mm cord scored IoU 0.5; (c) two traced motifs 0.5 mm apart that the rebuild + pull comp bridge become ONE
  stitched component and BOTH fail (IoU ~0.5 with width/height ratios 1.0).
- **Project practice (qa_gates.py):** visible-colour raster (stops drawn in sew order, later over earlier), 0.4 mm thread,
  1 px closing, then 0.25 mm erosion = the pull-in the pull comp compensates; art builder cuts a 0.75 mm separation
  between different traced motifs of one family (refmask.separation_cut) and keeps rebuilt objects on the traced silhouette.
- **Proposed engine:** `qa.dst_visible(dst, origin, bbox, ppm)` + `qa.motif_match(..., pull_mm=)` so every project measures
  the same way. **Check:** a synthetic 2 mm satin cord built by dst2 passes motif_match against its own 2 mm mask.
