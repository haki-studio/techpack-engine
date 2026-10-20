# RECAP 2026-10-20 — Keep Clean Our Space hoodie, Rev C (branch kcos-revc)

## Why Rev C
- Founder 2026-10-20: KCOS is top priority; finish Rev B's "final build + page check" as a deliverable Rev C.
- Rev B (19 Oct 20:41) was built from DSTs written at 20:13, but the art changed again at 20:55 (sparkle
  traced-silhouette fallback); the last rebuild was killed by the token-cost pause. Rev B therefore shipped one failing
  A14 row (FR field star, IoU 0.70) and DSTs that did not match the committed art. Rev C rebuilds everything.
- Factory answered 19 Oct (factory.json): frames 300 × 300 + 400 × 450, 12 colours, puff yes. Rev B splits were for the
  assumed 360 × 360.

## What changed (source)
- `kccore.py`: Rev C / 20 Oct; `CUT_KEEP_MM = 1.0` (house rule 6); make_pattern patch: flat stops cannot hide travel
  under the later puff stops (foam mask 0.5 mm inside the puff edge).
- `art_size.py`: `knock_under_puff` cuts flat work sewn before the foam (the glow stipple, `nok`) out of the puff
  footprint, keeping the 1 mm edge band (runs end 0.6 mm inside it).
- `kcstitch.py`: `foam_gates` on every written DST (puff stops only puff, nothing flat after them, base_under_puff = 0).
  Red on the Rev B FR M file (110 flat needle points inside the foam), green on Rev C.
- `prod_gates.py` (new, run by build_all): every file, every size: max stitch, ≤ 12 colours (PES), section fits the
  400 × 450 frame, foam gates, keep-outs. Exits 1 on any failure.
- Docs: G4 rewritten (7 founder questions amber), F1 "5b hoopings on your frames" + "6 puff" (puff confirmed), S1 foam
  check lines, G5 foam note, cover + README wording, T9 Rev C row, T8 pointer to G4; Rev B WIP patch applied (sleeve flat
  front half, CJK outlines, thread estimates flagged, same-card-code warning).
- Founder ruling (20 Oct): the garment mockup governs; reference.png only for the text wording. Checked: no close-ups
  exist and nothing traces or grades from reference.png (only shown on compare sheets / E pages).

- Page check (D1) found straight glow-green lines across the JP halo: the stipple walk bridged long hops with
  straight stitches (13 chains >= 15 mm on Rev B FR M, longest 57.5 mm) and travel hid inside unsewn sheer runs.
  Fix: `stipple_band(max_hop=3)` starts a new run; sheer runs never hide travel; `prod_gates.straight_chains` gate
  (red on Rev B, green on all Rev C files). Cost: FR M 301 -> 500 trims, FL 229 -> 351, sleeves ~130 -> ~195 (reported).
- R1 / E pages: HAZE is a stipple run, not open tatami (text was wrong since Rev B).

## Final numbers (size M, read from the DSTs)
| Piece | Stitches | Trims | Colours | Max st | Hoopings (400x450) | Foam stop | Flat pts in foam |
|---|---|---|---|---|---|---|---|
| FR | 58,974 | 524 | 12 | 7.07 | 2 | ok (STOP before stop 7) | 0 |
| FL | 46,764 | 378 | 8 | 7.00 | 2 | ok (STOP before stop 6) | 0 |
| SR | 6,735 | 204 | 2 | 3.83 | 4 | n/a | n/a |
| SL | 6,944 | 200 | 2 | 4.22 | 4 | n/a | n/a |
All 112 files (7 sizes x 4 pieces + splits) pass prod_gates; A14/A15 blocking 0; keep-outs pass every size; pattern QA pass.

## Review of PR #20 (CHANGES) — fixed
- 界 stitched without the centre vertical of 田 / 要 counters closed: root cause in `kclettering.glyph` (union of outer
  contours minus union of holes is wrong for overlapping contours of a variable-font instance) -> `nonzero()` fill rule.
  New per-glyph gate `glyph_gate.py` (font glyph vs DST read-back: IoU >= 0.80, no dropped piece > 3 mm2, counters
  matched): red on the old files (界 0/4 counters, 要 2/5, KR '!' 0.61, EN A 6.3 mm2 missing), green on all 7 sizes.
  Needed two more fixes to get there: gap-filler columns for glyph parts no stroke covers (KR '!' dot, A apex) and exact
  travel (dst2.ExactCover, B27: a 1.6 mm float joined '!' to its dot). Cost: FR M 501 -> 524 trims, FL 357 -> 378.
- One foam procedure (`kcdoc.foam_steps`): STOP before the first puff stop, tear after the last; per full file and per
  split, printed on S1 (STOP + TEAR rows), F2 and the README (every size); G3 / G5 wording aligned.
- Tests `tests/test_kcos_gates.py` (6, red-then-green) for foam_gates, foam mask, straight_chains, glyph_check; gate code
  moved to `kcgates.py` (pure). LESSONS A32 / B40 / B41 / D5 (main ended at A31 / B39 / D4 when merged in).
- Also: compare sheets say Rev C, compare_03 zooms fixed, T1 lists F2, F1 chenille section dropped (chenille=False), Q5
  shown large (G4), G4 sizes from the DST, E05 star count reconciled (187; the 190 predates the glint exclusion), JP text
  rows on a stated text tier (IoU >= 0.40, size 0.55-1.45) instead of an exemption, the 'moved' JP mint row was a real miss
  (a 2.6 mm mint dot right of い) -> traced and stitched, F2 asks about 2 sleeve hoopings turned 90 deg.
- Full pytest 255 passed; prod_gates 112 files OK; every printed stitch/trim count re-diffed vs read-back (112 files).
- Copied PDF + zip + compare_front_M to C:\Users\devin\Desktop\keep-clean-RevC\.

## Decisions
- Fronts do NOT fit 400 × 450 in one hooping (M 267 × 512): 2 hoopings each; full single-hooping files ship too and F1
  asks which frame takes a whole front (factory confirmed 340 × 505 without naming the frame).
- Sleeves (M 435 × 558) need 2 × 2 on 400 × 450 (width 435 > 384 usable).

## Open
- 7 founder questions (STATUS.json) — built as proposed, printed amber on G4.
- ENGINE_NOTES 20 (foam travel mask → engine make_pattern), 21 (F1 multi-hooping list when frames are confirmed).
- Independent review of Rev C.
