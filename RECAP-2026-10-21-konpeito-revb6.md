# RECAP 2026-10-21 — Konpeito jeans Rev B6 (founder answers J1–J5, PR #34)

## Decisions applied (founder 21 Oct)
| # | Answer | Effect |
|---|---|---|
| J1 | 05 moved 9 mm inward = OK | "move CONFIRMED" on T8 / G6 |
| J2 | patch field straight 0° tatami | no art change (FIELD already 0°) |
| J3 | hammer loop off = confirmed | PROPOSED dropped on T4 / T6 |
| J4 | DROP the 3 clipped side-seam konpeito | `kjfront.product_map` + `EXCLUDE_CLIPPED=True`; trace still detects them (red X on C5); map = 14, renumbered S01–S14 |
| J5 | KEEP the soot sprites (licence risk accepted by founder) | 9 sprites traced (`trace_soot`: eye pairs) + digitised (`soot_regions`): tatami body, prebuilt radial fur, triple-run legs, satin eyes, knot pupils; new thread Soot black #151414 |

## Numbers (DST read-back)
- 07a 8,225 st / 135 trims / 25.0 min; 07b 2,290 / 32 / 6.8 min; 8 threads each.
- Per garment (all files, 07 now included): 42,332 st · 489 trims · 108.9 machine-min. 01–06 unchanged.
- Gates: all konpeito A14 + position pass (14 front); sprite gate (kjsoot.py) 9/9; tests 284 passed.
- Pack 26 pages (new C7 soot compare, Q1 founder decisions), PDF 8.1 MB; Desktop/konpeito-RevB6.

## Still open
- Size run 26–40 incl. half-way 29/31/33 (unanswered).
- Soot-sprite drawing details (uniform Ø 14.2, fuzz 0.2–1.1, legs) PROPOSED — confirm on sew-out.
- ENGINE_NOTES 34–36 (A7 override wording, clipped default, fuzzy-body primitive) for the coordinator.
- Loop-label question removed (obsolete since B2: HI centrefold label).
