# RECAP 2026-10-20: ENGINE_PLAN M5 — SVG parity on Konpeito

Branch `engine-m5-svg` (off origin/main 755faf6). Parallel to M2 (`engine-m2-organic`).
Command: `PYTHONPATH=engine python3 -m digitize.run projects/konpeito-jeans/bench/run_wb_svg.yaml --no-api`
(also coin / spill / starP / starY) -> `projects/konpeito-jeans/out/engine_m5/<el>/` (git-ignored). Parity:
`cd projects/konpeito-jeans && PYTHONPATH=../../engine:. python3 engine_m5_parity.py` -> `bench/PARITY_M5.md` (committed
copy) + `bench/m5/*.png` (panels + delivered-vs-engine live views, committed).

## What was built
| piece | file | notes |
|---|---|---|
| SVG parser | `engine/svgart.py` (new) | kjsvg promoted + generalised: M L H V Q T C S Z abs/rel, rect rx / circle / ellipse / polygon, transform lists on elements AND groups (matrix, rotate about a point, skew), fill attr / style / inherited, evenodd + nonzero. Arcs and `<use>` raise. `layer_mask` = cairosvg per layer (gate reference), `parse_iou`, `thread_of` (exact hex, else CIEDE2000 nearest, extractor refuses > max_dE). |
| SVG -> parts | `engine/digitize/extract/svg.py` (new) | roles per layer (yaml) or by shape: patch_border (band trapezoids across the band + heat-cut edge column, last), field, border_motifs (ellipse florets minus other-fill holes, circle dots), column (glyph_columns, ONE needle width per layer = art - 0.15, loops keep counter, rings radial, eyes -> dots), petals (polar-profile valleys), dot, star, fill. Every part has a declared DirSpec (source rule). z = SVG paint order. Placement frame (translate / centre / scale) for spill + stars. |
| runner | `engine/digitize/svgrun.py` (new) + 2-line dispatch in `run.py` | stages extract / plan / review / compile / gates / panel; `order_complete` sequence; `gate_file()` shared with the parity script. |
| techniques | `column_satin.py`, `dot.py`, `radial.py`, `turning.py` (new) + appended hook in `techniques/__init__.py` | `same_side` density halved internally; bead dots; radial (florets/stars/rings only); turning satin along a declared axis (underlay kept inside the petal). |
| rulebook | `rules/house.yaml` (appended) | 4 technique defaults + 15 patch kinds. Numbers = what Rev A actually sews (tatami 0.45, patch satins 0.36). |
| dst2 | `turning_satin` guard (1 line); `ExactCover`, `_unsewn_init/_unsewn_done`, `make_pattern(exact_travel=None)` | default path untouched; kjcore/kccore source-patch markers kept intact (both still apply). |
| qa | `motif_match(near_mm, out_stops)`, `centreline_match`, `skeleton`, `dst_stitches`, `dst_stop_masks`, `exposed_stitches(min_ex)`, `direction_match(groups)` | inserted after motif_match (not at file end) to stay clear of M2 appends. |
| compile | `write(..., **mp_kw)`; returns runs / regions / exact_trims | additive. |

## Decisions (and why)
- **Patches: no cut-under** (`sequence.cut_under: false`): house patch spec sews motifs on a full field; rule 6's 2-layer
  limit holds (field + motif). SVG parts are design, not fragments, so `absorb_fragments` is not run.
- **Paint order binds only overlaps** (`touch: -0.05`) and the next thread is one whose remaining parts wait on no other
  thread: coin 14 -> 11 stops. The specks now sew after all candies (painter order is still respected where shapes overlap).
- **Exposed-travel thresholds tightened** after LOOKING at the first live view: dot pairs read as dumbbells and hair
  strands were bridged at their tips by travel that the Rev A thresholds (halo 0.35, > 1 mm) accepted. M5 travel check
  and gate: halo 0.25 (pull 0.15 + DST 0.1 mm grid), stitches >= 0.5 mm, > 0.3 mm exposed. Same gate applied to the
  delivered files: 7 (waistband) and 30 (coin) such stitches. Cost: waistband trims 139 -> 161.
  `unsewn_only` kept ON (keep-clean lesson): turning it off gives 141 trims but travel would run on top of sewn satin.
- **Border dots / flower centres / cheeks / accent dots = bead dots** (needle = art - 0.2, min 1.1 / knots 0.9): the
  delivered border dots (auto satin) read IoU 0.61 and fail; bead dots 0.76+. In the live view they read slightly smaller
  and squarer than the fan dots - judged on the sew-out.
- **Petal tints have no centre-run underlay** (the rule table said none; Rev A's builder added one regardless).
- The delivered Rev A pages say tatami 0.42 for BAND/FIELD but dst2 sewed 0.45 (SP_TAT); the engine uses 0.45 = what
  was sewn. Flag for the next pack revision.

## Parity (bench/PARITY_M5.md; same gates on both files)
| element | file | stitches | trims | stops | threads | centreline | motifs | exposed |
|---|---|---|---|---|---|---|---|---|
| wb | delivered | 14,918 | 139 | 11 | 8 | 6/6 | 56/76 | 7 |
| wb | engine | 15,069 | 161 | 10 | 8 | 6/6 | 76/76 | 0 |
| coin | delivered | 10,540 | 82 | 12 | 9 | 1/1 | 26/46 | 30 |
| coin | engine | 10,525 | 84 | 11 | 9 | 1/1 | 46/46 | 0 |
| spill | delivered | 3,651 | 60 | 9 | 7 | - | 9/9 | 0 |
| spill | engine | 3,609 | 58 | 7 | 7 | - | 9/9 | 0 |
| starP / starY | both | 281 | 1 | 2 | 2 | - | 2/2 | 0 |
Max stitch <= 7.0 everywhere; uncovered 0 everywhere; fills coherent.

## Default-preserving proofs
- 28-region synthetic motif through `dst2.make_pattern` defaults: DST/PES sha identical main vs branch (two probes).
- Konpeito Rev A build (`kjstitch.py coin spill wb starP starY`) with the branch engine: DST sha identical to the
  delivered files. keep-clean `kccore._patch_make_pattern` still applies.

## Red -> green (scratchpad m5/mutate.py; all 21 RED, restored green)
group transforms ignored; nonzero read as evenodd; relative h absolute; turning_satin guard removed; motif_match near
ignored; out_stops ignored; centreline width check dropped; centreline d_max doubled; same_side not halved; needle =
art diameter; house-min not reported; bead rows fan; exact_travel accepts all; exposed_stitches never reports;
direction groups ignored; edge not last; ALLOW 0; only first flower per shape; M1 deepest-first thread choice;
run.py dispatch removed; M5 plugins not registered. pytest: 110 passed (95 before).

## Left for M5b / later
- Note 14 is in qa (`groups=`) but not wired into svgrun (no grain reference for SVG sources; could compare against
  the declared part angles instead).
- 'haki' back-pocket lettering is traced (not in the SVGs): stays project code. Front-leg star sections not run.
- No gate yet for "travel on top of sewn same-stop satin" (unsewn_only prevents it; nothing measures it).
- Waistband +22 trims vs Rev A (the cost of 0 floats); try smarter in-stop ordering in M4.
- Pages (F1 base size, CJK font) and stitchrender (notes 5, 6, 10) untouched.
