# KCOS hoodie — Rev I (founder defect 21 Oct: flat bits on the puff letters), 21 Oct 2026

## Why
Founder screenshot of FL M (EN badge): small satins at another angle at P, R, S, A, E. Coordinator diagnosis: gap fillers
and narrow stroke bits of PUFF glyphs fell under `PUFF_MIN_MM`, were classed FLAT and sewed after the foam was torn
(stops 7-8). Glyph / A14 gates could not see it (bits inside the outline).

## What changed
- `kcmotifs.puff_absorb`: in a puff glyph every gap filler, every narrow group touching a puff stroke and every narrow
  group < 8 mm sews PUFF in the stroke's stop; only a whole free stroke group >= 8 mm could stay flat (none exist now).
  M: JP 1, EN 8, CN 31 bits absorbed; 0 flat pieces left in any puff glyph.
- `kcmotifs.bridge_fillers`: first try (puff only) still left P's filler as a detached strip under the bowl (seen on the
  stitch zoom) -> each absorbed filler is widened 0.6 mm into the stroke it joins so core + rim are one shape.
- Gate `kcgates.flat_fragments` + `frag_gate.py` (in `build_all.py`): reads every written front DST (full + splits, all
  sizes). Red on Rev H FL M = exactly 8 (the founder's spots) + 28 on FR (CN + 宙); Rev I = 0 everywhere.
  `out/frag_gate_revH_M.json` is the red proof. 5 new tests in `tests/test_kcos_gates.py` (280 pass in the full suite).
- Star specks: `kcmotifs.speck_sliver` + `scene.speck_guard` -> sliver specks sew as the house dot (M: FR 1, CN ring 1,
  FL 3 incl. the 0.7 x 7.9 mm zigzag right of CLEAN; sleeves 0; back 0 because it copies the filtered front stars).
  First thresholds (narrow 1.2 / aspect 2.5 / inscribed disc) caught 31-46 good dots + concave sparkles: concave sparkles
  hold a small disc only, so the test uses the rotated box; final 1.0 / 3.0 / disc 1.0.
- Pages: G4 puff rows list absorbed bits, E05 lists the speck filter counts, T9 + README Rev I row. Rev I everywhere.
- Zoom sheets Rev H vs Rev I (dstzoom, same scale): out/zoom/ (every badge every size + each Rev H defect spot at M).

## Numbers (M, read back): FR 29,240 st / 273 trims / 14 stops (was 16), FL 27,576 / 222 / 6 (was 8), SR 2,756 / 97,
SL 2,771 / 97, BK 5,311 / 191. Max stitch 7.03. 10 threads. 27 pages, 4.4 MB; zip 30.5 MB. Desktop/keep-clean-RevI.

## Notes
- LESSONS rows B43 / A33 are written ready-to-paste in ENGINE_NOTES 30 (builders may not edit LESSONS.md).
- CN thin strokes (1.2-2.2 mm) now sew over the foam with their glyph; the thin-puff question to the factory (F1/F2) covers it.
