# Dismantle Pants — brief (Rev A, 27 Oct 2026)

## Founder's words (verbatim, 27 Oct 2026)
> this is the front and back of a pair of pants we want to sample. these are not the final product though. right now we
> like the print, that's all. we want these to have the hidden inventory fit, along with the same waistband construction
> as hidden inventory. i need to add a back label on the waist band, as well as two back pockets, same shape as hidden
> inventory.

Product: PLM `pipeline.products` e05f184d-20f9-4aa9-be67-126d0d097344 ("Dismantle Pants", status Designing).
Audience of Rev A: the founder's INTERNAL team (sampling draft, not a factory send).

## Sources
| What | Where |
|---|---|
| Print references (print ONLY; ignore their elastic waist + shape) | `inputs/reference/print-reference-front.png`, `-back.png` (copied from Desktop/TECH PACKS/Dismantle Pants/references) |
| HI silhouette + construction lines | `inputs/reference/hi-silhouette-source_konpeito-flat-lay.png` = the Konpeito flat lay (same HI block, cargo removed); line positions copied from `projects/konpeito-jeans/kjflat.py` |
| HI design details + BOM | `projects/konpeito-jeans/inputs/reference/HiddenInventory_CAMOPANTS1_techpack.pdf` p. 2 (design details), p. 8–9 (BOM) |
| HI size chart | PLM `pipeline.size_charts` 9a469aee-d93c-4ec1-9aca-8614b5980b52 (read 27 Oct 2026; same values as Konpeito T3) |
| Labels | `engine/labels.py` + `assets/labels/` (Haki standard main label; care label by fibre) |
| Size label | `dmlabels.py` = copy of `projects/konpeito-jeans/kjlabels.py` (HI centrefold), sizes = HI chart |

## Given (founder)
- Print: black ground, fine tan/beige windowpane grid check (from the refs).
- Fit: Hidden Inventory. Waistband: same construction as HI.
- Back label on the waistband. Two back pockets, HI shape.

## Assumed in Rev A (all amber "[proposed — confirm]" in the pack; listed on Q1)
- Front: HI scoop pockets + coin pocket + zip fly + 28 L shank button (HI front, as Konpeito).
- No cargo pockets, knee seams, hammer loop, HI flag labels; no embroidery.
- Back label = Haki standard main label 6.5 × 2 cm white, OUTSIDE at CB of the waistband, sewn on all 4 sides; inside CB
  carries the size label only.
- Belt loops: HI CB loop replaced by two loops flanking the label (15 mm clear) → 6 loops.
- Fabric: option A yarn-dyed cotton twill check 10–12 oz (preferred) vs option B printed on HI 12 oz denim / 9–10 oz twill.
- Repeat 12.7 mm (1/2 in) square, line ≈ 1.3 mm — ESTIMATED from the photos (P1 shows the working).
- Colours: ground #151513, line #9A8F7B (photo); ≈ 19-0303 TCX Jet Black / ≈ 17-1009 TCX Dune (approximate).
- Sizes: HI published run 26 28 30 32 34 36 38 40; sample size 32.
- Wash: rinse + soften only (no HI stone / enzyme wash).
- Hardware matte black as Konpeito; style code HK-PT-DISMANTLE-BK.

## Owed by Haki ([MISSING])
Mockups front/back (founder ChatGPT render), care label (needs the fibre), hang tag art, barcodes, packing design,
a physical swatch for the line style / repeat.
