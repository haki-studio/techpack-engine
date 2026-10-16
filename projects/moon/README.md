# Moon jacket (HK-JK-DRUM-MOON) — Drum Island pattern, washed navy, moon + power lines + clouds
Built by the /techpack builder. Inputs + brief in inputs/, outputs in out/ (git-ignored). Run everything with `./py.sh`.

1. `art_size.py XS S M L XL XXL 3XL graded` — scene.py (moon, clouds, pole, wires; licensed-figure box knocked out) per size + graded art
2. `emb_place.py` — clearances per size (keep-outs, wire wrap 8/8) -> out/results/clearances.json
3. `build_size.py <SIZE>` (01 back + splits, 03L/03R) · `build_grade.py A|B|C` (02R/02L, 04R/04L + sleeve splits) · `collect.py` (gates)
4. `pattern_moon.py qa dxf pdf` — pattern QA, DXF per size, 1:1 plot
5. `covers.py` · `moonspec.py 01 02 03 04` · `build_all.py` (G1–G5 + T1–T16 merged) · `finish.py` (shrink + zip)
Engine proposals: ENGINE_NOTES.md.
