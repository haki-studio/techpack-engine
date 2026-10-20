# ENGINE_NOTES — pixel-sky-fleece (proposals for the coordinator; engine/ untouched)

## 1. svgrun: `gates.exposed` override crashes
Problem: `gate_file` builds `dict(halo=0.25, min_mm=0.5, min_ex=0.3, **G.get("exposed", {}))`; any run.yaml that sets
`gates: {exposed: {halo: ...}}` raises `TypeError: dict() got multiple values for keyword argument 'halo'`.
Fix: `EX = {**dict(halo=0.25, min_mm=0.5, min_ex=0.3), **G.get("exposed", {})}`.
Check: unit test that a run with `gates.exposed.halo: 0.35` reaches the exposed-stitch gate with halo 0.35.

## 2. Exposed-stitch halo must follow the fill's pull compensation
Problem: on sherpa we sew tatami with pull comp 0.30 (pile pulls more than duck). The exposed-stitch gate's fixed halo
0.25 then flags the pull-comp overshoot at staircase (pixel-art) corners as "exposed" (E2: 3 stitches 0.35-0.44 mm,
E1B: 1 stitch 0.53 mm). Proven: the same E2 art at pull 0.20 gives 0 exposed stitches.
Fix: halo = max(0.25, part pull_comp + 0.05) per stop (read from the plan's StitchSpec), not a constant.
Check: red-then-green test — a 1 mm float between two motifs stays red at pull 0.30; a pull-comp corner at 0.30 is green.
Project workaround: `gates_fl.py` runs `qa.exposed_stitches(halo=0.35)` on every DST and reports both numbers.

## 3. New product type: engineered jacquard sherpa
Problem: no engine support for knitted / jacquard panels (cell maps per pattern piece and size); built in project code
(`jacquard.py`: trace on a fixed cell grid anchored at CF / hem, detail fill, reflection for hidden areas, indexed PNG/BMP
per panel + size). Proposal: move the grid tracer + panel rasteriser into `engine/jacquard.py` once a mill confirms the
file format (BMP indexed, 1 px = 1 cell, palette = yarn colours) — ask in F1.
Check: test that a panel map's cell count == knit area / cell² ± edge cells, and the hem row is anchored on every size.

## 4. Derived blocks by chart deltas
Problem: `fleece.py` swaps `drum.POM_CM` inside a context manager to add pile ease, because `pattern.draft` reads the
module-level chart. Proposal: `pattern.draft(size, chart=None, rib=None)` taking an explicit chart dict + rib heights.
Check: `test_fleece_inherits_jacket_shape` (same seam walks, chart deltas only).
