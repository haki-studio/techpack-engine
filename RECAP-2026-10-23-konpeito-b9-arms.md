# RECAP 2026-10-23 — Konpeito Rev B9: soot-sprite arms the right way up (builder, mission konpeito-soot-sprites)

Founder (23 Oct): "i think a lot of the arms are upside down of the soot sprites. like so. k9, 8 5, and 1 suffer from this."
Branch `konpeito-b9-arms` (worktree ~/te-konpeito-b9) = local merge of the two approved shas 1415c5a (B8 sprites, #58) +
640ea23 (factory summary, #57). GitHub is suspended: local commits only, no PR.

## What changed and why
- **Cause**: `kjsootart.py` rooted each holding arm on the UPPER side of the candy direction, so it left the top of the body
  (exit 49-72° above horizontal) and read as an antenna arching over to the candy. The mockup (founder's red line on K09):
  the arm leaves the side facing the candy at about eye height, runs out, then goes straight up to the candy's underside.
- **New rule** `kjsootart.holding_arm`: root on the body edge at 10° above horizontal on the candy's side (eye centres sit at
  y ≈ 0); level run out to 0.5 mm body-side of the candy centre line; rounded elbow (0.8 mm); straight up to 0.8 mm inside
  the candy's lower edge (the candy is sewn later, on top, so the end tucks under it). If the climb would be < 2.5 mm the
  root drops below the shoulder (K08 → -8°, K01→S02 → -1°), never below -30°.
- Regenerated `inputs/soot_art.json`: only the arm polylines changed. Eyes and legs byte-identical (asserted). Limb counts
  unchanged (K01 4, K05 4, K06 4, K08 3, K09 3; hidden arms behind body-held candies still not sewn).
- **K06** raised empty arms left as B8: they root at 52° (upper shoulder, not the top), rise without arching, and match the
  mockup's lines above the body (x ±5-7, y -8..-13 px). The root band is only checked on holding arms (no candy to face).
  Lead's call if the founder wants them from the side too.
- **Gate** `kjsoot.arm_shape` / `art_gate` (from the DST component the limb check matched): root elevation where the arm
  leaves the fur, side = toward the held candy, |elev| ≤ ROOT_BAND_DEG 35°; arch = highest arm point above the hand
  (pixel nearest the candy) ≤ ARCH_TOL 0.5 mm. 35° sits between B9's max |8|° and B8's min 49°.
  Sheet label gains "arms ok / UPSIDE DOWN"; `python3 kjsoot.py --b8` renders the red evidence.

## Red / green
| | K01 | K05 | K08 | K09 | others |
|---|---|---|---|---|---|
| B8 (shipped DST, B8 table) root ° | 67, 56 | 65, 63 | 49 (arch 0.55 mm) | 72 | pass |
| B9 root ° | 8, -1 | 8, 8 | -8 | 8 | pass |
- B8: arms red on exactly K01/K05/K08/K09; every older check still green on them. B9: 9/9 PASS.
- Mutation: band off → only K08 stays red (via the arch), so the band is what catches 3 of 4.
- Synthetic: drawn "J" passes, inverted "n" fails root + arch, far-side shoulder fails side.
- Tests: 557 passed (tests/). Fixtures: tests/fixtures/konpeito_b8 (07a/07b DST+PES md5 = B8 SAMPLE READY zip, + B8 table),
  tests/fixtures/konpeito_b9 (this build), tests/fixtures/konpeito_front_stars.json (copied into out/ when missing, so the
  konpeito tests run in a fresh worktree; B8 follow-up closed).
- 07a 8,680 st / 148 trims / 26.9 min; 07b 2,446 / 38 / 7.6 min (B8 8,681/149/27.0; 2,437/38/7.6).
- Compare (reference | B9 | B8): https://claude.ai/artifact/Rim7RdzHJ49aBuCuiksufk

## Pending
- Reviewer (lead runs it). Only after GO: build Rev B9 pack + kjfactory.py factory summary/reference zip (leak gate),
  TECH PACKS/1 swap (B8 → older versions, READ ME item 1), brief "Rev B9 assumptions", ENGINE_NOTES lesson
  "a limb count doesn't check direction".
- HOLD: konpeito-send-to-factory sends B9, not B8.
