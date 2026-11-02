# RECAP 2026-10-27 · KCOS pullover, Rev L (lead-product-kcos-hoodie-pivot)

Founder feedback on Rev K (team review 27 Oct): stars front vs back looked different; halve the back stars, hood just as sparse; remove BK-H2; Come Over specs; brushed fleece + wash exactly like Hidden Inventory.

## What changed (projects/keep-clean-our-space-hoodie)
- `pv_art.py`: `DENS_BY` BK/HR/HL ×0.5; star DECK per panel (library plus-share ~40% + size quantiles, shuffled) instead of a random library pick, so every panel matches front on size + plus ratio; `TRIM_BY` BK 70 mm trims the 59 mm bottom strip (Rev K BK-H2 left, BK-H4 right) → back = 2 hoopings.
- `pv_block.hoop_name`: back halves named BK-L / BK-R so "BK-H2" never reappears as a new file.
- `pv_pack.py`: Rev L, FABRIC + WASH block (Hidden Inventory BOM wording), Q2 asks Mandy to name the HI wash + shrinkage, Come Over only (EE dropped), K5 per-panel stars/sparkles/size table, back-band + BK-L/R legend, Q1 "answer before digitizing".
- Founder (via Chief): A) brushed fleece exactly like Hidden Inventory; B) no wash name on file → Mandy names it.

## Numbers (size M, DST read-back)
| | Rev K | Rev L |
|---|---|---|
| hoopings | 15 | 13 |
| stars | 677 | 535 (back 162→74, hood 108→54) |
| stitches / trims | 75,600 / 1,147 | 72,097 / 988 |
Star mean size per panel 3.24–3.29 mm, plus share 39–41% everywhere. Rev K front 3.3 mm/41% vs back 3.1 mm/38% (random draw) — the founder's "bigger front stars" was in the AI mockup, not the pack.

## Where
- Branch `kcos-revl` in `~/te-kcos-revl` (local, engine main 27c0c70 base). Pack copied to Desktop/TECH PACKS/2 Keep Clean Our Space hoodie (Rev K → older versions).
- TD: td-generalist (L1-L9) + td-chair → HakiCode/missions/kcos-hoodie-pivot/td-chair-revl.md.
- Card kcos-pullover-revk-send-mandy updated to Rev L (WhatsApp). PLM product 83df91ce (Designing) linked to tech_packs; revision set L by hand (nightly sync reads engine main — ship `kcos-revl` so it doesn't revert).

## Gotchas
- Engine y axis runs DOWN from the neck: BK-H2 was the bottom (hem) strip, not the top.
- Hidden Inventory's pack has no wash line; "French Terry/Fleece … Brushed on reverse side" = fleece.
- Run with PYTHONPATH=<wt>/engine:<wt>; copy art_M.pkl + inputs/fonts from ~/te-kcos-pullover.

## Next
- Ship `kcos-revl` to engine main. Deferred TD: labels/COO, SPI, tolerances, Rev J reference-page leftovers → post-Mandy rebuild on her DXF.
