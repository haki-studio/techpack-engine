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

## 11. Seam-true wrap from two render views: smooth displacement fields, never a pasted band (Rev B, 19 Oct 2026) — proposed LESSON A17
- **Problem:** the front and back views of an AI render disagree at every silhouette seam (sides, shoulders, sleeve underarm,
  sleeve fold). Rev B's first try (seamfill: a continuation band pasted into the follower piece, joined to its own art at a
  min-mismatch cut, plus a row-by-row stretch) moved the mismatch INTO the panel: the founder saw a near-vertical cut line
  0-60 mm in from the FL armhole/side and a horizontal step in the stripes.
- **Fix (project, `seamwarp.py`):** per piece side (sleeve halves separately) one thin-plate-spline field (scipy
  RBFInterpolator): pass 1 brings the art to the seam (normal displacement from the innermost art, smoothed, faded to 0 at
  fixed edges + 100 mm in), pass 2 slides the follower along the seam onto the leader's stripes (local cross-correlation of
  the tone sequence, then run-edge pins; monotone, slope-limited 0.8, fold-checked det J > 0.25). Tapers only into bare
  fabric. Curls move rigidly with the field at their centre (`mv` recorded per unit so the gates follow the move).
- **Proposed engine fix:** `engine/wrap.py` with SeamSide / Unroll / the two-pass warp; seams from `pattern.draft`.
- **Check:** `discont.py` — straight cut lines (constant-depth tone edges >= 12 mm) per seam side + stripe-edge jumps across
  probe lines 8-120 mm from each seam; before (seamfill) vs after on the same DSTs (G9). Test idea: two synthetic striped
  panels offset 20 mm along a seam -> after the warp, edge jump at the seam < 2 mm and no constant-depth edge inside.

## 12. Fidelity gates must see the same placement as the art (A14 references)
- **Problem:** with the reference mapped by the render map only, every motif the wrap moved (up to 40 mm) failed IoU, so
  the gate measured the wrap, not the trace / digitizing.
- **Fix (project, `gates.py`):** curls + drops: each motif's own render pixels placed rigidly like the art + the unit's
  recorded move; coverage + wave masses: the reference sampled through the inverse of the composed seam warp
  (`seamwarp.warp_grid`). Moves are reported per row. Input pixels only (A14), the transforms are the art's own.
- **Proposed engine fix:** `qa.motif_match(..., move=)` taking a displacement grid; a test with a shifted motif.

## 13. Thread names from a reviewer are not data
- The review asked for "Polyneon 1801" as an ecru: in `engine/pal/threads.json` 1801 is "Barely Blue" #E4E8FF. Ecru
  #D3CAC1 matches Isacord 0184 Pearl (ΔE 3.2) / Polyneon 1682 Taupe (ΔE 5.0). Always match codes with `tech.match()`.

## 14. emb_place.py over all sizes in a sampling package
- The keep-out check loops over every size's art pickle, so a stale Rev A size can print FAIL (or pass) for art that is not
  shipped. Project fix: sizes from argv, default `DOC_SIZES`. Proposed: the engine template does the same.

## 15. Seam TONE handover (Rev B fix round, 20 Oct 2026) — proposed LESSON A33
- **Problem:** seamwarp lines the stripe EDGES up across a seam, but the two render views disagree on the TONE of the same
  stripe: same thread on both sides of the seam only 0-77 % on CF zip / side R / underarm R / armhole front R (art, 1-4 mm in).
  The review asks for "stripe tone and width identical on both sides of every seam".
- **Fix (project, `tonematch.py`):** per seam (fixed priority order: CF zip, sides, shoulders, armholes, underarms, sleeve
  centre), the leader side keeps its threads (body over sleeve; else the side with more stripe on the seam); every follower
  stripe region whose seam samples meet the leader takes the leader's majority thread (>= 60 % of its samples), WHOLE region
  (a tone step inside a stripe would be a new cut line). Regions lock once they led or followed. [M: CF zip 29 -> 97 %,
  side R 59 -> 78 %, underarm R 43 -> 89 %, armhole front R 0 -> 100 %, armhole back L 77 -> 92 %; 52 regions re-threaded]
- **Proposed engine fix:** `engine/wrap.py` tone handover after the seam warp, with the leader rule as a parameter.
- **Check:** test: two striped panels with swapped tones along a seam -> after the pass every seam sample pair has one thread;
  a region far from the seam (> 6,000 mm², < 40 % within 60 mm) is never re-threaded.

