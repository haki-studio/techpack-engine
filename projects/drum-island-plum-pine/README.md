# Drum Island jacket — plum + pine (HK-JK-DRUM-PP)

12 oz duck work jacket, Drum Island fit (XS–3XL), corduroy collar, YKK #5 brass zip, rib hem + cuffs.
Embroidery: 01 back scene (wraps onto the right sleeve), 02R/02L chest branch split at the zip, 03 chest pine,
04 lower-front bamboo.

Build order (from this folder, after `source ../../scripts/env.sh projects/drum-island-plum-pine`):
1. `flat2.py` / `flatf.py` — compose back + front art (scene code: `back2.py`, `front.py`) → `back2_vis.pkl`, `front_vis.pkl`
2. `qa2.py` — region width QA
3. `back_size.py <sizes>` — per-size back + sleeve art (wrap re-clipped per size)
4. `build_dst3.py A|B|C <pieces> nosplit` — graded front stitch files; `build_size.py <size>` — back + sleeve + splits
5. `spec2.py`, `run_front.py 02 03 04` — element specs; `pattern_out.py qa dxf pdf` — pattern
6. `build_all.py` — embroidery pack + garment pack merged; `finish2.py` + `shrink.py` — package

`legacy/` holds the v1/v2 scripts for reference (superseded).
Inputs: `inputs/flat.png` (mockup), `ref1/2.png` (motif references), `emb_boxes.json`, `wrap_marks.json`.
