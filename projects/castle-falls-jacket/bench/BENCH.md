# Benchmark - Castle Falls BK size M crop (ENGINE_PLAN M0)

Every engine milestone is scored on the same crop with the same gates (`engine/digitize/bench.py`). Rows are appended,
never edited. Config: `bench.json` (crop, targets), registration: `registration.json` (config as data).

**Crop.** ENGINE_PLAN asked for x -180...+20, y 370...570 mm. Its bottom 5 mm fell outside the back_left close-up's
registered region (feather weight down to 0.25 against the 0.6 threshold), so the crop is **x -180...+20, y 365...565 mm**
(shifted 5 mm up; min weight 0.647). Garment mm on the BK piece: x from CB (+ = wearer's right), y from the CB neck seam.

**Reference quality.** The reference is sampled on a 12 ppm GRID; that is not a detail guarantee. The real source
detail is ~2.6 px/mm in this crop (register.reference `source_ppm`: the back_left close-up), and direction_match masks
8 mm tiles whose close-up weight is < 0.6 (`masked` in the rows; 0 here, the crop lies inside the close-up).

**Gates** (qa.py): direction_match on the visible layer at 12 ppm (>= 85 % OK, <= 5 % chaotic), angle_coherence per
part (needs part ids; a DST has none), density_map (areas over 7 mm/mm2), trims_per_area (<= 25 / 100 cm2 of covered
area), satin_shape (0 blobs, nothing > 7 mm), stack_map (<= 2 layers), colours (<= 12 threads, red and gold present).
"Dir all" = the old score over every stitch including underlay, for comparison only.

## Baseline (19 Oct 2026): the shipped Rev B DST fails every gate, as intended

DST `projects/castle-falls-jacket/out/01_back-scene/M/HAKI_CSFL_01_back-scene_BK_M.dst` (sha256 b8dd2fcf852983f3,
build output not in the repo, read from the main checkout), origin (-0.009, 330.3) mm from `result_BK.json`.
Product status unchanged.

![baseline panel](panel_2026-10-19_baseline--shipped-rev-b-dst.png)

| gate | baseline | target | |
|---|---|---|---|
| direction_match, visible layer, 12 ppm, 625 tiles of 8 mm | 11.7 % OK, 77.9 % chaotic, 65 off-grain | >= 85 % OK, <= 5 % chaotic | FAIL |
| (old score: every stitch incl. underlay) | 2.4 % OK, 97.3 % chaotic | info only | |
| angle_coherence | 535 constructed regions (WALL / ROOF / TMB) in the crop, 0 with a part id, 479 with an "auto" angle -> raises | per part, declared | FAIL |
| density_map (all stitches, 1 mm grid) | mean 5.67, p95 10.45 mm/mm2; 194 areas (66.2 cm2) over 7.0 | 0 areas | FAIL |
| trims_per_area (DST read-back) | 452 trims on 399.8 cm2 of covered area = 113.1 per 100 cm2 of covered area | <= 25 per 100 cm2 covered | FAIL |
| satin_shape | 1925 satin columns: 1159 blobs (aspect < 2.5), 31 under 1 mm, 0 over 7 mm; 319 radial fans | 0 blobs | FAIL |
| stack_map | up to 6 layers; 19.97 cm2 (5.1 % of covered cells) over 2 | <= 2 | FAIL |
| colours | 12 threads (24 stops in the crop); no red, no gold (merged into rose / cream at build) | <= 12, red + gold | FAIL |

Reading it: the direction failure is mostly chaos (fragments sewn at their own angles, the A16 symptom), not wrong
grain. Judging only the visible layer raised the score from 2.4 % to 11.7 %, so underlay was hiding part of the picture,
but most of the failure is real. The angle_coherence FAIL is plumbing, not a measurement: the Rev B scene carries no
part ids, so the gate raises before it measures anything (M1 runs carry part ids from the plan into the DST labels). Fans are counted, not failed: rule 4 allows radials on florets, and telling a floret
from a window fan needs the part map (M1+). stack_map counts sewn runs; objects joined by hidden travel share a run, so
it can only under-count.

## M1 skeleton (20 Oct 2026): parts, declared angles, falls as cords

`PYTHONPATH=engine python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api`
(zones: `zones_BK.json`, hand-authored windows + tone families; run config: `run_bk_crop.yaml`). The DST is a build
output in `out/digitize/BK_M_crop/` (not in the repo).

![M1 panel](panel_2026-10-20_m1-skeleton--sky---falls-splitters--zone.png)

| check | baseline | M1 | target | |
|---|---|---|---|---|
| direction, visible layer (625 tiles, 0 masked) | 11.7 % OK, 77.9 % chaotic | 89.0 % OK, 7.0 % chaotic | >= 85 %, <= 5 % | OK / FAIL |
| ... fall_cord tiles | - | 98.4 % (61 tiles) | >= 85 % | OK |
| ... sky_band tiles | - | 100 % (2 tiles: the crop has almost no sky) | >= 85 % | OK, thin evidence |
| ... zone_stub tiles / pool tiles | - | 88.0 % (552) / 75.0 % (8) | (stubs: M2/M3) | info |
| parts | none (535 unlabelled constructed regions) | 381: 14 fall cords, 2 sky bands, 4 pools, 361 stubs; 18.4 % under 20 mm2 | <= 400, < 25 % | OK |
| angles | 479 "auto", random fills | 0 undeclared, 0 random: 20 by rule, 361 field-mean | 0 | OK |
| angle_coherence (by plan part id) | raises (no ids) | 109 fails, all stubs/pool: 58 buried (< 12 visible stitches), 51 spread > 10 deg | 0 | FAIL |
| satin shape | 1159 blobs, 319 fans | 0 satins, 0 blobs, 0 fans | 0 blobs | OK |
| density | 194 areas > 7 | 78 areas (13.8 cm2), mean 4.43 | 0 | FAIL |
| stack | max 6, 19.97 cm2 > 2 | max 5, 8.7 cm2 > 2 (where 3+ zones meet) | <= 2 | FAIL |
| trims per 100 cm2 of covered area | 113.1 (452) | 33.0 (132) | <= 25 | FAIL |
| colours | 12, no red, no gold | 12, red (24 parts) and gold (13 parts) sewn | <= 12, red + gold | OK |
| stitches in crop / stops | 150,250 / 24 | 84,090 / 17 (file 91,317 incl. travel) | | info |

Reading it: falls and sky follow the reference grain; every part has a declared angle; red and gold survive. What
fails is the zone STUBS (one field-mean angle per tone component): chaos and off-grain tiles sit in the village roofs and
mixed foliage, and small buried stub parts trip angle_coherence. Those are M2/M3 (direction fields, strata, crowns,
buildings). Thread v0 merged the two water blues away (area-weighted), so the falls are cream + mist only (M4).

## Scoreboard

| date | label | dir OK % (visible) | chaotic % | dir all % | angle coh. | density mean / p95 / flags | trims per 100 cm2 of covered area | satins / blobs / >7 mm / <1 mm / fans | max stack / cm2 > 2 | threads (red, gold) | gates passed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-19 | baseline: shipped Rev B DST | 11.7 | 77.9 | 2.4 | FAIL: no part ids | 5.67 / 10.45 / 194 | 113.1 (452) | 1925 / 1159 / 0 / 31 / 319 | 6 / 19.97 | 12 (n, n) | 0/8 |
| 2026-10-20 | M1 skeleton (sky + falls splitters, zone stubs) | 89.0 | 7.0 | 63.5 | FAIL (109) | 4.43 / 8.09 / 78 | 33.0 (132) | 0 / 0 / 0 / 0 / 0 | 5 / 8.7 | 12 (y, y) | 3/8 |
