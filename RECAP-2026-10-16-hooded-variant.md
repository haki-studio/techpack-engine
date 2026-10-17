# RECAP 2026-10-16 — hooded variant of the Drum Island block

For: red-beast-hoodie, comet-city-hoodie, keep-clean-our-space-hoodie, koi-blossom-hoodie (Drum Island body, collar → hood).

## What was built
- `pattern.draft(size, variant="hooded", hood=None)`. Default variant unchanged: golden DXF hashes generated from
  unmodified main (`tests/dxf_golden.py`, timestamps blanked) and checked by `test_default_dxf_unchanged`.
- `engine/hood.py`: 3-panel hood. H01 side (pair), H02 centre panel, H03 facing side (pair) + H04 facing centre
  (traced off the hood), H05 sherpa side lining (pair) + H06 sherpa centre lining. Collar C01/C02/IC01 dropped.
- Self-fabric R01 HEM BAND / R02 CUFF (category `BAND`, shell duck, folded double).
- `pattern_out`: `VARIANT`/`HOOD` globals, `--hooded` CLI flag, emb_place optional (new projects have none),
  hood seam walks, `band_check`, `hood_checks`, `sew_simple`.
- `pattern._welt_ref()`: falls back to the Drum Island welt polygon when the project has no `front.WELT_L`.

## Decisions (not visible in the diff)
- **Woven band = seam 1:1** forces two body changes in the hooded variant only: sleeve opening = chart H (was
  1.25 × H for the rib), so sleeves taper more; side seams taper to ½ D at the hem (XS 15.5 mm, M 9.5, 3XL 0.5 per
  side seam). The founder said "same pieces"; this is the smallest change that keeps every chart POM in tolerance.
- Cuff band 6.0 cm (rib was 7.5), hem band 5.5 cm (= rib, so the block's hem seam and keep-outs don't move).
- Hood dims are all PROPOSED in `pattern.HOOD` (M: height 34, width 25.5, face opening 76, centre panel 10 cm;
  grade ±0.6 / ±0.4 / ±1.0 cm per size). `pattern.proposed("hooded")` = the open-questions table.
- Sherpa turn-of-cloth: centre seam moved in 3 mm at the crown, ramped to 0 at the neck (keeps neck = body neck).

## Verification
- `python3 -m pytest -q tests` → 72 passed. `pattern_out.py qa dxf pdf --hooded` in red-beast-hoodie → all pass,
  9 DXFs + 25-page 1:1 PDF.
- Red runs: default 0.01 mm change → golden test red; hooded with rib cuff ratio / no taper → chart test red
  (H 20.0–21.25, D 55.1–62.5); hood neck without the centre-panel share → walk red (579.5 vs 479.5); corner guard
  caught a real 95° first chord at the nape (fixed by dense sampling).

## Open / next
- Hooded embroidery keep-outs must come from the drafted pieces (LESSONS C8): side taper + narrower sleeve.
- If the founder sends boxy-hoodie hood files: put their numbers in `HOOD` (or a project override) and re-run QA.
- Hood keep-outs / embroidery on the hood: none yet.
