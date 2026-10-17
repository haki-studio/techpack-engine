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
