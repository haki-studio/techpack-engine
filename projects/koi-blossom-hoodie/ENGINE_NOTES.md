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

## 11. Garment pages on the zip-hoodie block (19 Oct 2026)
- **`hoodie.Variant` has no `ORDER`**: `pattern_out.write_dxf/plot_pdf` iterate `blk.ORDER`, so `blk=hoodie.Variant(welt=...)`
  raises AttributeError. Workaround: `garment.Blk` (ORDER = hoodie.ORDER, draft = front.pieces). Fix: `Variant.ORDER = ORDER`.
  Check: `write_dxf(["M"], tmp, blk=hoodie.Variant(welt=...))` in a test.
- **`pattern_out.EMB_ON / EMB_NAME` are the Drum Island elements**: a design with other element names must monkeypatch them.
  Fix: `write_dxf(..., emb_on={code: [element]}, emb_name=...)` or read them from the project's `emb_place`.
- **Block pages are not importable as a library**: `projects/zip-hoodie-block/build.py` computes `G = {sz: HD.draft(sz)}` at
  import; a design with a welt override has to replace `G/gM/mM` and `hflat.Flat.welt` after import (`garment.py`). Fix: move
  the page builders to `engine/hoodie_pages.py` taking `(G, flat_cls)`.
- **`shrink.py` re-encodes every image as RGB**: a transparent PNG (art on a flat) turns its background black. Workaround: skip
  images with an SMask / alpha. Fix: same in the shared shrink step. Check: render the shrunk T1 and look at it.

## 12. A14/A15 gates on a 1 px/mm mockup (19 Oct 2026)
- **Small motifs fail IoU on pull compensation alone**: a traced 5–15 mm² petal stitched with 0.2 mm pull per side reads
  IoU 0.55–0.69 against its own reference. Fix used: inset traced geometry by the pull comp (0.2; 0.32 under 8 mm²) so
  stitched = traced, and run the gate at 5 px/mm (3 px/mm quantisation alone costs ~0.1 IoU on a Ø2.5 mm dot).
  Proposed engine fix: `dst2` option `pull_inset=True` for traced regions; `qa.motif_match` docstring: recommend ppm ≥ 5.
- **`merge_stops` mixes families in one stop** (a navy stem moved into the navy traced-fill stop), so a DST mask split
  by per-stop codes cannot isolate stems. Workaround: subtract the art's stem footprint (+0.45) from both masks and list
  stems as "generated, not traced". Proposed: `readback.dst` per-object spans (stop, object id, code) so masks can be
  split per code from the file itself.
- **Garment details in a front-view mockup mapped onto pieces**: seams/topstitching land INSIDE the art area after the
  mockup→piece mapping. `mockref.flora_mask` order that worked: piece clip → welt +4 mm → edge-connected white background
  → sleeve inner 28 % (body visible behind the sleeve) → replaced-motif footprints → colour test → opening 2 mm (lines) →
  closing 1.6 mm + fill holes. Proposed: `engine/mockref.py` with this pipeline + a test on a synthetic seam line.
- **Close-up vs mockup reference conflict**: a motif traced from the close-up does not match the 1 px/mm mockup pixels.
  Composed reference used: mockup ∪ close-up-traced silhouettes; small mockup bits within 1 mm of a close-up motif are
  "close-up zone" (counted on the compare sheet, not gated). Proposed: `qa.motif_match(..., exclude=mask)`.

## 13. Rev C (19 Oct 2026): non-circular A14 gates — `engine/refmask.py` candidate
- **Problem:** Rev B's gate references were partly built from the art (art fish regions as the fish reference, rasterised lily art
  ORed into the flora mask, stem footprints removed from both sides, DST mask hole-filled) — the gate proved DST == art.
- **Fix used:** `refmask.py` imports nothing from the art side (no scene.pkl, art pkl, templates). Reference = input pixels only:
  mockup warped to the piece grid, close-up pasted per registration disc, garment details from the PATTERN (keep-outs, welts),
  fish found by colour (light blobs holding red), isolated thin lines dropped (topstitching), stems kept in. DST mask = 0.4 mm
  stitch lines + 0.5 mm closing, never hole-filled. The art tracer has its own classifier (different thresholds) so the gate is
  not fed by the tracing mask.
- **Proposed engine fix:** `engine/refmask.py` (source(), art_area(), flora(), fish_px()) + a test that imports it with the art
  modules blocked (`sys.modules["scene"] = None`), and a red-then-green test: a stand-in shape at the right position fails.

## 14. Fish poses from pixels (heading bug found)
- The typed Rev B fish list had the SL lower fish reversed (tail/head). `refmask.fish_poses`: blob centroid + PCA axis, head =
  the end away from the peduncle (width minimum at 10-35 % of the length) — matched 17/18 typed headings within 4°, the 18th
  was the typed error. Proposed: `qa.motif_pose(mask)` in the engine; check: synthetic fish silhouette, both orientations.

## 15. Tones by nearest thread (Lab) + luminance bands
- Rev B ranked k-means classes by luminance onto a fixed thread list, so a pale-ish lily became ice/white whatever its colour.
  Rev C: per pixel the nearest palette thread in Lab; blurred rim (outer 1 mm at 1 px/mm) takes the interior tone; per motif
  <= 2-3 dominant threads laid out as bands cut on the smoothed luminance (sigma 1.2 mm) at the midpoints of the threads' own
  mean luminance -> long-and-short steps, no speckle. Thread-mix mean vs source mean matched within ~5 levels on every lily.
  Proposed: `engine/tones.py` (nearest_thread, tone_bands) + test: a two-tone gradient disc gives 2 bands, no islands.

## 16. Satin along an elongated petal
- Same as note 10: there is no "satin rows along the axis" for elongated shapes; Rev C uses tatami at the petal-axis angle
  (rows along the petal). Proposed: `st="satin_fixed"` honouring a numeric angle.

## 17. Vectorised sleeve mapping
- `mockmap.sleeve_P` calls griddata per point; tracing polygons needs thousands. `floratrace.to_mm` does one griddata call per
  array. Proposed: make `sleeve_P` accept arrays.

## Rev D (22 Oct 2026, RFQ edition): engine asks
- factory.requests_page (F1): "art W x H mm → N hoopings today" trips factory_copy's history pattern (`N mm → M`). Reword in the engine,
  e.g. "art W x H mm: N hoopings on the proposed frame". Koi uses a narrow scrub rule for it (rfqgate.SCRUB) until then.
- factory.requests_page reads the ONE factory profile on file (frames "on file", needles "confirmed", chenille yes). For an RFQ to a
  new factory those are another factory's facts. Koi's pack.f1_pages passes a neutral copy in factory mode (frames/needles/chenille/
  thread card = not confirmed). The engine should take a per-supplier profile (or an "unknown supplier" default).