## 16. Chenille shipped as a DST before the format was known (B33 hit on a live package)
- **Problem:** the Rev B package (19 Oct) shipped `_CHENILLE.dst/.pes` files as the PRIMARY foam, written by an arc-length
  resample (B32) in a format the factory never named. B33 (added 20 Oct) forbids exactly that.
- **Fix (project):** primary files sew the foam lockstitch (padded tatami + spiral curl cord + loop spiral); chenille is a
  plan per piece (`chenille.plan`: engine `spiral_paths` + `resample_const`, json + preview, constant chord deviation 0).
- **Proposed check:** `tests/`: a project package containing a file named `*CHENILLE*.dst` while factory.json
  `chenille_format` is null fails (scan of out/pkg_*).

## 17. Direction gate on a 0.7 px/mm render
- **Problem:** `qa.direction_match` refuses < 12 ppm (A17); the wave's only reference for most of the garment is the render at
  ~0.7 px/mm (the FL close-up covers one crest). Resampling to 12 ppm satisfies the guard but the "grain" read is blur.
- **Workaround (project, gates.py):** 4 ppm reference resampled x3 to 12 ppm, result reported as INDICATIVE on G8 with the
  source resolution; per-family breakdown (stripes 8 mm tiles, foam + drops 4 mm).
- **Proposed engine fix:** `direction_match(..., source_ppm=)` that marks tiles whose source resolution is below a thread
  pitch as "no evidence" (neither OK nor fail), so a low-res mockup cannot fail or pass the gate; then the A24 rule
  (independent tiles >= 50 %) decides whether the verdict can be given at all.

## 18. Motif gate merged crests through HIDDEN travel runs (fix round 2, 20 Oct 2026)
- **Problem:** `gates.dst_family` drew EVERY stitch of the family's threads. Cream travel runs sewn before a crest and buried
  under it (up to 58 mm on FL) joined neighbouring crests into one DST blob, so the FL big curl (6,361 mm2) read IoU 0.50
  although the art was right (art-mode IoU 0.96). Same class as A21, but the bridge was invisible thread, not a touching motif.
- **Fix (project, gates.py):** the motif gate reads the VISIBLE top layer of the written DST (`qa.visible_segments`, 12 ppm,
  sew order) + `near_mm` (1.5 crests, 1.0 drops). Curls: 39 -> 0-1 failing rows per piece with the same DSTs.
- **Proposed engine fix:** `qa.dst_family_mask(dst, threads, visible=True)` as the one way a motif gate rasterises a file.
- **Check:** test: two squares of one thread joined by a run sewn BEFORE a third fill that covers the run -> two components.

## 19. Drop reference vs stitched threads did not match (fix round 2)
- **Problem:** the drop REFERENCE was cream + grey pixels (CREAM + GREY classes) but the stitched side was the w1 thread only,
  so a drop the render shades grey (traced as w3 / g1) read "MISSING" (IoU 0) with the drop sewn in place.
