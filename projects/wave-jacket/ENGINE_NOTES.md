# Engine notes from the wave jacket (16 Oct 2026)

Problem → proposed fix → check. Worked around in project code only.

## 1. Tracing a whole view from a low-res render (new, reusable)
- **Problem:** every batch build hand-places motifs; for this design a tonal trace of the whole render was faster and more faithful.
- **What worked (project):** `wavetrace.py` (Lab nearest-tone classes on a x4 Lanczos upscale, majority filter, stripe slits closed into the band,
  band tones continued under foam, thick cream = crests / long thin cream on a band = rope lines, silhouette-edge highlights dropped) +
  `waveart.py` (crests split into curls by watershed, curls + drops moved as RIGID motifs on an anisotropic map so they stay round).
- **Proposed fix:** `engine/trace.py` (moon's tracer + these steps) with `rigid_components()`; a render-to-pattern map object (`mockmap.py`).
- **Check:** golden test: a synthetic 3-tone image traces back to the same polygons (IoU > 0.95), a disc stays round on a 1.3:1 map.

## 2. Sleeves on AI flat lays cannot be mapped seam-true
- **Problem:** the render's drop-shoulder sleeves are ~1/2 the pattern sleeve width and long; a Coons patch armhole→cap folded over (Jacobian
  sign flip near the cap) and blew curls up 40x.
- **Workaround:** affine map fold line → sleeve centre line, widened ≤ 1.45 so the render's inner edge meets the underarm keep-out; armhole
  15 mm keep-out on both pieces (no wrap marks).
- **Proposed fix / LESSON (A12):** "AI flat lays draw sleeves that do not fit the pattern: place sleeve art by fold + shoulder + cuff, never
  seam-true, unless close-ups of the sleeve are flat." **Check:** sleeve-map Jacobian determinant > 0 everywhere in the sleeve quad.

## 3. Chenille / loop look has no native stitch type
- **Problem:** foam loops are built as thin `run` polygons (scalloped contour spirals); each separate loop object on top of an earlier fill
  is an exposed move → trims. `build_object` walks only the exterior of a run polygon, so loop rings had to be chained into open spirals.
- **Proposed fix:** a native `loop` / `curl` texture stitch (path given as a LineString, sewn in the same stop as the fill under it, so travel
  hides under its own fill) and support for LineString line regions in `build_object`.
- **Check:** a 40 mm padded disc with loop texture sews with 0 extra trims.

## 4. `build_size` split loop crashed on an empty split section
- **Problem:** `split_clip` can return a quarter with no regions (sleeve art in two groups) → `make_pattern([])` → IndexError in `bounds_of`.
- **Fix (project):** skip empty sections. **Proposed:** `split_clip` drops empty keys; `bounds_of([])` raises a clear error.
- **Check:** test split of two far-apart blobs in a 2x2 frame grid returns 2 sections.

## 5. heavy.sh + nohup from an agent shell
- `( nohup ./run_all.sh & )` from the agent's Bash tool kept running although it looked dead (slots were all taken by other products, logs
  stayed empty), and a second launch raced it on the same files. **Proposed:** `heavy.sh` writes a "waiting for slot" line to stderr; run
  scripts take a lock file per project (`flock projects/<slug>/.run.lock`).

## 6. Registering a perspective close-up onto the render (A12)
- **What worked:** `register_cu.py` — score = NCC of the white (foam) + blue (band) masks of the warped close-up vs the render; coarse
  grid over rotation / scale / shift, then Powell refinement of an affine and of a full homography (score 0.97 → 1.32 of 2.0). The close-up's
  classes then replace the render's inside its footprint (`wavetrace.closeup_labels`). A visible seam remains at the footprint edge.
- **Proposed fix:** `engine/register.py` (mask-NCC homography search) + feathered blending of the two label maps at the footprint edge.
- **Check:** registering a crop of the render itself (rotated 30°, scaled 3x) recovers the crop box within 2 px.

## 7. Turning satin left 5-15 % of the wave stripes bare in the DST (found in QA, 19 Oct 2026) — proposed LESSON B25
- **Problem:** stripes were typed satin when `2·area/perimeter < 5 mm`; hole perimeters count, so a 480 mm stripe with 38 holes
  (5,933 mm²) read as "thin" and got turning satin on ONE centreline: 26 % of it never sewn. All WV satin on M BK: 84.6 % covered
  (with holes) / 95.2 % (without); ~4,200 mm² of bare fabric in the stripes. The art-region preview (stitchrender) showed it solid,
  so the compare sheets looked right; only a stitch-by-stitch render of the DST showed the gaps.
