# Engine notes from the koi blossom hoodie (16 Oct 2026)

Problems hit while building this product, worked around in project code only. Each: problem → proposed engine fix → check.

## 1. Sleeve art placed from a front-view mockup
- **Problem:** the mockup shows the sleeves from the front only; the engine has no way to map a front-view point onto the sleeve
  pattern (Drum Island only had a back→sleeve wrap in seam coordinates).
- **Workaround:** `mockmap.sleeve_P()` / `sleeve_Pinv()`: per sleeve, the mockup's outer silhouette (= sleeve centre line x = 0)
  and inner edge (= front underarm seam) as polylines from the armhole to the cuff seam; a point is mapped by (t along, u across)
  with a cylinder projection (u = arc fraction, projected p = (1 − cos πu)/2) to the S01/S02 front half. `warp_piece()` resamples
  the mockup into sleeve coords for the compare sheets.
- **Proposed fix:** `engine/mockmap.py` with front-panel + sleeve maps driven by a small landmark json per project.
- **Check:** round trip `sleeve_P(sleeve_Pinv(x, y)) ≈ (x, y)` within 0.5 mm on a grid; compare sheet shows mockup koi on top of the render.

## 2. Hatchers fail on degenerate (self-touching) polygons → fills render as their complement
- **Problem:** zig-zag tone boundaries (long-and-short look) left 0-width spikes; `stitchrender.hatch()` rotates the polygon, the
  rotated ring became invalid and `intersection()` returned the complement inside the bounding box (a whole petal rendered as a
  hole; the same rotate-then-intersect pattern is in `dst2.tatami_rows`).
- **Workaround:** `kbvis.tidy()` = make_valid + buffer(+0.03, −0.06, +0.03, mitre) + simplify(0.02) on every visible region.
- **Proposed fix:** `make_valid` + tiny open/close inside `stitchrender.hatch/radial` and `dst2.tatami_rows/fixed_satin` before rotating.
- **Check:** test: a polygon with a 0-width spike hatches to ≈ its own area (not bbox − area).

## 3. Whole-motif keep-out fitting (no cut motifs)
- **Problem:** clipping koi / petals / lily clusters at a keep-out line cuts them in half; dropping them loses mockup detail (A11).
- **Workaround:** `art_size.fit_group()`: every unit (koi, petal) and every flower-cluster core (flowers + stems) is nudged
  (≤ 18–24 mm, spiral search) and only then shrunk (≥ 85 %) until it lies inside that size's keep-outs; cluster leaves are fitted
  one by one after the core move. Moves are recorded per size (art_<size>.pkl info) — 0 units dropped on any size.
- **Proposed fix:** generic `qa.fit_units(items, clip, max_move, min_scale)` in the engine, with the move log printed in G2.
- **Check:** after fitting, every unit's union lies inside the clip (0 mm² outside) on every size.

## 4. Single-hooping pieces in split tables
- **Problem:** `split_clip` returns one section when the art fits the frame; the Grand Line pages assumed S1 + S2 (split line
  drawn at y = 0).
- **Workaround:** pages check `len(sections) > 1`.
- **Proposed fix:** `split_clip` sets `sy = None` and names the single section `S1_single`.

## 5. Same as Grand Line notes 1, 5, 8 (palette/rules hard-wired, font, split y-search)
- Project palette + rules injected by `kbcore.py`; `split_clip` y-search widened by exec-patching (copied from Grand Line).

## 6. Hooded variant
- `front.pieces()` calls `pattern.draft(size, variant="hooded")` and falls back to the Drum Island draft (TypeError). Keep-outs,
  placement and per-size art read the pattern, so re-running `art_size.py` + `run_sizes.sh` after the PR lands re-fits everything.

## 7. Parallel builders: autostash pull reverted uncommitted project files (process lesson, E-section)
- **Problem:** between my first commit and my next, `scene.py`, `kb_motifs.py`, `art_size.py` and `kbvis.py` were silently reset on
  disk to the committed version (an autostash `git pull --rebase` in a shared checkout restores files when the stash pop
  conflicts or another session's rebase is half-done). Stitch files built after that came from the old art; caught only because
  the M counts were identical to the earlier run. Also: `.git/rebase-merge` (autostash) left by another session now blocks
  `commit_project.sh`'s pull, so pushes fail (local main ahead 6 / behind 4 at delivery).
- **Proposed fix:** one git worktree per product (as PLM does), or `commit_project.sh` commits *before* pulling and never autostashes
  other projects' files; refuse to run when `.git/rebase-merge` exists and say so.
- **Check:** builders hash their source files at start of a stitch build and refuse if art_<size>.pkl is older than scene/motif sources.

## 8. Rev B (19 Oct 2026): close-up registration + pixel trace (LESSONS A12/A13) — candidates for `engine/closeup.py`
- **Problem:** A12 asks to register a close-up and trace from its pixels, but every project writes its own (Grand Line
  `closetrace.py`, this project `cu_register.py` + `cu_trace.py`). The AI close-up drifted 13 mm mean / 30 mm max from the
  mockup and dropped 2 of the 6 koi, so a single global warp cannot provide positions.
- **What worked here:** (a) matched features (motif centres, koi head + tail) with brute-force assignment, affine + DLT
  projective fit, residuals in mm → decision rule "positions from the mockup when the mean residual > ~5 mm"; (b) per-motif
  similarity transform (close-up motif → its mockup counterpart) used for tracing AND for the compare-sheet close-up column;
  (c) colour mask → silhouettes (union of row runs, then simplify + round smoothing, `mask_poly`); (d) k-means tones over
  the motif pixels → `clean_labels()` (islands < 70 px and 1-px necks given to the nearest tone — no speckle, nothing
  `clean_vis` would later drop as a fabric hole) → max 3 tones per petal; (e) hand guides (tip + width) only to split a
  flower silhouette into overlapping petals.
- **Proposed fix:** `engine/closeup.py` with `register(features_cu, features_mock)`, `similarity()`, `mask_poly()`,
  `clean_labels()`, `tone_regions(mask, k)`; tests: a synthetic two-tone disc traced back to ≈ its own area per tone,
  `clean_labels` leaves no island under min_px.
- **Check:** `out/closeup_registration.png` + `out/trace_closeup.png` reviewed; compare sheets carry a close-up column.

## 9. Compare sheets from the DST read-back (review item 4, LESSONS A12 check)
- **Problem:** Rev A compare sheets rendered `art_<size>.pkl`, which can differ from what the machine sews (clean_vis,
  merges, splits). Reviewers asked for the final DST.
- **Workaround:** `compare.py render_dst()`: pyembroidery read of the DST, colours from the PES thread list, stitch
  coords + the file's recorded origin = piece mm; thread-width lines, 2x supersampled.
- **Proposed fix:** `stitchrender.render_dst(dst, origin, bbox, ppm)` in the engine so every project's compare sheets use it.
- **Check:** compare sheet header names the DST files it was drawn from.

## 10. Satin direction "along the petal axis"
- `dst2.build_object` sends every elongated satin to `turning_satin` (stitches ACROSS the centreline) whatever `ang` says, so
  a long petal tone band cannot be satin-stitched along its length with a fixed angle. Workaround: radial satin from the
  flower centre (= along each petal axis). Proposed: honour an explicit numeric `ang` for satin (or `st="satin_fixed"`).
