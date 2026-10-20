# Parts-based digitizing engine (engine/digitize/), plan of 19 Oct 2026

Founder-approved direction: digitize PARTS, not colours. Techniques are plugins switchable per run. Built toward the PLM
self-serve goal: images in → Claude asks questions → factory-ready pack. House rules: docs/DIGITIZING_PRINCIPLES.md.

## Layout
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
