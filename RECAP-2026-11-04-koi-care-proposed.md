# RECAP 2026-11-04 — Koi care label: proposed 100 % cotton (mission standard-labels)

## What / why
- Lead ruling 2026-11-04 (lead-eng-standard-labels; founder moved the fibre question to the lead on 2026-10-29): the Koi shell
  "washed navy 12 oz duck" is cotton duck, so its care label = Haki standard **100 % cotton**, shown **amber**
  "[proposed — confirm fibre: 100 % cotton]" (`fibre_confirmed=False`), same treatment as the six jackets
  (forestball / drum-island `SHELL_MAT = "... 100% cotton duck canvas ..."`). Not confirmed, not MISSING.
- `garment.py` `ZB.SHELL_MAT = "washed navy 12 oz 100% cotton duck"`; cover KEY SPECS + T8 Q3 read it; `pack.py` Q3 and the
  `rfq.py` shell swatch say 100 % cotton [proposed]. No engine change: `labelsheet` defaults already give amber.
- RFQ keeps asking the factory for every fibre % (Q1). Wording changed from "care label held / MISSING state" to
  "proposed 100 % cotton, pending your fibre %; if it differs we send the matching artwork". Internal TBD line updated.

## Verification
- `tests/test_koi_care_label.py` (3 tests): red 3/3 with origin/main Koi files, green 3/3 on the branch. The amber-vs-green
  assertion was checked to fail if `fibre_confirmed=True`.
- Rebuild: copied the Rev F build state (art pkl, dst json, scene, out/) from `~/te-koi-rfq` (same pack scripts as main),
  re-ran pack.py, garment.py, finish.py, rfq.py only (stitch files unchanged).

## Open / next
- When the factory answers Q1: if 100 % cotton, set `fibre_confirmed=True` path (green); otherwise change SHELL_MAT and the
  label swaps (a non-standard fibre goes back to MISSING until a matching Haki care label exists).

## Bug found + fixed (pre-existing)
- `finish.py` picked the garment pages with `glob(".../GARMENT_*.pdf")[0]`; with Rev D/E/F all in out/, filesystem order
  gave **Rev E** garment pages inside the delivered "Rev F internal pack" (its cover read "garment Rev E / embroidery Rev E").
  Now it opens `GARMENT_{REV_GAR}`. Factory summary + full tech pack were unaffected (rfq.py builds them itself).

## Results
- Full suite: 724 passed, 2 failed (known konpeito_gates, git-ignored out/front_stars.json).
- Rebuild: DST stitch files sha-identical to Rev E; leak gate ok (0 hits in summary 17 pp + tech pack 31 pp).
  T6b labels page renders the 100 % cotton care label front + back, heading amber "[proposed — confirm fibre: 100 % cotton]".
  Factory zip labels/ now carries the 100-cotton care label files.
