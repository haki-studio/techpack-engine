# Engine notes from the Comet City hoodie (16 Oct 2026)

Problems hit while building this product, worked around in project code only. Each: problem → proposed engine fix → check.

## 1. Graded fronts on longer bodies: the scene floats above the hem
- **Problem:** fronts are graded about the CF neck (A 92 / B 100 / C 108 %) so the halves meet at the zip. Body length grows
  ~21 mm per size, so on L/XL (grade B) the city + railing + bicycle ended 33 / 53 mm above the hem-band seam (keep-out 10);
  the mockup has them standing on the hem band. Same on S and XXL/3XL (31 mm).
- **Workaround:** `art_size.py` slides every item down by `dy = hem(size) − hem(M) × scale`, ramped in by the item's reference
  y (0 above y 200, full below y 340 at M); whole motifs move together (per `unit`), cloud tone patches move with their cloud
  silhouette (`cref`), the comet never moves (strands would shear). CF marks (top rail, kerb) shift with it.
- **Proposed engine fix:** `grade_scene(items, size, anchors={"neck": y0, "hem": y1}, ramp=(a, b))` in the engine, with unit / group
  aware translation.
- **Check:** hem clearance on every size within 10–13 (T13 / `emb_place.py`): before 30–53, after 10.4–13.0.
- **LESSON proposal (A12):** "Art that sits on a garment edge (hem, cuff) is anchored to that edge per size, not only scaled about the neck."

## 2. Mockup tone areas pick up garment details (seam topstitching, welts, zip tape, star glows)
- **Problem:** reading clouds as the mockup's own luminance areas also read the side-seam topstitching (a 300 mm tall strip),
  the welt pocket bags, the zip tape edge and the glow around the red falling star / comet fringes as "cloud" fills.
- **Workaround:** cloud masks exclude: 20 mm inside the side/armhole seams, 12 mm around the welt boxes, 17 mm each side of CF,
  a 2–9 mm zone around the comet and every star/meteor head; components < 12 mm² (sky: < 25 mm²) dropped.
- **Proposed engine fix:** `qa.mockup_mask(..., exclude=[seams, welts, zip, motifs])` helper that every tone-trace uses.
- **Check:** compare sheet shows no tone strips along seams; FL lost a 300 mm cloud strip + a welt-shaped haze block.

## 3. Sleeve mapping from a hanging-sleeve mockup
- **Problem:** the mockup shows the front half of each sleeve as a curved, foreshortened band; motifs must land on the flat
  sleeve piece. No engine support.
- **Workaround:** `mockmap.SP / SPinv / swarp`: along the sleeve = shoulder point → cuff seam, across = half cylinder
  (`x = W(y)·(asin(2u−1)/π + ½)`), silhouette tables read from the zooms. The 10–28 mm next to the silhouette edges is background /
  body and is not read.
- **Proposed engine fix:** `mockmap.sleeve_map(silhouette, piece)` in the engine (the 4 hooded products all have sleeve art).
- **Check:** sleeve compare sheets (`out/compare_SR.png`, `compare_SL.png`).

## 4. Palette / rules / stop order still hard-wired (same as Grand Line note 1)
- Worked around in `cccore.py` exactly like `glcore.py`. A project palette file (ROADMAP step 1) would remove ~60 lines per project.

## 5. Motifs for the library (`cc_motifs.py`)
- comet strand bundle (`strand`: offset ribbons along a spline spine, tapered both ends), tapered meteor with head dot,
  8-ray falling star, 4/8-point sparkles with white centres, palm / fern plant (`palm` + `pinna`: arching pinnate fronds,
  two-tone leaflets), bicycle line art, figure seen from behind (original pose), lamp post.
- Proposed: `engine/motifs3.py` with a render test per motif.

## 6. Hood variant timing
- The hooded block (`origin/hooded-variant`) changes the cuff to a 60 mm self-fabric band with cuff = opening 1:1, so the sleeve
  pieces get longer + narrower at the cuff. `front.pieces()` switches to `draft(size, variant="hooded")` automatically once the
  engine has it; re-run `sleeve_scene.py`, `art_size.py`, `build_size.py` for all sizes, then the documents.

## 7. Rev B (18 Oct): registering a re-composed close-up (LESSONS A12 in practice)
- **Problem:** the founder's detail view re-composes the scene: the comet and sky stars register (exact on 7 features), but its
  clouds tilt and its city/figure are ~2x larger. One global fit folded the warp into a swirl (two conflicting cloud points).
- **Fix (project):** `closeup.py` = projective fit on all matched features + thin-plate spline on the SKY features only, a Jacobian
  fold/stretch mask, and the close-up used only where it agrees with the mockup layout (comet traced; clouds/city layout from the mockup).
- **Proposed engine fix:** `engine/register.py` with this fit + `residuals()` + fold mask, and a reviewer overlay (close-up warped
  over the mockup, half-transparent) as a standard compare-sheet panel.
- **Check:** residuals printed in scene_meta.json (`closeup_residuals`): 0.0 px on the 7 sky features.

