# Parts-based digitizing engine (engine/digitize/), plan of 19 Oct 2026

Founder-approved direction: digitize PARTS, not colours. Techniques are plugins switchable per run. Built toward the PLM
self-serve goal: images in → Claude asks questions → factory-ready pack. House rules: docs/DIGITIZING_PRINCIPLES.md.

## RE-PLAN 2026-10-20 (founder-approved): generic primitives + a vision step — no rule per subject
Founder: "the idea is for me to hand you any mockup and fundamentally you understand what it is and how to embroider it. We're not
going to go through the entire animal kingdom to make a rule for every possible animal. Then we'll never have a self-service solution."
M0–M6 built subject splitters (sky, fall, pool, stratum, cloud, building, trunk/crown/blossom; the KOI trial added fish/lily). They
stay as working reference and test fixtures, but the engine grows from here ONLY through generic pieces:

**Primitives** (each = geometry recogniser + stitch recipe; the techniques already exist):
| primitive | covers (examples) | stitch recipe | direction rule |
|---|---|---|---|
| stroke / column (1–7 mm) | lettering, stems, fins, rails, lines | satin / column satin | across the stroke |
| cord / strip | falls, trunks, vines, fish bodies lengthwise | split satin | along the medial axis |
| band | sky, strata, far roofs, stripes | tatami / guided fill | along the band |
| lobe | clouds, leaves, petals, crowns, bodies | guided / contour fill (+ lit/shade layers) | the lobe's own grain/axis (outline bucket) |
| plane | walls, roofs, flat graphic areas | tatami at one deliberate angle | constructed (independent) |
| radial cluster | florets, fins, tails, rays | radial | from the centre |
| dot | eyes, studs, stars, beads | dot | — |
| run line | outlines, cracks, tile lines | run / bean | along the line |

**Vision step** (`extract/vision`): read the garment MOCKUP (close-ups only inform detail inside mockup motifs, see LESSONS) and write
`parts.labels.json`: every motif → its parts, each with primitive, seed/polygon hint, layer order (z), direction intent, colour, and a
confidence; low confidence → a review question (review.py). The engine turns labels into Parts with existing techniques; no subject code.
- **Now (founder 2026-10-20): the vision step is done by the Claude Code SESSION itself** (it looks at the image and writes the labels
  file) — no Anthropic API calls. In the PLM self-serve flow the same step becomes an API call writing the same file (with `--no-api`
  mocks per the global rule).
- Subject splitters become optional "experts" behind the same labels contract, never required.

**Design-type-aware targets:** gates/targets derive from the design (full-coverage scene vs separate motifs on bare fabric, motif
count, coverage). E.g. the trims-per-100 cm² target applies to full-coverage scenes only — founder: for separate motifs (Koi) it does not
apply. Stitch count is reported, never a limit.

**New milestones (replace M7/M8 ordering):**
- **G1** labels contract + primitives recognisers + labels→Parts compiler; the Castle crop re-run through labels must match or beat
  the subject-splitter result on the same gates.
- **G2** vision step by the session on an UNSEEN mockup with zero new subject code (proof: Koi FR — the fish must come out of
  lobe + band + radial + dot), side-by-side vs Rev B, judged by the founder.
- **G3** design-type-aware targets + the review/question loop surfaced for the founder (then the PLM page uses it).
- then M7 (full Castle via labels), M8 (Wave), PLM self-serve (vision via API).

## Layout (as built M0–M6)
- `schema.py`: Part, Layer, DirSpec (never "auto"), StitchSpec, Block, ObjectPlan
- `config.py`: run.yaml with technique toggles, threads, budget, hoop, gates
- `rules/house.yaml` + `rulebook.py`: kind → technique (first enabled wins; none enabled = hard error) + direction + underlay + comp + limits
- `direction.py`: structure-tensor field, constructed-rule angles, depth angle, neighbour separation, phase field
- `techniques/`: plugin registry. tatami, satin, split_satin, guided_fill, contour_fill, radial (florets only), run, bean, blend, puff, chenille, chain. Each plugin: check, plan, estimate, sequencing, gates.
- `extract/`: register (close-ups at 12 ppm), evidence (tone trace = evidence only), zones, svg, splitters/<kind>
- `sequence.py`: z-DAG, cut-under keeping 1 mm, min fragment, ≤ 2 stacked layers, budget, stops
- `threads.py`: ≤ factory needles, importance-weighted, protected accents, optical mixing
- `compile.py`: hooks into dst2.make_pattern(builder=..., keep_order=..., threads=...), reusing the router/write/readback
- `gates.py`, `review.py` (part_map.png + questions.json / answers.json: the future PLM question step), `panel.py`, `bench.py`, `run.py`

## Milestones (each in its own worktree + PR, tests red-then-green, real-data check)
- **M0:** honest gates (visible-only direction_match at ≥ 12 ppm, per-part angle_coherence, density/trims/satin-shape), 12 ppm registration, bench harness + baseline on the Castle crop
- **M1:** skeleton end to end on the crop (sky + falls splitters, zone stubs, tatami/satin/split_satin/run/bean, sequence v0, threads v0, compile)
- **M2:** organic parts (direction field, guided/contour fill, blends, stratum + cloud splitters)
- **M3:** constructed parts (building template fitter, wall/roof/eave/window/stud) + trunk / crowns / florets
- **M4:** thread planner, full sequencing, review step → crop passes every gate → ⚑ founder live-view sign-off
- **M5:** SVG parity on Konpeito (can run in parallel after M1)
- **M6:** puff, chenille, chain plugins + toggles (⚑ factory format via F1)
- **M7:** full Castle Falls (⚑ founder approval)
- **M8:** Wave

## Benchmark
Castle BK M, crop x −180…+20, y 370…570 mm (check it lies inside back_left close-up coverage).

Targets:
- ≤ 400 parts, < 25 % under 20 mm²
- 0 blob satins, 0 radials outside florets, 0 random angles
- direction ≥ 85 % OK and chaos ≤ 5 %
- ≤ 2 stacked layers
- ≤ 25 trims per 100 cm²
- red and gold present, ≤ 12 colours
- shape and coverage gates pass
- the founder approves the live view

Estimate: about 14–19 builder sessions. Risks: part extraction from AI rasters (zones + splitters + review), gate circularity
(references from input pixels only), and engine churn (additive package, default-preserving hooks, full pytest + one product
rebuild per PR).
