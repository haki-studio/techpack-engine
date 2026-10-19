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
