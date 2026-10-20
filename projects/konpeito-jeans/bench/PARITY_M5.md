# M5 parity: parts engine (founder SVG) vs delivered Konpeito Rev A

Same gates on both files (digitize.svgrun.gate_file). Exposed = stitches >= 0.5 mm with > 0.3 mm on bare fabric (outside own stop art + 0.25 mm and not under a later stop). Centreline: mean skeleton distance <= 0.5 mm and width within 20 %. Motifs: IoU >= 0.70 + extents >= 80 % per SVG shape (house-min dots counted as pass).

| element | file | stitches | trims | stops | threads | max st | min | centreline | worst cl mm | motifs | min IoU | house-min | exposed | uncovered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| wb | delivered Rev A | 14918 | 139 | 11 | 8 | 7.0 | 34.5 | 6/6 | 0.14 | 56/76 | 0.61 | 2 | 7 | 0 |
| wb | engine M5 | 15069 | 161 | 10 | 8 | 7.0 | 36.8 | 6/6 | 0.13 | 76/76 | 0.74 | 1 | 0 | 0 |
| coin | delivered Rev A | 10540 | 82 | 12 | 9 | 6.9 | 23.0 | 1/1 | 0.13 | 26/46 | 0.61 | 0 | 30 | 0 |
| coin | engine M5 | 10525 | 84 | 11 | 9 | 6.9 | 23.1 | 1/1 | 0.13 | 46/46 | 0.76 | 0 | 0 | 0 |
| spill | delivered Rev A | 3651 | 60 | 9 | 7 | 5.83 | 11.4 | 0/0 | None | 9/9 | 0.83 | 0 | 0 | 0 |
| spill | engine M5 | 3609 | 58 | 7 | 7 | 5.9 | 11.0 | 0/0 | None | 9/9 | 0.83 | 0 | 0 | 0 |
| starP | delivered Rev A | 281 | 1 | 2 | 2 | 5.41 | 0.5 | 0/0 | None | 2/2 | 0.82 | 0 | 0 | 0 |
| starP | engine M5 | 281 | 1 | 2 | 2 | 5.41 | 0.5 | 0/0 | None | 2/2 | 0.82 | 0 | 0 | 0 |
| starY | delivered Rev A | 281 | 1 | 2 | 2 | 5.39 | 0.5 | 0/0 | None | 2/2 | 0.82 | 0 | 0 | 0 |
| starY | engine M5 | 281 | 1 | 2 | 2 | 5.39 | 0.5 | 0/0 | None | 2/2 | 0.82 | 0 | 0 | 0 |

## Centreline per string

| element | string | delivered mean / width ratio | engine mean / width ratio |
|---|---|---|---|
| wb | 05_frame_RED 40wt | 0.05 / 0.9 PASS | 0.05 / 0.9 PASS |
| wb | 10_hearts_PINK 40wt | 0.1 / 0.93 PASS | 0.09 / 0.93 PASS |
| wb | 12_face_BLACK 60wt | 0.07 / 1.14 PASS | 0.07 / 1.14 PASS |
| wb | 13_lettering_BLACK 60wt | 0.14 / 1.0 PASS | 0.13 / 1.0 PASS |
| wb | 14_name_chihiro_RED 40wt | 0.09 / 1.04 PASS | 0.09 / 1.06 PASS |
| wb | 15_signature_risa_BLUE 40wt | 0.08 / 0.92 PASS | 0.09 / 0.94 PASS |
| coin | 04_lettering_RED 40wt | 0.13 / 0.91 PASS | 0.13 / 0.9 PASS |

## Exposed stitches in the delivered files (same gate)

- wb: 7: stop 7 at (56.5, 21.6) 0.33 mm, stop 7 at (64.7, 19.5) 0.34 mm, stop 9 at (20.6, 36.4) 0.38 mm, stop 9 at (34.7, 28.7) 0.36 mm, stop 9 at (35.5, 30.3) 0.39 mm, stop 9 at (46.2, 22.9) 0.32 mm, stop 9 at (41.2, 20.7) 0.38 mm
- coin: 30: stop 4 at (24.1, 39.2) 0.33 mm, stop 4 at (23.6, 39.2) 0.34 mm, stop 4 at (18.6, 41.9) 0.32 mm, stop 4 at (18.4, 39.7) 0.32 mm, stop 4 at (13.4, 38.4) 0.31 mm, stop 4 at (14.4, 38.5) 0.33 mm, stop 4 at (13.9, 32.2) 0.33 mm, stop 4 at (14.2, 32.0) 0.35 mm
- spill: 0
- starP: 0
- starY: 0
