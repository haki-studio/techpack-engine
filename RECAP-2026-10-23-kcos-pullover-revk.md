# RECAP 2026-10-23 · KCOS pullover hoodie, Rev K (session cf6d5f6f, lead-eng-kcos-hoodie-techpack)

Founder (2026-10-23 ~21:05Z): "make the tech pack as is then we'll send to mandy and see what she thinks". KCOS pivoted from the
zip hooded jacket (Rev J) to a washed-black kangaroo-pocket PULLOVER on the EE / Come Over block, all-over stars as in
`HakiCode/missions/kcos-hoodie-pivot/mockup-2026-10-23-hoodie-front-back.png`.

## Where things are
- Worktree `~/te-kcos-pullover`, branch `kcos-pullover` (off `labels-kcos` d42d82e = Rev J). Local commits only (GitHub suspended).
- Scripts (project `keep-clean-our-space-hoodie`): `pv_block.py` (block), `pv_art.py` (badges + script + stars + hoop plan),
  `pv_view.py` (layouts), `pv_stitch.py` (one DST/PES per hooping), `pv_pack.py` (K1-K6 + Rev J E01-E04/R1 reference).
- Needs Rev J's `art_M.pkl` (git-ignored; copied from `~/te-labels-kcos`) and `inputs/fonts` (+ Source Serif 4 Italic, OFL).
- Outputs `out/pv/M/` (git-ignored): `HAKI_KCOS-PULLOVER_RevK_M.pdf` (11 pp) + `_files.zip`; zoned fallback = `*_zoned*`.

## Decisions + why
- **Block = Akimbo size chart.** EE = Equivalent Exchange Hoodie; EE + Come Over are PLM product type "Hoodie - Akimbo";
  the only data is the published chart `pipeline.size_charts` 801ed167 (4 POMs, XS-XXL, inches). Every other dimension is
  PROPOSED (amber, page K6) and K1 Q6 asks Mandy for her DXF: she already makes this hoodie. No 3XL on that chart.
- **Badges = Rev J regions, translated only** (no rescale/rotation), so every Rev J gate still holds; text from Rev J
  (CN 污 per founder Rev D, KR 우리들 소중한 우주!), never the mockup (AI, mirror-reversed KR, wrong CN).
- **Stars cloned from the Rev J back field** (founder-reviewed), same density (~631/m²), placed AFTER the hoop plan.
- **Hoop plan:** cells ≤ 340 x 505 either way; splits avoid badges/script by 10 mm; stars 10 mm off splits, 18 mm off cut
  edges, none under pocket +10 mm, 40 mm off hood face edge. Result M: FR 4, BK 4, PK 1, SR 2, SL 2, HR 1, HL 1 = **15**.
  BK-H2 is a 59 mm strip with ~7 stars: trimming it would leave a ~40 mm bare band, so kept (K1 Q1 asks for fewer).
- **No minutes/prices in the pack** (supplier-quote rule). Machine minutes stay internal.

## Numbers (size M, DST read-back)
| variant | hoopings | stitches | trims | machine min [I, 750 spm unconfirmed] |
|---|---|---|---|---|
| all-over (the pack) | 15 | 75,600 | 1,147 | ~217 (trims ≈ 115 of it) |
| zoned half-density fallback (`pv_art.py M zoned`) | 9 | 61,132 | 602 | ~143 |

## Gotchas
- `kclettering.set_line` only knows the space glyph for 'en'; pv_art has its own `set_sc`.
- Satin columns overhang the font outline: object footprints for split checks must use the region geometry.
- CJK in plain SVG text = tofu; use `kcdoc.auto` + `tofu.check` (now on every K page).
- `pkill -f <pattern>` inside a bash call can kill the calling shell (pattern matches its own command line).

## Next
- Mandy's answers → factory.json (frame for 340x505, wash after sewing, price basis), then all sizes on HER pattern.
- Strike-off: back panel BK-H1 + BK-H3 through the real wash.

## Delivered (2026-10-23T22:09:14Z)
- Reviewer APPROVE. The fixes applied were: K1 Q1 asks for hoopings per piece, the 90° frame note, K1 sizes taken from the read-back, a thread question, and an embroidery-only quote. In the message, the "lighter version ready" hint was removed.
- The pack was copied to Desktop/TECH PACKS/2 Keep Clean Our Space hoodie/ (Rev K PDF + stitch files zip).
- Founder card: kcos-pullover-revk-send-mandy.
