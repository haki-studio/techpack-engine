# RECAP 2026-10-22 — standard labels (lead-eng-standard-labels)

## What / why
Founder (17:30Z): `label-6,5x2cm-white.pdf` = the standard main label for every product; care label from the Haki care-label files by fibre. Konpeito is sampled TODAY, so it went first.

## Built
- `assets/labels/` — copies of the 7 founder files (originals untouched in Downloads). Founder mirror: `Desktop/TECH PACKS/_Brand labels/` + READ ME.
- `engine/labels.py` — `MAIN` (65 × 20 mm), `care_label(composition)`: 100 % cotton → `100-cotton`, 90/10 cotton-poly → `90-cotton-10-polyester`, else **None = FLAG** (never nearest). `files_for()` for zips, `render()` for previews (cache in out/labels_cache).
- LESSONS **D7** + `tests/test_labels.py` (red on a "≥80 % cotton → 100-cotton" mutation, green on the real rule).
- Konpeito **Rev B7**: T5 BOM, T6, T7 (placement rects 65×20 / 30×65, label detail draws the real main label), T7b (main + care columns replace the HI crops; care = front + back), Q1 + cover flags (T7b no longer flagged), zip labels/ carries main + 100-cotton care files, README text. Built from the B6 out/ copied from the `tp-konpeito-jeans` worktree (code identical to main); only label content changed.

## Decisions
- Care label colour: the `-white.pdf` (white ground, black print), to match the white main label. The plain PDF's black/red version ships in the zip as an alternative.
- Main label weave: kept "woven, flat, sewn down on all 4 sides" (as HI) marked [proposed — confirm weave]; the file does not state the label type.
- The care label prints MADE IN CHINA; flagged in T7b + README ("tell Haki if made elsewhere").

## State
- PR https://github.com/haki-studio/techpack-engine/pull/53 (head 8e9a4a2), independent review running.
- Next: on APPROVE, swap Rev B7 into `TECH PACKS/1 Konpeito jeans/` (B6 → older versions) + READ ME line; then KCOS, Pixel Sky, Koi.

## Pending / gotchas
- KCOS / Pixel Sky / Koi packs record NO fibre content → care label cannot be picked until the composition is known (PLM product data or founder). Do not guess.

## Update 17:50Z
- REVIEW: APPROVE 8e9a4a2 (no blockers). Rebuilt from that exact head (T5 row edit had landed after the earlier build), then swapped into TECH PACKS/1 Konpeito jeans (B6 → older versions), READ ME updated incl. the factory asks (main-label material, MADE IN CHINA).
- Review nits left open: Q1 column header reads "What changed in Rev B7" over the B5→B6 rows (stamp bump); brief.md still says 5 × 2.5 main label (input only, not rendered).
- Fibre lookup (PLM, Shopify storefront, TECH PACKS PDFs): KCOS "12 oz cotton duck" (no %), Pixel Sky "polyester" only in our NOT READY draft, Koi "washed duck"/[proposed — confirm]. None recorded as a %. Escalated; care label stays [MISSING] on those packs.
