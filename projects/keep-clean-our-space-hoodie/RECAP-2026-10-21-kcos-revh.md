# KCOS hoodie — Rev H (founder answers to the 4 PR #38 questions), 21 Oct 2026

## Why
Founder answered the 4 open items on PR #38: (1) back = embroidered stars only, front star style, hood plain;
(2) drop the stipple glow halo + the star haze entirely; (3) keep puff on the 2.5–3.0 mm strokes, ask Mandy on F1/F2;
(4) keep CN weight 800.

## What changed
- New piece **BK** (pattern B01), element **06 back stars** (`back.py` keep-outs: neck 10, shoulders / armholes / sides 15,
  hem 10). Layout seeded from the front field logic in `scene.py` (density 8.0 / dm², gap 3.3 mm = fronts' p10 NN, each back
  star a copy of a front field star; 248 stars at M) — PROPOSED. `art_size.place_back` grades positions by the back panel.
- `kccore.GLOW = False`: no stipple bands (01/02/03) and no haze under sparkles. Glow green + Star haze removed from the
  thread list (10 threads); hexes kept registered (`LEGACY_PAL`) so `tests/test_kcos_gates.py` fixtures still write PES.
- Pages: E06 back page, S3 stop table, back views on G1 / G2 / T1, F1 (e) + F2 §7 puff question for Mandy, G4 / T8 questions
  replaced, T7 includes BK clearances, T9 Rev H row; compare_06_back.png (front field style vs back DST, same scale).
- Stitch counts dropped a lot with the glow gone (FR 59k → 29k, FL 48k → 27k at M); see PR comment for the numbers.

## Open
- Back layout (PROPOSED: confirm or send a back view). Factory: thin puff strokes on the strike-off.
- Noted, not changed: two 43–51 mm² traced blobs at the FRONT hem corners (FR92, FL69) look like hem-corner glints in the
  render rather than stars; they were already in Rev G; excluded from the back library. Worth a reviewer look.
