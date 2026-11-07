# RECAP 2026-11-07 — CI tests workflow (mission standard-labels, builder)

## What
- `.github/workflows/tests.yml`: runs `python -m pytest -q tests` on every pull_request and on push to main
  (Python 3.10 = the local venv's version, `requirements.txt` + system `libcairo2`, 45 min timeout, read-only token).
  Purpose: give pr-gate a real check to read on techpack-engine PRs.
- Fixed the 2 known red tests in `tests/test_konpeito_gates.py` (seen in the #63/#64 reviews):
  `test_soot_sprites_traced_and_gated` and `test_soot_art_gates_red_on_b7_green_on_b8`.

## Why they were red
Their "green on the shipped build" legs called `kjsoot.run()` with its default `dst_dir="out/stitch"`. `out/` is
git-ignored build output, so on any fresh clone (and CI) the folder does not exist → `FileNotFoundError`. They only
ever passed on a machine where someone had built konpeito locally. The shipped Rev B9 DSTs are already committed in
`tests/fixtures/konpeito_b9` (and `test_soot_arms_red_on_b8_green_on_b9` already uses them), so both tests now read
that fixture. B8 is not the green leg any more: under the B9 arm check B8 fails K01/K05/K08/K09 by design.
Real fix, not xfail. Every assertion is unchanged (incl. the K01 limbs_dst==4 / K05 gaze mutations, which hold on B9).

## State
- Local: 721 passed + 2 failed before; konpeito file 11/11 after. Full suite ~11.5 min locally.
- Prove-the-guard: canary `tests/test_ci_canary.py` (assert 1+1==3) at 0d3ccc3 → run 42414893141 FAILED, log names
  the canary. Same run exposed a real CI-env gap: 6 test_labelsheet tests need `pdftoppm` → added `poppler-utils`.
  Canary reverted + poppler at de401e3 → run 42415491809 SUCCESS, 723 passed in 5m38s on GitHub (11.5 min locally).

## Caveats
- `requirements.txt` is unpinned; CI resolves latest compatible versions, local venv may differ (numpy 2.2.6,
  shapely 2.1.2, pyembroidery 1.5.1). If CI and local disagree, pin.
- The konpeito file alone takes ~11 min (kjsoot.run renders full sections); a candidate for speeding up later.
