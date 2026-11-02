# Pixel Sky sherpa fleece jacket (HK-FL-PIXSKY)
First fleece. Engineered jacquard sherpa (sky blue / cream clouds, optional black bird) + embroidered pixel sparkles.
Block: Drum Island + pile ease (`fleece.py`, PROPOSED). Full rebuild: `bash projects/pixel-sky-fleece/run_all.sh`.

| Step | Script | Output |
|---|---|---|
| pattern | `fleece.py`, `pattern_fl.py qa dxf pdf png` | out/pattern |
| mockup classes + details | `pixels.py`, `mockmap.py` | — |
| jacquard maps | `jacquard.py [sizes]` | out/jacquard (PNG/BMP per panel + size, stats) |
| embroidery art | `emb_art.py` | out/art (SVG per file, placements.json) |
| stitch files | `python3 -m digitize.run bench/run_E*.yaml --no-api` | out/stitch/E* |
| gates | `gates_fl.py`, `emb_place.py` | gates_fl.json, clearances.json |
| flats / compare / pack | `fflat.py`, `compare.py`, `pack.py`, `finish.py` | out/*.pdf, zip |
