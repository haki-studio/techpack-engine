# td-generalist · Pixel Sky fleece · pack review rfq-readiness · 2026-10-22 · input Rev F (99b23d6)

**Verdict: RFQ-ready = YES WITH FIXES.** The design data is strong: graded DXF, a jacquard cell map for every panel and size, DST files, and bird options A and B that can be swapped without a rebuild. As an RFQ it fails on three counts:
- It talks to the old factory: it repeats that factory's answers and states its frames and colour limits as "confirmed".
- It carries internal QA pages and jargon.
- The basics a knit-sherpa factory prices from are missing: fabric spec, a colour standard, stitch/SPI, labels and packing, wash, a quantity ladder, and a sample request.

Inputs opened: /home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt; pg-01, 02, 04, 07 and 09 (.png); the project's inputs/brief.md, fleece.py, jacquard.py (grep) and emb_place.py; engine/drum.py; the knowledge bank (only a scorecard and pant/supplier files; nothing for fleece or this factory). The pack has no MEDIA.md, so `not-checked: media index missing`. Pattern diff not run (no tool, and there is no earlier signed fleece pattern; this is the first fleece).

**Findings**

Format: id · point/area · claim · evidence · confidence · ask · cost if wrong

**Must not go to the new supplier**

- PS-01 · F2 + F1 + G1 (old-factory content) · spec · The pack quotes another factory's answers to the new one. F2 has "Factory said 'jacquard sherpa normally no problem' (19 Oct)" and "Factory said 'embroidery on sherpa yes'". F1 §2 says "Frames on file: 300 x 300, 400 x 450 … max 12 per stitch file (confirmed)". G1 says "(factory.json frames)" and "as the factory does (factory.json)". F2 §3 says "frames confirmed". The new factory would take these as its own commitments. · evidence: all.txt lines 493, 506, 724–726, 743, 749, 758, 765–766 · high · ask: rewrite each one as a question to the new factory (frame sizes, max colours, hoop or float, embroidery in-house?). Strip every factory.json reference. · cost: wrong frame/colour assumptions mean a re-split of the stitch files and a lost sampling round, about one to two weeks.
- PS-02 · Q1 page · spec · This is an internal board page and must not go out. It includes "status_set.py --question", inbox paths, the founder Q&A log, and the line "bird resembles a pixel-art game sprite (phoenix)". That line invites an IP doubt from a supplier. · evidence: lines 779–829 · high · ask: replace Q1 with a short "Open points for the factory" list (mill, trims, collar). Drop all founder/IP history. · cost: reputational/IP risk; no rounds.
- PS-03 · R1 page, J3 revision history, the gate/IoU blocks on G2–G5, the "IP cleared" line on G5 · spec · Engine QA jargon: LESSONS codes, gates_jq.py, "planted specks", IoU, chaos tiles, Rev A–D trace history. It means nothing to a mill and makes the pack look unfinished. · evidence: lines 412–466, 545–569, 696–698, 854–927 · high · ask: drop R1. Cut J3 to the side-by-side image plus one line ("cells cannot follow sub-cell edges; designer may touch up the maps"). On G2–G5 keep only the colour stops, thread refs, stitch/trim counts, size and placement. · cost: credibility; possibly a "too complex" quote premium.
- PS-04 · T3 "PATTERN CHECK … pass" row; "Pile ease vs Drum Island"; T2 note "Mockup vs block…"; amber "founder 21 Oct" notes on T2 and J1 · spec · These are internal provenance notes, not factory instructions. They are low harm but noisy. · evidence: lines 109–117, 164–173, 326 · med · ask: keep "fit sample in M mandatory". Remove the block names and founder dates from the supplier copy. · cost: low.
- PS-05 · target price · spec · Checked: no target price, FOB or $ figure appears anywhere in the pack. Nothing to remove. · evidence: grep of all.txt for $/price/FOB · high · ask: none · cost: none.

**Missing for quoting and sampling (RFQ completeness)**

