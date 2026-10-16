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

## Engine proposals from the first /techpack batch (Grand Line, Forestball, Moon — 16 Oct 2026)
Merged: unknown colour raises in `tech.stops()`, pull comp read at call time, split fit counts the cross arm on the
split line, stitch split at 7.4 mm, `sheet.FOOT`, shared venv in `env.sh` (LESSONS B16–B18, E5). Still open (each built
three times over in project code, so this is the next engine work, in this order):
1. **Project palette/rules file** (all three builds patched `motifs2.PAL/HEX`, `tech.RULES/COLOUR_ORDER/LAYER_NAMES`,
   `dst2.COL_MERGE`, `specbase.TH` in place: `glcore.py`, `fbcore.py`, `moonpal.py`). Also per-code density
   (`RULE_DENSITY`) for sheer rays / low-density moon.
2. **First-class placeholder** for licensed areas (`moonstitch.add_placeholder`, Forestball `PH` + `build(voids=)`) — LESSONS A9.
3. **Any-grid hoop split** (`projects/moon/moonsplit.grid_split`) and frame-adaptive cross spacing (Grand Line `split_marks(ext=4)`).
4. **Pattern config**: materials, welt size/position, style code, embroidery-piece map (`pattern_gl.py`, `pattern_moon.py`, `pattern_fb.py`);
   `pattern.keepout_lines(size, piece)` (LESSONS C8).
5. **QA**: `drop_floating` into `qa.py` (A8); `absorb_slivers` with line regions keeping their slivers (B19); seam-wrap helper (`scene.seam_check`).
6. **Hidden-travel router**: merge later-stop masks before insetting; native overlay (`ko=False`) regions; dashed-run stitch; auto-section fills with many holes (B14).
7. **Motif library** (with a render test each): clouds/sparkles/sun/sea (`grand-line-jacket/gl_motifs.py`), moss/limb/rock/leaf spray/
   light ray/stream/grass (`forestball/fmotifs.py`), cloud/moon/pole/wires (`moon/moonmotifs.py`).
8. Fonts: `get_fonts.sh` installs Noto Sans CJK; `sheet.py` warns when `fc-match` falls back.
