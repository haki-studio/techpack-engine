# RECAP 2026-10-20 — Keep Clean Our Space hoodie, Rev D (founder answers to the 7 G4 questions)

## What changed and why
| Founder answer | Done |
|---|---|
| 1 back + hood = artwork to follow | G1/T1/T8/E05 say `[MISSING]` (not "plain"); still an open question |
| 2 puff on all signs | CN text + KR oval ring + JP dot now puff; rule: stroke < 2.5 mm stays flat, glyph puffs only if >= 50 % of its stroke length qualifies; table on G4 with measured widths |
| 3 12-colour plan / haze | unchanged; haze stays open |
| 4 CN dots puff | already puff (Rev C) |
| 5 污 | `kccore.TEXT["03"] = 不要世界污染`, all labels |
| 6 KR approved | labels say approved |
| 7 no extra text | closed |
| teammate (founder) | F1: no chenille, no quote basis / price asks (project filter, ENGINE_NOTES 23) |

## Decisions (not in the code diff)
- Puff limit 2.5 mm = the project limit since Rev B (JP/EN puffed 2.4-3.0 strokes in Rev C); house.yaml says 3.0, so strokes 2.5-3.0 are PROPOSED and asked on F2 for the strike-off.
- CN font weight 600 -> 800: at 600 only 11 % of stroke length reached 3.0 mm; the mockup CN strokes look as heavy. Glyph gate passes all sizes at 800.
- CN text no lighter rim (mockup CN letters show none) -> no new thread; FR stays 12.
- KR text stays flat (median 1.4 mm). JP 1 bar (2.2) + 4-point sparkle (tapered) flat.
- Flat strokes inside a puff glyph sew after the foam is torn ("top" stops).

## State
- 112 stitch files, prod_gates FAILS none, glyph gate none, A14 blocking 0. M: FR 59,273 st / 542 trims (12 colours), FL 47,730 / 385, SR 6,735 / 204, SL 6,944 / 200.
- 25-page merged PDF, ~4 MB. Copied to C:/Users/devin/Desktop/keep-clean-RevD/.

## Open
- back view (founder), star haze (founder), puff 2.5-3.0 strokes + foam (factory strike-off).