- **Fix:** drops compare cream + shade + grey threads, and each drop only with the visible stitches attributed to ITS motif
  (unit id of the art object under each visible segment's midpoint) - the reference is still input pixels only (A14).
  The sewn drop is drawn with each stitch shortened by the drop pull compensation at both ends (the fabric pull-in that
  compensation exists for; same principle as `qa.centreline_match` subtracting 2 x pull).
- **Proposed engine fix:** `motif_match(..., out_by_motif={id: mask})` + a `pull_mm` argument for the file rasteriser.
- **Check:** red-then-green: a drop sewn 1 mm off its reference still fails; a drop sewn against a crest in the same
  thread passes only when its own stitches match.

## 20. Close-ups that are super-resolved crops of the mockup (fix round 2)
- **Finding:** the founder's close-ups register onto the mockup views as pure scale + shift (SIFT + RANSAC, 92-98 %
  inliers): they are upscaled crops of the same render (6-14 close-up px per render px), so placement and motif counts are
  the mockup's by construction and their pixels can replace the render's inside each footprint (classes for the trace and
  the A14/A15 reference, grain for A16). A 2x2 composite (sleeves) is split at its separator rows / columns; its masking
  artefacts (exact separator colour, here #1D2B43) count as no data.
- **Proposed engine fix:** `digitize.extract.register.auto_register(closeup, view)` (SIFT + RANSAC, accept >= 100 inliers and
  >= 80 % of matches, overlay PNG) writing the registration JSON the engine already reads; composite splitting by
  uniform separator lines. Needs OpenCV in the engine env (the project ran it on the system python).
- **Check:** test: a crop of a fixture render upscaled x8 with noise registers back to its box within 0.5 render px.

## 21. Bare areas explained as "moved by the wrap" (fix round 2)
- **Problem:** A15's explanation "moved by the wrap" (inside 45 mm of a seam, art within 40 mm) accepted 3,000-5,800 mm2 of
  bare navy per sleeve that the mockup shows embroidered (review: "real bare navy inside the SL art").
- **Fix (project, gapfill.py):** every gap except a keep-out edge is filled from the mockup / close-up tones there, merged
  into the touching stripe / crest (small fills take the neighbour's thread), foam fills get the curl structure (rows along
  the curl + loop spiral). Art level: 18 unexplained -> 1.
- **Proposed LESSON (A15 addendum):** "moved by the wrap" is not an explanation unless the gap's reference content is found
  stitched within the reported shift (3 mm check); otherwise fill it.

## 22. clean_vis deleted parts of small motifs (fix round 3, 21 Oct 2026)
- **Problem:** `dst2.clean_vis` drops fill fragments < 1.5 mm2 or < 0.7 mm wide. On a spray drop (one rigid motif: cream
  body + shade + grey crescents) that removed the shade / grey crescents whole (BK drop at -95.7/157.5: 19.8 mm2 traced,
  12.5 mm2 left) and left bare navy inside the traced outline. A14 failed the drop (IoU 0.61) and A15 never saw it (each
  hole < 25 mm2). Found by following one drop through every build stage (items_for -> ... -> clean_vis).
- **Fix (project, waveart.keep_unit_slivers):** a piece removed by clean_vis inside a rigid motif goes to the touching
  surviving region of the SAME motif (longest shared edge); nothing tiny is sewn alone, the silhouette stays traced.
- **Proposed engine fix:** `clean_vis(vis, absorb_by="unit")`: absorb, don't delete, slivers that belong to a motif.
- **Check:** test: a 5 mm disc split into a 4 mm core + a 0.5 mm ring (different colour, same unit): after clean_vis the
  union area is still >= 98 % of the disc.

## 23. qa.visible_segments under-reads satin (fix round 3)
- **Problem:** the drop gate drew `qa.visible_segments` (each stitch shortened to its visible length, re-centred). On a satin
  zigzag each stroke hides most of the one before, so the re-centred pieces leave false holes and false bare rims: BK
  drop 98 art = reference (IoU 0.98) but gate IoU 0.67, with a hole in the middle of a fully sewn satin.
- **Fix (project, gates.drops_hr_gate):** the sewn shape is the z-buffer raster itself (every stitch in sew order, 0.42 mm,
  pull-in shortened; a pixel counts when its TOP stitch is a drop thread of that motif), stitches within 1 mm of the drop.
  Red-then-green on the round-2 files: drop 98 / 105 / 120 pass (fully sewn), the drops that really lost their crescents
  (82, 99, 100, 104, 109) stay red.
- **Proposed engine fix:** `qa.visible_mask(segs, bounds, ppm, keep=predicate)` next to visible_segments, used by every
  shape gate; visible_segments stays for direction only.
- **Check:** test: a fixed-angle satin square; visible_mask covers >= 97 % of it, visible_segments' mask < 90 % (documents
  why shape gates must not use it).

## 24. Small constructed motifs need ONE declared angle (fix round 3)
- **Problem:** drops were satin 'auto' -> turning satin across an elongated drop; the close-up grain at drop scale runs ALONG
  the drop (edge-dominated): drops scored 10-15 % on A16, dev 70-88 deg.
- **Fix (project, waveart.drop_angles + wavecore declared satin):** one angle per drop motif = its long axis (minimum rotated
  rectangle of the whole motif), all its parts, sewn as fixed-angle satin (split > 7 mm), tatami at the same angle if the
  satin covers < 97 %.
- **Proposed engine fix:** region key `decl` (declared angle, source) honoured by `dst2.build_object` before the turning-satin
  branch; `qa.angle_coherence` reads it.

