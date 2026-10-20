# Bench write-up: M3a buildings (20 Oct 2026, after the PR #9 review)

Row "M3a buildings (rule-angled roofs, walls, members; depth by tier)" in BENCH.md / SCOREBOARD.json, scored at engine
commit cef3c8d (branch `engine-m3a-buildings`, origin/main 182a82b merged in; M4g, PR #8, NOT yet merged: the stack /
density numbers below are without its cut-to-2 sequencing and must be re-scored on the merged tree). Command:
`PYTHONPATH=engine python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api`.
Every number is from `out/digitize/BK_M_crop/gates.json` (DST sha256 b759f3d3b9a4611e) or from a scratch variant run
named as such (never benched).

![M3a panel](panel_2026-10-20_m3a-buildings--rule-angled-roofs--walls-.png)

## What M3a does on the crop

The `village` zone became five building windows (temple, pagoda, castle centre, houses right, roof line at the bottom)
with the `building` splitter. Inside each window the template fitter traces the roof / wall / member / ornament tones
(run yaml `building.roles`) and fits:

| part | rule (house.yaml M3a block) | count |
|---|---|---|
| roof plane | NEAR tier: down the slope (perpendicular to the fitted eave; hips fan 20-45 deg to their side). FAR tier: one plane along the eave (rule 3) | 13 (3 near, 10 far) |
| wall plane | one angle per plane, square to the eave of the roof above (along it under a far roof, across under a near one); ground colour = the face's brightest pixels | 21 |
| eave | satin across, along the fitted eave line, every tier whose eave is visible | 11 |
| roof tile lines | bean down the slope in the plane's second roof tone, near tiers | 3 |
| window band | a row of windows as ONE satin band across it | 14 bands |
| member | red rails / posts (frames split into both), gold / blue trims, satin across | 15 |
| stud | dot 1-1.5 mm, never touching | 6 |
| suggested, not sewn (rule 9 minimums) | listed in plan meta `building_suggest` | 7 single windows, 10 members under 1 mm |

Pixels of other tones inside a building window go back to the zones below (foliage stubs 7,914 mm2, ground 4,141 mm2:
M3b). Village stub area: 11,389 mm2 -> 0.

## Crop table

| check | M2 (71f0097) | M3a first PR (49aebb8) | **M3a after review (cef3c8d)** | target |
|---|---|---|---|---|
| direction, INDEPENDENT tiles | 98.6 % of 73 (11.7 %) | 79.9 % of 204 (32.6 %) | **62.6 % of 203 (32.5 %)**: FAIL | >= 85 % on >= 50 % |
| (combined, info) | 91.7 | 86.7 | 80.5 | |
| chaos, all tiles | 4.2 % | 4.3 % | **10.7 % FAIL** | <= 5 % |
| parts / under 20 mm2 | 367 / 11.2 % | 324 / 10.8 % | 364 | <= 400, < 25 % |
| random angles (audited) | 0 | 0 | 0 | 0 |
| angle_coherence fails | 61 | 42 | 48 (stubs 31, studs 6 no-visible, building 10) | 0 |
| separation close | 46 | 24 | 25 | 0 |
| density flags | 113 | 163 | 160 | 0 |
| max stack / cm2 > 2 | 4 / 9.07 | 5 / 12.08 | 5 / 17.44 | <= 2 |
| trims per 100 cm2 | 26.5 | 23.3 | **28.8 FAIL** | <= 25 |
| satin columns / blobs | 0 / 0 | 10 / 0 | 45 / 0 | 0 blobs |
| colours | 12, red + gold | same | same | |
| stitches (file) | 93,036 | 93,961 | 98,561 | info |
| gates | 3/9 | 4/9 | **2/9**: satin, colours | |

**Reading it.** The first PR passed chaos and trims by dropping detail: 17 window bands and 7 members were dropped at
underlaps, far eaves were not sewn and the temple wall was one red slab. The review asked for fidelity first: keep the
detail and report what it costs. That is what this row does. 45 satin details (windows, rails, posts, eaves, trims) cost
the chaos gate (a 1-2 mm satin across a band of horizontal far-tier rows makes the 8 mm tile read as mixed directions),
5.5 trims per 100 cm2 and 4,600 stitches. The stack and density cost is expected to be cut by M4g's sequencer: the
reviewer's trial merge of the first PR measured stack 4 with 0 flags and density 113 -> 59. **This row has to be
re-scored on the M4g-merged tree.**

