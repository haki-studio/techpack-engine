# RECAP 2026-10-27/28 · KCOS pullover, Rev M from "Mockups 3" (lead-product-kcos-hoodie-pivot, session b2cf3b8a)

Nick approved the founder's "Mockups 3" (Desktop/HakiStop/Designs/Playtime/Keep Clean Our Space/Mockups 3.png) on 27 Oct.
Rev L (rule-based halving) is superseded and must NOT be sent. Rev M = stitch files + pack that match Mockups 3.

## Approach
- `mock3.py` (new): reads the star detector output (missions/kcos-hoodie-pivot/revm/stars.json, 225 blobs), drops badge /
  script / hood-V glint pixels, and maps every star to garment mm **by panel proportion** (body: HPS line → hem-rib seam,
  share of half width; pocket: trapezoid share; sleeves: along + across, front view = front half; hood: share from CB seam).
  The mockup is not to scale (its body is ~1.4x taller than wide; our Come Over block is about square), so one px→mm factor
  would have pushed stars off the pieces.
- `pv_art.py`: Rev M mode is now the only mode. Badges + script centred where Mockups 3 has them (badges still the Rev J
  art, translated only). Each mockup star → Rev J library unit of its kind (plus ≥ 6 px blob, else dot) at its size rank.
  Keep-out / split conflict → nudge ≤ 10 mm, else dropped and counted. Hoop cells cover only the art actually there.
  DENS_BY / random placement / zoned fallback removed.

## Gotchas
- Python env: `~/.venvs/techpack/bin/python`, `PYTHONPATH=<wt>/engine:<wt>`; copy art_M.pkl + inputs/fonts from ~/te-kcos-revl.
- Mockup star blobs include render glow: plus stars read ~8 mm, library plus units are 3.8-6.3 mm. Kept the library sizes.

## Numbers (size M, DST read-back) — c38457c
| | Rev L | Rev M |
|---|---|---|
| hoopings | 13 | 9 (FR 2, BK 2, PK 1, SR 1, SL 1, HR 1, HL 1) |
| stars | 535 | 155 (FR 32, BK 29, PK 12, SR 34, SL 33, HR 7, HL 8) |
| stitches / trims | 72,097 / 988 | 61,962 / 589 |
| machine min [engine est., internal] | ~196 | ~143 |
- 168 mockup stars mapped; 13 dropped (mostly on the body side seams, where the render's arm overlaps), 34 nudged (mean 7 mm).
- Plus share ~60% (mockup) vs Rev L ~40%.
- Planner: prefers the plan with fewer hoopings even if stars must be nudged (first try gave 11 hoopings with thin strips).

## Status
- TD pass (td-generalist → td-chair) then reviewer, then card kcos-pullover-revk-send-mandy → Rev M.

## 2026-10-29 (session 44eb2d3c): TD fixes + rebuild
- td-generalist M1-M10 recovered (prev session's subagent couldn't write); applied M1 (Q4 blocks-or-float, lists overhanging hoopings), M2 wording, M4 (JP→CN gap ≥25 mm), M5 (seam stars nudge ≤20 mm inward + drop cause), M6 sleeve front sign, M7/M8 Mandy questions.
- td-chair: SEND-WITH-FIXES; MF-1..3 + M9 applied in pv_pack (Q1 "we re-plan the back for your frame", Q5 adds SR-H1 sleeve swatch through the wash, Q3 adds price without hood hoopings, K5 rule matches Q4). MF-4 = cover message "answer Q1/4/5 before cutting".
- Rebuild M: 9 hoopings, 166 stars (FR35 BK32 PK13 SR35 SL35 HR7 HL9), 62,373 st / 592 trims, ~144 machine min [engine est.]. 11 seam stars recovered vs c38457c (155).
- Gotcha: pv_pack globs result_allover_*.json; stale per-piece result files from an older run override a new combined one. Moved the old ones to out/pv/M/stale-c38457c/.
- Gotcha: the low-memory reaper killed a background pv_pack; run it in the foreground after `heavy-jobs` = 0 (38 s).
- Founder open: star size (library 3.8-6.3 mm vs mockup reads ~1.5x) — look choice, not a blocker.
- Reviewer REQUEST-CHANGES d04a04e (K1: Q4 label overlap, Q6 into footer) → fixed → REVIEW: APPROVE 7104225.
- Shipped: TECH PACKS Rev M PDF + zip (Rev L → older versions); card kcos-revm-send-mandy filed. Branch not pushed (no GitHub access to techpack-engine from here).