## 25. Stripe rows follow the close-up grain where it is clear (fix round 3)
- **Problem:** stripes sewn along a geometric flow field + 8 deg cord twist reached 79-84 % on A16 (gate 85).
- **Fix (project, grainfield.py + flowdir.wv_parts):** where a founder close-up covers the stripe (weight >= 0.6) and shows a
  clear grain (coherence >= 0.3), the 6 mm cell is sewn at the close-up's thread angle (input pixels, same map + warp as the
  gate); elsewhere the geometric field + twist. This is A16's rule for organic bands, not a gate change.
- **Proposed engine fix:** `digitize.direction.grain_field(reference, weight)` producing the 1 mm angle / coherence grid that
  fills use as their angle source ('closeup' bucket in A28).

## 26. One-sided seam runs ended as straight cuts (fix round 3)
- **Problem:** where only one piece carries art at a seam (shoulder L: the front wave runs over the shoulder, the back render
  is bare there) the foam stopped on the keep-out as a straight line along the seam (G9 'parallel straight cut').
- **Fix (project, seamedge.py):** along each one-sided run >= 6 mm the foam edge is scalloped into lobes (r 2.6 mm, notch
  2.4 mm), as the mockup's crests end; nothing is invented on the bare partner. Items tagged gen='seam lobes'.
- **Check:** discont.py parallel straight cuts on those runs -> 0.

## 27. Satin pull compensation as an all-round buffer + drop parts under the crests (fix round 3)
- **Problem 1:** `dst2.fixed_satin(p, ang, pull)` hatches `p.buffer(pull)`: the buffer also adds rows along the SIDES, so a
  2 mm drop sews 2.3 mm wide (A14 width / height 1.2-1.3 on 4-8 mm2 drops).
- **Fix (project, wavecore.ends_satin):** hatch the shape itself, lengthen each stitch by `pull` at both ends only.
- **Proposed engine fix:** same change inside `fixed_satin` (and `radial_satin`); pull comp acts along the stitch.
- **Problem 2:** a drop's shade / grey parts sat on the foam-detail layer (under the crests), so a drop traced mostly grey
  was knocked out whole by an overlapping crest (SL: IoU 0.01). **Fix:** every part of a drop motif sits with the drop
  (z just under its cream body, sewn in the drop layers).
- **Check:** test: fixed_satin on a 2 x 4 mm ellipse at 0.15 pull -> sewn width (z-buffer, pull-in modelled) within
  +/- 5 % of 2 mm.

## 28. Foam loop texture read as chaos on the direction gate (fix round 4, 21 Oct 2026)
- **Problem:** the padded foam's loop texture (scalloped contour rings, 2.1 mm apart, w3 run on top) points every which way
  inside a 4 mm tile, so the foam family scored 20-26 % OK (half the failing tiles chaotic), and the live view read as flat
  hatching. Padded rows at the curl tangent deviated from the close-up grain in the other half.
- **Fix (project):** `flowdir.fm_grain_parts` (padded foam + its shade / hollow / inner-blue details, 4 mm cells on the
  piece lattice, angle = close-up grain `ang4` where weight >= 0.6 and coherence >= 0.25, else the old angle) and
  `foamcord.py` (texture = streamlines of the same grain, seeded 2.1 mm, >= 1.6 mm apart; rings stay where no clear grain).
  SL foam 19.7 -> 77.7 % on the first experiment.
- **Caveat (A24):** these angles are read from the close-up the gate grades: self-derived, not independent. Reported so.
- **Proposed engine fix:** a `texture` primitive in digitize for raised / looped fills: grain streamlines (field from the
  close-up) as the top texture instead of contour rings; rings only when no grain is readable.
- **Check:** direction gate foam family on the wave pieces; a unit test that streamlines stay inside the region, keep the
  min gap and follow the field within 10 deg.

## 29. "keep-out edge" excused real gaps; thin tails never filled (fix round 4)
- **Problem:** A15 excused any gap < 400 mm2 within 6 mm of the art limit. The reference is already clipped to the limit,
  so such a gap is mockup art INSIDE the allowed area (SL: a crest 10-15 mm short of the sleeve edge after the rigid curl
  move: the SL wave-mass row with h 0.38). Separately, spray tails 1-2 mm wide off a crest were under the 25 mm2 / 1 mm
  opening, so a traced-short mass never got them (BK mass w 0.79).
- **Fix (project):** explain_gaps excuses only slivers (< 2 mm across, < 2 mm from the limit); gapfill.py fills the rest and
  also TAILS (>= 6 mm2, >= 1 mm wide, touching the art, reaching >= 2 mm beyond it; rims inside 2 mm are not filled).