- PS-06 · RFQ cover / quote basis · spec · There is no RFQ page saying what to quote and on what quantities. Missing:
  - quantity ladder and size ratio (MOQ on an engineered jacquard is likely per layout, possibly per size)
  - separate prices for the knit-down, the blank fit sample, the jacquard proto and bulk
  - sample ship-to, response deadline, Incoterm, payment terms
  - an attachment list (DXF, BMP maps, DST)

  · evidence: no such page in the contents list, lines 10–29 · high · ask: Ops/Nick add a one-page RFQ cover. The ladder numbers come from Nick, not from me. · cost: quotes that cannot be compared; about one week of back-and-forth.
- PS-07 · Shell fabric spec · make · The shell is "~300 g/m², polyester [proposed]". Missing:
  - fibre content % (needed for the FTC label anyway)
  - pile height and pile type (curly sherpa or straight high pile)
  - single- or double-face
  - usable width
  - shrinkage warp/weft
  - colourfastness
  - finished stitches/courses per cm (that is what the 2.5 mm cell has to convert to)

  The stated weight looks light for a high-pile jacket shell (opinion). · evidence: line 256; fleece.py docstring "sherpa ~8-10 mm pile" is not printed in the pack · high · ask: closed questions in the feasibility matrix, plus a swatch and a photo of the fabric reverse with a ruler. · cost: wrong pile/weight means the fit sample and ease are invalid; one round.
