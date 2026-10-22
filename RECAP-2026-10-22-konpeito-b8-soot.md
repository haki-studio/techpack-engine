# RECAP 2026-10-22 — Konpeito Rev B8 soot sprites (builder, mission konpeito-soot-sprites)

Founder: "the eyes all look crazy and cracked out; some limbs of the soot sprites are missing." Branch `konpeito-b8-soot`
(worktree ~/te-konpeito-soot), rebased on main after PR #53 merged.

## What changed and why
- **Art table** `projects/konpeito-jeans/inputs/soot_art.json`: the sprites are ~15 px on the mockup and the arms are 1-px
  lines, so nothing can trace them. Read by eye from 20x crops: candies held, visible limbs (23: arms to the candy where
  they show, legs), eye size 0.30 D × 0.38 D (mockup ~4-5 × 6 px on 15 px), tilt ≤ 20°, ONE gaze per sprite.
  `kjsootart.py` turns the typed reading (READ dict) into the json; certainty noted per sprite.
- **Gaze is an art rule, not a measurement**: pupil pixels on the mockup are ±0.5 px noise (two sprites read as cross-eyed).
  Rule: both pupils look at the candy held, up when arms are raised. PROPOSED in brief #22.
- **Arms hidden behind a candy held against the body are not sewn** (K02, K03, K04, K07, K08→S13), as on the mockup.
- `kjfront.soot_regions` draws from the table. Eye white = true zigzag satin 0.20 mm crossings + centre run. Dead end:
  a "rows + 0.2 mm connector" satin lost its connectors in the engine (min-stitch filter) and left gaps every ~1 mm.
- **Gate** `kjsoot.py` `art_gate`: limb count + each limb traced, pupils agree ≤ 0.35 mm, gaze vs table ≤ 0.35 mm,
  eye area ±15 %, satin crossing step ≤ 0.30 mm, no split. B8 9/9 PASS; shipped B7 0/9, every new check red on every
  sprite while the old checks still pass. Fixture: tests/fixtures/konpeito_b7 (shipped B7 07a/07b DST+PES, md5 = zip).
- Lead's nits: Q1 last column now "Revision it changed" with the rev per row (+ J6 row); brief main label 6.5 × 2 cm.

## State
- 07a 8,681 st / 149 trims / 27.0 min (B7 8,225 / 135 / 25.0); 07b 2,437 / 38 / 7.6 (B7 2,290 / 32 / 6.8).
- Pack Rev B8 built in out/ (26 pages). NOT copied to Desktop/TECH PACKS yet — only after reviewer APPROVE on the head sha.
- Compare page (reference | B8 | B7): https://claude.ai/artifact/TuAFBSukzJ6q79JWVh74L8
- Tests: 541 passed.

## Pending
- After APPROVE: copy RevB8 pdf+zip to Desktop/TECH PACKS/1 Konpeito jeans/, move B7 to older versions, update READ ME.
- Sew-out confirms limbs + gaze (Q-b). Proposed LESSONS row + engine art_table kind in ENGINE_NOTES 37/38.