- **Proposed engine fix:** `qa.uncovered` gets `limit=` and reports near-limit gaps as gaps; a `qa.tails()` helper.
- **Check:** gates A15 table: 'keep-out edge' rows only for slivers; mass rows near the limit pass.

## 30. Straight-cut detector flagged stripes that cross a seam at 90 deg (fix round 4)
- **Problem:** discont.straight_cuts flags any tone edge at constant position for >= 12 mm. A stripe that crosses a seam
  square has exactly such edges BY DESIGN (armhole back L A: 26 'across' lines, all stripe edges running with their
  neighbours), so the in-panel count (88) mixed real cuts with stripes.
- **Fix (project):** `discont.flow_check`: structure tensor of the tone-edge map beside the line (+-6 mm, the line's own
  +-1.5 mm left out); coherent (>= 0.4) and within 20 deg of the line = a stripe edge running with the flow, reported as
  `with_flow`, not a cut. A pasted band end (edges crossing it) stays a cut.
- **Check:** `test_discont_flow.py` (red-then-green: the old detector flags the 90-deg stripes; a shifted band and a
  vertical cut through slanted stripes stay cuts).

## 31. Direction headline pooled every object in a tile (fix round 4)
- **Problem:** the all-visible A16 headline pooled every stitch in an 8 mm tile, so every tile on a crest / stripe border
  read chaotic; the per-family rows already judged each tile on its dominant object (konpeito ENGINE_NOTES 14).
- **Fix (project, gates.py):** headline per object (groups = art object under each visible stitch), pooled kept as
  `pct_ok_pooled` and printed beside it on G8.
- **Proposed engine fix:** `qa.direction_match(groups=...)` as the default for any multi-object piece; the bench prints both.

## 32. Art-chain steps restore from stale "pre" files (fix round 4)
- **Problem:** tonematch.py always restarts from art_M_pretone.pkl when it exists, and gapfill.py restored art_M_pregap.pkl
  at IMPORT time. A partial re-run (from gapfill on) silently dropped the new gap fills, and importing gapfill for a
  diagnosis rewrote the shipped art. Both happened in this round; the rebuilt files were identical to the previous ones.
- **Fix (project):** gapfill restores only under `__main__`; the chain scripts delete art_M_pretone.pkl before tonematch.
- **Proposed engine fix:** an art-chain runner that stamps each stage's input hash into `info` and refuses a "pre" file
  whose hash is not the current upstream output.
- **Check:** after a chain re-run, `info['gapfill']` in art_M.pkl equals the gapfill log of that run.

## 33. Two independently drawn mockup views cannot meet at a seam - redraw the ART, not the stitches (Rev C, 21 Oct 2026)
- **Problem:** four fix rounds tuned warps, tone handovers and stitch settings for the wrap seams; meet / tone stayed
  34-71 % on the DSTs because the traced ART already failed (continuity --art: CF zip 63/37, side L 58/57, sleeve centre
  R 70/32). The front and back AI views show different waves at the same seam: no stitch setting can join them.
- **Fix (project, seamredraw.py, founder 'Do A'):** per wrap seam, both sides unrolled by seam length; two candidate
  pictures of the joined band (each side continued across by a glide map: stripes at their own angle, matched at the
  stitch edge = pivot; rigid motifs moved whole); ONE min-mismatch cut path (DP, image-quilting style) that never comes
  closer than keep-out + 8 mm to the seam, may switch side at a cost, prefers outlines, penalises deleting art and
  one-sided runs at a keep-out corner; foam continued into bare fabric ends in lobes. Art seams 93-100 %, stitched 95-100 %.
- **Lesson (proposed LESSONS A33):** before tuning stitches for a cross-piece match, measure the ART on the same metric
  (`continuity.py --art`); if the art fails, redraw the art in a band (founder-approved design change, shown before /
  after) - never redefine the metric.
- **Proposed engine fix:** `engine/seamband.py` (from this file: Side unroll, glide_cols, cut_path, foam_lobes, apply_zone)
  driven by the pattern's seam walks, for every garment with a wrap; the gates name rows inside redraw zones (still open).
- **Check:** `test_seamredraw.py` (glide continues a slanted stripe straight and meets at the pivot; m=0 mutation red;
  the cut never enters the DMIN band; a one-sided corner run is deleted, not kept).
