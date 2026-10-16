# Roadmap — from one garment to "drop a batch of mockups"

## Where things stand (Oct 2026)

| Stage | Status | Code |
|---|---|---|
| Fit block from a POM chart | generic (chart is data) | `engine/drum.py` |
| Pattern drafting XS–3XL, SA, notches, DXF, 1:1 PDF, QA vs chart, seam walks | generic for a boxy jacket block; new silhouettes need new drafting functions | `engine/pattern*.py` |
| Motif library (plum branch, blossoms, buds, pine fans, bamboo, mist, snow, leaves) | reusable motifs | `engine/motifs*.py` |
| **Scene composition** (placing motifs to match a mockup) | **hand-written per design** | `projects/*/back2.py`, `front.py` |
| Region → stitch file (travel, satin, underlay, blends, density, stops, splits) | generic | `engine/dst2.py`, `engine/tech.py` |
| Placement per size + keep-out solver | half generic (rules are data, pieces named per garment) | `projects/*/emb_place.py` |
| Spec pages, embroidery pack, garment pack | page builders are per project today | `projects/*/spec2.py`, `espec.py`, `pack.py`, `gtp*.py` |

## Next steps

1. **Project config instead of code.** One `project.yaml` per style: POM chart, fabric + trims, palette, element
   list (name, piece, process, keep-outs, grade rules), house spec. Page builders read it; `drum.py` → `block.py`.
2. **Motif authoring stage (agentic).** For each element in a new mockup:
   - crop + name the recurring motifs; match against the library (CLIP-style embedding + a human-readable index);
   - for a new motif, an agent writes a generator (shapely regions with stitch type + angle + layer), renders it
     beside the crop, scores it (SSIM / colour histogram / silhouette IoU) and checks stitchability
     (LESSONS A/B), iterating until both pass; then it's saved to the library with tests;
   - composition: place motifs to match the mockup layout (keypoints from the crop), then attach checks
     (LESSONS A1: nothing floats).
3. **Batch runner.** `techpack run inbox/*.png` → one worker per mockup (and per element / per size inside it),
   each writing to `projects/<style>/`, with the LESSONS checks as gates between stages and a summary table at
   the end. Locally via Claude Code subagents + `xargs -P`; long stitch jobs on all cores.
4. **Tests.** Golden-file tests for the stitch engine (trim count, stitch count, max stitch on fixed fixtures),
   pattern QA (measurements vs chart for every size), document builds (page count, no overlapping text).
5. **Factory loop.** Record sew-out feedback per element (puckering, coverage, registration) in the project and
   fold it into density / pull-comp rules — the only way to know the files are right is a sew-out.