- PS-08 · Unlined reverse · make · "Unlined: sherpa reverse inside", but on a pile jacquard the technical back (ground knit, colour changes) is the inside of the garment. It may be unsightly or scratchy, and nobody has seen it. · evidence: lines 102–103 · med · ask: a daylight photo of the back of the mill's jacquard sherpa. Ask YES/NO: is the reverse acceptable as an inside face, or do they recommend a lining or bonding? · cost: a lining added after sampling changes ease and BOM; one round.
- PS-09 · Colour standards · spec · Yarn colours are given only as hex (#80AEF7, #F1EAE2, #24201E). There is no Pantone TCX for sky, cream or black, nor for the navy taslan, binding, zips or pulls. The sky taslan is "lab dip to the sherpa", but that sherpa does not exist yet, so the order of work is circular. · evidence: lines 349–353, 264–266 · high · ask: Nick picks a TCX for each colour. The sherpa yarn and the sky taslan are both dipped to the TCX, not to each other. Lab dips are judged only from daylight photos next to the TCX card with a ruler in shot. · cost: a colour rejection of the jacquard, about two to four weeks per re-dip.
- PS-10 · Construction page · make · The only stitch spec is "4-thread overlocked + navy taslan tape". There is no stitch type or SPI per seam, nor any spec for:
  - binding attachment (coverstitch or lockstitch, folder)
  - zip setting, edge-stitch, bar-tack locations
  - the pocket slit finish
  - collar top-edge topstitch
  - pile shaving in seam and binding allowances

  On high pile, an overlocked two-layer seam covered by a tape that "encloses" it is very bulky. Unlined fleece is commonly flatlocked instead (opinion). · evidence: lines 90–103, 229 · high · ask: add a per-seam table (seam × stitch type × SPI × finish). Ask the factory, YES/NO, which they recommend for this pile: overlock + tape or flatlock. · cost: a bulky or rejected first sample; one round.
- PS-11 · Neck seam inside and label carrier · make · The labels go "on the back neck tape", but no neck tape exists in the cut list or the BOM. How the inside of the collar/body/piping seam is finished is not specified. · evidence: lines 103–105, 185–217, 297 · high · ask: specify the inside neck finish (taslan tape over the seam, carrying the main and size labels and the hanger loop), add it to the cut list and BOM. · cost: an open raw seam on the sample; a re-sew.
- PS-12 · Labels + packaging · spec · There is no label artwork and no fibre content, COO, RN/manufacturer ID or care text (FTC). There is no hangtag, polybag/fold, carton or barcode spec. · evidence: line 297 is the only label line · high · ask: add a labels page (main, size, care/content/COO with placement and orientation) and a packing page. Ask the factory YES/NO: can they make woven/printed labels in-house, and at what MOQ? · cost: bulk delay at the TOP stage; non-compliant labels.
- PS-13 · Wash / care · make · There is no production-wash or care spec, yet F1 asks for the strike-off "on the real shell fabric (washed, as in bulk)", a bulk wash that is never defined. Pile behaviour after a home wash (matting, shedding, colour bleed of navy binding onto cream) is unaddressed. · evidence: line 714; nothing on T5 · high · ask: state "no garment wash" (or define one). Ask for the mill's care recommendation and the shrinkage %, plus a wash test of the knit-down (shrink, colour fastness incl. navy-on-cream bleed, pile matting). Standing line: "Tell us the seam allowance and shrinkage % you used." · cost: post-wash shrink or bleed found only at PP; one round.
- PS-14 · Measuring method · spec · T3 has text-only "How measured" and no diagram. On pile it is not said whether to measure at the fabric base or the pile surface. The cuff is elastic but only "relaxed" is given; a stretched value is needed. Tolerance Q (binding width, ±0.1 cm) cannot be measured on a pile edge. · evidence: lines 129–159 · high · ask: add a measuring diagram, a "measure at the base of the pile, garment flat" rule, a cuff-stretched point, and a realistic binding tolerance (the engine sets the number). · cost: a factory measured sheet that does not match ours at the fit-sample stage.
- PS-15 · Per-size art reference · spec · G1 gives the M design centre for E3 "from the underarm line", but emb_place.py grades E3 from the cuff seam. Per-size positions exist only on DXF layer 8. · evidence: line 522 vs emb_place.py lines 2–3, 24–25 · med · ask: state on G1 "per-size positions = DXF layer 8 marks" and fix the E3 reference wording. · cost: sleeve sparkles misplaced in the size set.

**Feasibility and make risk**

- PS-16 · Engineered jacquard per size · make · There are 42 maps (5 panels × 7 sizes, plus the F02 bird variant). A low-MOQ mill may only run one continuous border repeat, or charge set-up and MOQ per layout. This is the biggest cost driver and the pack does not ask it in that form. · evidence: lines 336–345, 356–371, 890 · high · ask: the matrix questions below. A fallback (a continuous horizontal border repeat placed in cutting, with the bird embroidered = option B) should be ready to send if engineered placement is NO. · cost: no quote, or a quote far above budget; two to three weeks.
- PS-17 · Bird at single-cell resolution · make · The option-A bird uses single 2.5 mm cells. On a curled or brushed pile, detail finer than the pile height blurs (opinion; the mill must confirm). Option B (embroidered bird) then becomes the likely route, which roughly doubles embroidery time. · evidence: lines 332–334, 386, 497–499 · med · ask: minimum motif size in mm on their pile; a knit-down of the F02 bird area photographed flat with a ruler. · cost: a rejected knit-down; two weeks.
- PS-18 · Embroidery on high pile · make · The plan is sound (water-soluble topping, cutaway backing, strike-off). Not judged: whether the smallest plain-plus sparkles stay readable on pile. · evidence: lines 504–518 · med · ask: strike-off on a jacquard (or blank) offcut of the actual pile with raking-light close-ups and a ruler. Embroidery in-house or subcontracted, and same shop for bulk? · cost: one strike-off round.
- PS-19 · Low-use custom trims · make · Several trims need custom runs for tiny quantities:
  - sky taslan dyed to match (0.05 m per jacket)
  - a separate plain cream sherpa just for the collar inner (0.05 m per jacket)
  - a black coil zip with a blue pull
  - navy pocket zips with blue pulls

  Each can carry its own MOQ. · evidence: lines 261–280 · high · ask: the MOQ and lead time for each (matrix). Ask YES/NO whether the collar inner can be knitted as a plain cream panel inside the jacquard run. · cost: trim MOQ cash or substitutions found late.
- PS-20 · Zip on sherpa · make · The #5 coil runs from the bound hem to the collar top through about a centimetre of pile, with a taslan facing behind. Pile caught in the coil and pile at the chin are classic failures. There is no chin guard (zip garage) and no pile-shaving instruction at CF. · evidence: lines 75–77; flat pg-02 · med · ask: the factory confirms its zip-setting method on this pile (shave the pile in the zip allowance: YES/NO). Add a chin guard as a proposed detail for Nick to accept or decline. · cost: a re-sew on the sample.
- PS-21 · Vertical zip pocket on unlined sherpa · make · How the slit opening is finished on pile is unspecified (welt, facing or bound edge). The pocket-bag anchoring is inconsistent: the pack says "bar-tacked to the zip facing", while fleece.py says "free-hanging, bar-tacked to the CF facing", even though the bag sits about 20 cm from CF. · evidence: line 85–87; fleece.py line 130 · med · ask: specify the slit finish and the bag anchoring (stitched to the facing or caught in the side seam). The factory gives a YES/NO on feasibility and a scrap-mock photo before cutting. · cost: a re-sew; pocket sag.

**Fit and pattern**

- PS-22 · Pile ease vs thickness · fit · Rough calculation, opinion: thick pile on the inside of an unlined garment takes up inside girth, roughly two pi times the added thickness. Drum Island was corduroy plus a lining. The added ease is spread unevenly:
  - chest gets +4 cm round, which plausibly covers the loss
  - bicep gets +2 cm round, armhole and neck +1 cm, which likely do not
  - risk: sleeves and armholes feel tighter than the Drum Island jacket, and the zipped stand collar tight at the neck

  · evidence: fleece.py EASE_CM line 19; T3 lines 133–147; drum.py lines 13–20 · med · ask: the fit sample in M must be made in a stock sherpa of the same pile height and weight as the jacquard (not any blank fleece), with the pile-height question answered first. Needs a human fit session; no change before then. · cost: one extra fit round if the blank differs from the jacquard.
- PS-23 · Collar neck not graded · fit · The neck opening J is the same in all sizes, and so is the collar neck seam (49.7 cm). Both come from the approved chart. With a cream pile lining inside a 9 cm zipped stand, the collar will be tightest on the large sizes. · evidence: lines 147, 306–318 · med · ask: Nick decides whether J grades for the fleece. Check at the size set (L/3XL try-on, zipped). HOLD until then. · cost: a collar re-cut at the size set.
- PS-24 · Grade irregularities · fit · Body length A steps about two centimetres per size, but only 1.1 cm from XXL to 3XL. Shoulder C steps 1.0 cm at L against 1.2–1.5 elsewhere. Both are inherited from the approved Drum Island chart. · evidence: line 131, 135; drum.py lines 12, 14 · low · ask: Nick confirms these are intended. HOLD · cost: low.
- PS-25 · Motif-to-band spacing across sizes · fit · The bird and chest sparkles are anchored to the neck, but the cloud band is anchored to the hem. Across XS to 3XL the gap between the bird/sparkles and the band changes by the length grade (about four centimetres tighter at XS, seven looser at 3XL). The ends of the run look different from M. · evidence: jacquard.py lines 371–372, 539 (bird_anchor 0, neck); lines 356–363 (hem anchor); emb_place.py line 2 · med · ask: Nick judges this on J2-style maps for XS and 3XL before the size set. No action for the RFQ. · cost: a re-anchor before bulk (engine work, no factory round).
- PS-26 · Mockup slimmer than block · fit · The pack itself notes the render shoulder is about 46 cm against 53 cm on the block. The sample will look boxier than the mockup. The fit is founder-confirmed, so this is only a flag. · evidence: lines 109–117 · high · ask: none; Nick is aware · cost: none.

**not judged:** fabric hand, drape and recovery, pile shedding, true colour (no physical fabric; needs a knit-down and a human fit session). Grade table vs a measured garment: no garment exists.

**Feasibility matrix** (closed questions to the new factory)

*Jacquard sherpa (mill)*
1. Can you knit an engineered, placed-per-panel pile jacquard from our cell maps? YES/NO. If NO, can you knit a continuous border repeat? YES/NO.
2. MOQ in metres or pieces: per layout, per size, per colourway?
3. Knit-down cost and lead time in days.
4. Machine gauge, and finished stitches and courses per cm after brushing?
5. Pile height in mm, pile type (curly or straight), single- or double-face, weight in g/m², usable width in cm, fibre content %?
6. Minimum motif size you can hold on this pile, in mm?
7. Can you add a third colour (black) only in the bird area? YES/NO. Any MOQ or price add?
8. Shrinkage % warp and weft. Will you send a photo of the fabric reverse? YES/NO.
9. Can the collar inner be knitted as a plain cream panel in the same run? YES/NO.

*Embroidery on high pile*
10. Embroidery in-house? YES/NO. If subcontracted, will the same shop do bulk? YES/NO.
11. Max frame size in mm and max colours per file? (Our files use two to three threads.)
12. Do you hoop or float with adhesive cutaway? Do you have water-soluble topping in stock? YES/NO.
13. Strike-off price per file and lead time in days?

*Taslan collar*
14. Can you source sky taslan dyed to our TCX? YES/NO. MOQ and lead time?
15. Can you sew a woven taslan outer to a sherpa inner on a nine-cm stand with a zip to the top? YES/NO. What do you suggest?

*Bindings*
16. Navy bias taslan binding on a pile edge (hem, cuffs with elastic channel, neck piping): can you sew it? YES/NO.
17. Do you shave the pile in the binding allowance? YES/NO.
18. Navy taslan in stock? YES/NO. MOQ?

*Zips*
19. Black #5 separating coil with a blue pull: stock or custom? MOQ and lead time?
20. Navy #3 pocket zips with blue pulls: stock or custom? MOQ and lead time?
21. Can you set a zip on this pile without catching (shave CF)? YES/NO.

*Zip pockets on sherpa*
22. Can you sew a vertical zip pocket with a slit opening in high pile? YES/NO. Which slit finish do you recommend?
23. Will you send a scrap-mock photo before cutting? YES/NO.

*Seams*
24. Overlock plus taslan tape, or flatlock: which do you recommend on this pile? What SPI?

*Labels*
25. Can you make the main, size and care/content/COO labels? YES/NO. MOQ?
26. Confirm placement: main and size at CB neck tape; care at the wearer's left side seam (the pack says "left side seam"; orientation to confirm).
27. Hangtag and polybag sourcing: YES/NO.

*Samples*
28. Blank fit sample in M in a stock sherpa with the same pile height and weight: cost and lead time in days?
29. Jacquard proto in M: cost and lead time in days?
30. Price ladder at Nick's quantities.

**Must-fix before sending (yes-with-fixes):**
1. PS-01: remove the other factory's answers and the "confirmed" frame/colour limits; ask them as questions.
2. PS-02 and PS-03: drop Q1 and R1, cut J3 down, strip the gate/IoU blocks from G2–G5.
3. PS-06: add an RFQ cover page (what to quote, quantity ladder and size ratio from Nick, sample requests, deadline, Incoterm, attachments).
4. PS-07 and PS-08: add the fabric spec questions and the fabric-reverse photo request.
5. PS-09: Pantone TCX for every colour.
6. PS-10 and PS-11: a per-seam stitch/SPI table and the neck-seam inside finish (label carrier).
7. PS-12: a labels and packing page.
8. PS-13: a wash/care line, and fix F1's "washed, as in bulk".
9. PS-14: a measuring diagram, the pile-base measuring rule and a cuff-stretched point.
10. Put the feasibility matrix in as the F2 replacement.

```json
{"signed_master": false, "rows": [
 {"id": "PS-14", "kind": "tolerance", "point": "Binding width tolerance", "lens": "spec", "severity": "medium", "page": "T3", "size": "M", "value": 0.1, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L157", "comment": "Tolerance cannot be measured on a pile edge; engine to set a realistic value; add sleeve opening stretched point and a measuring diagram"},
 {"id": "PS-23", "kind": "comment", "point": "Collar neck seam length", "lens": "fit", "severity": "medium", "page": "T5", "size": "3XL", "value": 49.7, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L318", "comment": "Collar neck is not graded and has a pile lining inside a zipped stand; check at the size set on the largest sizes; Nick decides whether neck opening grades"},
 {"id": "PS-22", "kind": "comment", "point": "Bicep half", "lens": "fit", "severity": "medium", "page": "T3", "size": "M", "value": 26, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L141", "comment": "Pile ease on bicep, armhole and neck is small relative to chest; judge at the blank fit sample made in a sherpa of the same pile height and weight as the jacquard; change nothing before then"},
 {"id": "PS-24", "kind": "comment", "point": "Body length grade between the two largest sizes", "lens": "fit", "severity": "low", "page": "T3", "size": "3XL", "value": 73, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L131", "comment": "Grade step into the largest size is about half the other steps; inherited from the approved chart; Nick to confirm intended"},
 {"id": "PS-21", "kind": "comment", "point": "Pocket zip opening", "lens": "make", "severity": "medium", "page": "T2", "size": "M", "value": 16.5, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L159", "comment": "Specify the slit finish on pile and the pocket bag anchoring; scrap-mock photo before cutting"}
]}
```