- **Fix (project):** stripes sew tatami along the stripe; turning satin only for stripes with no holes and width < 3 mm.
  [M BK coverage 95.7 → 99.6 %; 237,785 → 276,487 stitches; trims 1,207 → 1,194]
- **Proposed engine fix:** `build_object` measures coverage of each satin object (rasterise its stitch lines at 0.4 mm vs the
  polygon) and falls back to tatami below 98 %; `width_of` uses the exterior only. Compare sheets always render the DST, never the
  region art.
- **Check:** `qa.dst_coverage(dst, art)` ≥ 98 % per stitch code on every file (project script: coverage per code/type, M all pieces);
  test: a 200 × 4 mm S-curve stripe with 10 holes sews ≥ 98 % covered.

## 8. Sleeve fold: bare 15-50 mm band down the sleeve centre + the fold highlight sewn as white dashes (QA 19 Oct 2026)
- **Problem:** the sleeve map lays the render's outer contour on the sleeve centre line, but the trace drops the silhouette-edge
  shading, so each half stopped 13-19 mm short (M) and the sewn sleeve had a bare vertical band; the render's fold highlight
  survived as 19 (SR) / 14 (SL) tiny "drops" in a vertical line on x = 0.
- **Fix (project, `waveart.close_fold`):** per half, g = 25th percentile of the innermost art per 10 mm row; stretch the half from
  its underarm edge so |x| = g lands on 0 (stripes point-mapped, curls/drops moved rigidly); drop units < 20 mm² within 6 mm of x = 0.
- **Proposed engine fix:** sleeve maps take the fold contour from the ART edge (trace mask), not the garment silhouette.
- **Check:** innermost art per 20 mm row on each half ≤ 5 mm from the centre line where both views show art; no unit < 20 mm²
  within 6 mm of the centre line.

## 9. Turning satin fans open on the outside of a bend: drops, curl shades, grey hollows (QA 19 Oct 2026)
- **Problem:** after the stripe fix, the DST coverage gate still found 94-97 % on DR / FM-sh / FM-gr satin (M): wedge gaps on the
  convex side of curved drops and shades, and one 60 mm² FM-sh object on SL almost bare.
- **Fix (project, `wavecore.covered_build_object`, patched over `dst2.build_object`):** every satin object is rasterised from its
  own stitches (0.6 mm thread, polygon eroded 0.25 mm); < 97 % → rebuilt as fixed-angle split satin (auto angle), or tatami if
  that covers more. [M: 15-23 % of satin objects fall back to fixed satin, 1-7 per piece to tatami; every code ≥ 99.6 %]
  Pitfall: drawing the thread at 0.45 mm against 0.42 mm rows rounds to gaps at 10 px/mm and condemned 77 % of objects.
- **Proposed engine fix:** the same guard inside `build_object` (and `qa.dst_coverage`), counts in the build stats.
- **Check:** coverage.py per code ≥ 98 % on every file; test: a 6 mm C-shaped satin drop sews ≥ 98 % covered.

## 10. Sleeve art boxes not monotonic across sizes (coordinator review, 19 Oct 2026)
- **Problem:** SL widths XS..3XL 379/363/411/394/333/425/390, SR heights jumping. Two causes: (a) the fold-highlight dashes (note 8)
  set the SR top on some sizes; (b) the render region that belongs to a sleeve was rebuilt per size from that size's armhole mapped
  back into the render, so curls near the sleeve/body boundary switched piece size to size (SL rigid motifs 60/53/61/55/49/56/53;
  XL lost 12 vs M) and were then clipped at the keep-out.
- **Fix (project):** the sleeve render region is the size-M one on every size (placement map still per size). After: SR
  395/409/430/443/456/478/490 × 285/293/301/310/318/327/338; SL 378/385/411/417/445/450/480 × 340..400; motifs 55-58 / 59-61.
- **Open:** BK heights now plateau (XS = S 457, L = XL 496) — check which motifs moved between back and sleeve before the
  graded rebuild (after the strike-off).
- **Proposed engine fix / check:** any per-size map keeps piece membership fixed (decided once on the base size);
  test: art box w and h non-decreasing XS..3XL for every piece, motif count per piece within ±3 of M.