**Trial merge with M4g (PR #8 head 3b9ad49, local, not pushed or benched):** pytest 186 passed, no HintError. The crop
scored independent 62.1 % of 203, chaos 11.2 %, trims 26.3, density flags 118, max stack 4 with 8.15 cm2 > 2 (39
flags), separation 22, 2/9 gates. M4g lowers stack, density and trims; it does not lower chaos (the satin details across
far-tier rows).

## Direction gate and independent coverage

Rule-angled building tiles moved the independent count from 73 to 203 of 625 (+130). The coverage gate needs 313:
buildings alone cannot reach it on this crop, because cliffs (160 tiles) and stubs (246) read their angles from the
reference. On the building tiles the details now on top (eaves 3 tiles all chaotic, members 9, windows 3) and the walls
(46 tiles, 14 chaotic) pull the independent OK rate to 62.6 %.

## The depth rule (review item 3): relative to scale, partly grain-informed

House rule 3: "depth goes from near-horizontal (far) to near-vertical (near)". The first PR used an absolute 22 mm
threshold, chosen by scoring the grain gate on this same crop. That made it circular, and it would not carry to another
artwork's scale. It is now **relative**: tiers of one style shrink with distance, so the largest tiers on the piece are
the nearest. A tier is FAR when its fitted height is under `near_tier_rel` x the zone's largest fitted tier (house.yaml
default **0.75**: a quarter smaller reads as further back). This is a perspective argument made before scoring. The audit
recomputes the reference height from the zone's roof parts.

On this crop the largest tier is the temple (26.1 mm). The castle tiers (4.8-13.5 mm) are far. The houses-right roof
(20.1 mm, two tiers the fitter could not split) and one 6.3 mm tier whose eave is hidden (height unknown, so near) are
near.

| variant (scratch runs) | independent OK of 203 | chaos | trims |
|---|---|---|---|
| depth rule off (`near_tier_rel: null`, playbook only: every tier down the slope) | 43.3 % | 16.2 % | 31.3 |
| 0.60 | 62.6 % | 10.7 % | 28.8 |
| **0.75 (house)** | **62.6 %** | **10.7 %** | **28.8** |
| 0.90 | 65.5 % | 9.9 % | 28.3 |

**Honesty note:** the far / near choice is what moves this gate (43 -> 63 %), and the reason the far tiers score well
is that the AI render stitched them along the eave. So the gate result for far tiers is partly grain-informed: it
confirms that rule 3 matches this render, not that the rule is right. The founder's live-view look is the independent
check. **Founder question:** do the far tiers read right as rows along the eave, and is "a quarter smaller than the
largest tier" the right line?

## Fidelity (review item 2)

- Underlap clearance is OFF by default (`seam_keep_mm: null`). The scratch run with it on (1.0 mm) keeps 2 window bands
  instead of 14 and 11 members instead of 15. It scores 67.0 % independent, 8.8 % chaos, 27.8 trims and stack 5 /
  15.6 cm2, so dropping detail buys only a small stack gain before M4g.
- Rule-9 minimums are not dropped silently: 7 single windows too small for a satin band and 10 members under 1 mm wide
  are listed in plan meta `building_suggest` with position, size and thread (for the review step / founder card).
- Every visible eave is sewn (11). Before the review, far eaves were skipped.

## Walls (review item 4)

The tone trace called the castle's plaster "bark tan" and gave the temple a red wall: its timber frame is the most
frequent tone there. A wall's ground colour is now read from the face itself: the mean of its brightest 15 % of pixels
(roles member / ornament / roof excluded), matched to the nearest thread by CIEDE2000. 15 of the 21 wall faces are now cream
(2 in the first PR). 4 stay bark tan and 2 dark brown: those are small, shaded faces whose brightest pixels are still
tan. The plaster measured RGB ~ 180-215 / 165-205 / 130-190. Details are the member / ornament / roof-tone
pixels and anything 60 darker than the ground:
- compact details become windows;
- long ones become members;
- a frame (the temple's red timber grid, the castle's red rails) is split into rails along the courses and posts
  across them.

The red slab under the temple roof is gone: the temple wall is cream with red rails and posts.

## What is still weak (looked at the panel)

- Windows: 14 bands survive, but the reference shows ~45 lit windows. Many read as dark outline in the 4 ppm tone trace
  rather than as gold panes.
- The temple roof fans in perspective (tile rows ~110 deg on the left, ~55 deg on the right). Neither side edge is
  visible (crop edge on one side, blossom crown on the other), so it is one front plane at 90 deg.
- The houses-right roof is two tiers merged by blue-framed walls; it counts as near (20.1 mm) and runs down the slope.
- Studs (1-1.5 mm) flag `no-visible-stitches` (6); the flag is kept (A22), and the gate scope is a question for M4.

## Default-preserving (scripts/identity_check.sh)

dst2 probe dst 84ff50ea74938675 / pes 1ecd8f657db3f53a; M5 wb DST 449c14f6e8f693b6; Castle crop DST changes
(intended) 0d86f00be8e9f8fa -> b759f3d3b9a4611e. The same engine with main's zones_BK.json (village = stub) reproduces
0d86f00be8e9f8fa.
