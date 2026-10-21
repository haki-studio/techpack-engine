# RECAP 2026-10-21 — engine: pro reference profiler (branch engine-pro-profile)

## What / why
Founder question: Castle full back extrapolates to ~890k stitches (~310 st/cm²), "3× a fill layer" — normal or not, and
is the extra layering or detail? Built `engine/proprofile.py`: reads stitch files, segments runs into rows, links
antiparallel rows into hatch objects (satin = ~1 stitch/row, fill = several), the rest is run; open/low-density objects
under a later dense object of the same block = underlay. Coverage raster 0.5 mm, depth = objects per cell. Exact
identity `st/cm² = 100·D·ρ/L` splits any rate into layering × density / stitch length.

## Inputs
- Pro = ONLY 10 allow-listed John Deer designs (PRO_ALLOW), read from PRO_REF_DIR; Law.DST + Chopper Jacket (founder's
  amateur files) never read (test pins it). Licensed: no files/renders committed; JSON of numbers only.
- Ours: Castle crop DST sha 1963d24fc2d3d862 (HANDOFF "crop on main"; copied from worktree agent-a60653016b7ae2fe0 into
  this worktree's git-ignored out/), Castle Rev B full back (main checkout out/), KCOS FR M, Wave FR M, Konpeito coin.

## Findings (docs/PRO_REFERENCE.md has the full table)
- Pro 366–512 st/cm² covered (median 483); ours 227–348 → all BELOW pro p10.
- Crop 289 = D 2.66 × ρ 2.02 / L 1.85; pro 483 = 3.57 × 2.80 / 2.10. Ratio to own single fill layer: pro 2.7×, crop 2.6×.
- Pro fills 0.20–0.25 mm rows (!), satin same-side ~0.46, last colour block satin/run in 10/10, dense 3+ deep on 37 %.
- Old 250–350k back budget (~100 st/cm²) is below a single pro fill layer (178 st/cm²).

## Classifier dead ends / fixes (caught on renders)
- Bean on a curve linked into a 0.1–0.2 mm "fill" → enclosed-loop-area retrace test (point-coincidence test also
  rejected radial fans, abandoned).
- dst2 lattice underlay (2 mm side-steps) and radial fans read as runs → side-step connectors in chain building.
- Overlap band widths are raster-limited (< 1 mm reads 1.0) — indicative only.

## State
- Tests: tests/test_proprofile.py 11 tests, each proven red by mutation/broken input (scratch prove_red.py); full suite
  287 passed.
- No gates or engine behaviour changed. Proposals ranked in PRO_REFERENCE.md (PROPOSED).

## Next
- Founder decisions on proposals 1–3 (rate-based budget, trims gate 25→50, rule 6 re-based).
- Get large-format pro files (jacket backs) — biggest gap in the reference.
- Wire `pro_reference.json` into bench/gates once decided.

## Fix round 1 (review CHANGES, PR #35)
- Wording: "consistent with small-design pro practice; unmeasured at jacket scale"; dropped the 1.0–1.35M back figure.
- LESSONS row numbered E12 (next free on origin/main) and marked PROVISIONAL.
- Proposal 1 restated: report D/ρ/L per file, flag outside pro p10–p90 in EITHER direction as review; over-dense limit at
  jacket scale is unknown (the old "> 512" flag caught nothing of ours).
- Density: row spacing ~2x ours, thread per layer area 1.4x (2.80 vs 2.02).
- Native vs resized: every pro PES header names `<code>_M.EMB` (Wilcom object design at size M) → stitches generated at
  that size, not a scaled stitch file; whether 0.2 mm is deliberate or Wilcom size-dependent auto-density is unknown
  (no EMB). `pes_source()` + `source_design` in the JSON.
- New tests: 0.2 mm tatami reads 0.20 mm and ~2.2x thread of 0.45; pes_source. Overlap rows dropped from the doc table
  (grid limit ~1 mm), kept in JSON.