## 8. Traced streaks below the reference resolution
- **Problem:** the close-up is ~2 px per garment mm; comet strands are ~1 mm, so palette tracing gives the colour layout and extent
  but a slab, not strands.
- **Fix:** traced body (extent + colour bands from the close-up) + generated tapering satin streaks inside the TRACED extent
  (per-t extent percentiles, smoothed) — the reference decides where and what colour, the motif only adds sub-pixel strands.
- **LESSON proposal:** "Trace what the reference resolves; generate only below its resolution, constrained by the traced extent."

## 9. Compare sheets from the DST, not from the art
- `compare.py` draws every stitch of the written full DST (thread colours from the PES list) — the reviewer sees what sews.
  Proposed: `stitchrender.dst_render(files, bbox, ppm)` in the engine.

## 10. Welt keep-out checked on stitch points
- `welt_check.py` reads every DST (full + splits) back into garment mm and measures the nearest stitch to each size's welt box
  (Rev B: welt keep-out 8 = 6 + 2 cut-out margin; worst stitch 7.75 mm). Proposed: generic `qa.stitch_clearance(dst, origin, geom)`
  for every keep-out (the art-outline check misses pull comp + underlay).

## 11. Rev B review round (19 Oct): tone thresholds, streak-vs-cloud, comet body
- **Tone thresholds in thread terms.** Cloud tones were cut at mockup luminance 100 / 128 / 165, but the threads they map to
  have luminance dusk 90, cloud 133, ice 179, white 240 — so ~half the cloud area stitched one tone too light (review: "posterised,
  too white"). Fix (project): thresholds at the midpoints between the thread luminances (66 / 112 / 154 / 205), tone masks smoothed
  at 1.0 mm and parts < 5 mm² dropped. **Proposed engine fix:** `tech.tone_thresholds(colours)` returning the midpoints, used by
  every tone trace. **LESSON proposal (A14):** "Cut tone regions at the midpoints between the luminances of the threads they
  become, never at round numbers of the mockup." Check: compare sheet tone area per thread vs mockup histogram.
- **Saturated streaks read as cloud.** A fine azure streak beside the comet passed the cloud luminance test and stitched as a dusk
  cloud blob (review "ghost tail"). Fix: cloud mask also needs saturation < 0.72 (clouds p90 = 0.60, streak 0.87); the streak is a
  meteor now. Proposed: the same gate in the `qa.mockup_mask` helper (note 2).
- **Body vs strands.** Strands alone (satin ribbons with fabric gaps) read as a hair-thin bundle; the mockup comet is a solid body
  with streak texture. Fix: tatami body over the whole traced extent (bands placed around the traced core line), strands on top in
  a neighbour tone. Feather edges with a CONTINUOUS arc length (projection on the spine), not the nearest-vertex index — the index
  gave 2 mm square "battlement" steps.
- **Speed:** `np.vectorize(spread)` over a 3 M-pixel grid inside a 40-step loop made scene.py take > 5 min; `np.interp` on the
  array directly: 38 s. Never vectorize a scalar interp.
- **E2/E6 hit again:** `pkill -f "cProfile.run"` killed this builder's own shell. LESSONS E2 stands; suggest `scripts/killpid.sh`
  that refuses patterns and takes a PID only.

## 12. A14 / A15 gates in practice (19 Oct) - fidelity.py
- **Reference masks need the same exclusions as the stitched masks**, or the gate measures the mask, not the art: star / meteor zones,
  the comet zone, the all-size keep-out band (LIM_ALL, not one size's clip) and the 8.5 mm lobed-bank-end band are applied to BOTH.
- **Touching neighbours merge in `motif_match`**: a traced meteor beside the comet body counted as one component with the body
  (IoU 0.11). Fix in the art (1.2 mm kob gap around meteors near the comet - also truer to the mockup) and no closing on the comet out-mask.
  Proposed engine option: `motif_match(..., out_labels=)` so callers can pass per-object labels instead of connected components.
- **What the gates found that three reviews missed:** a meteor skipped because its midpoint fell in the comet zone; hand-placed meteors
  ~2 mm off their streaks (now traced: PCA axis + percentile ends + perpendicular spread); the comet body following the close-up instead
  of the mockup (placement ref); small clouds dropped by a 30-60 mm2 size filter; the pale walkway below the kerb; sleeve cloud undersides
  (saturated blue = read as foliage); the hanging sleeve's inner-edge highlight read as cloud when the readable band went to 0.93 W.
- **Uncovered gaps need a classifier**: photo-render glow around stars/meteors and the bright haze between generated (IP-original)
  towers are light, not thread. fidelity.py labels every gap (keep-out edge / glow / skyline band / foliage / readable edge) and blocks
  on any UNEXPLAINED. Proposed: `qa.uncovered(..., explain=callable)` in the engine.
- **Art-mode iteration**: `python3 fidelity.py art` rasterises art_M.pkl (seconds) - the delivered gate always runs on the DSTs.
