# Pixel Sky sherpa fleece jacket · HK-FL-PIXSKY · pack review "rfq-readiness" · chair output · 2026-10-22

Input: Rev F (all.txt + page PNGs), project source, one blind td-generalist pass (findings PS-01 to PS-26 + feasibility matrix). Chair checks re-opened: all.txt lines quoted in PS-01/02/03/06/07/09/10/11/13/14/15/21/23/24 (they hold what is claimed); emb_place.py header and place(); fleece.py docstring, EASE_CM and the pocket-bag note; STATUS.json; brief.md.

Every item here is a RECOMMENDATION. Nick confirms fit and spec, the founder signs, Ops sends to the factory. This file has no measurement values; numbers live in the json block and come from the engine.

## Team decision: full loop NOT needed

- Only one pass ran, and nothing in it is disputed. The high-confidence findings are either sourced to a pack line I re-opened and confirmed, or they are factory questions whose answer we cannot have yet. Another TD cannot settle a factory question; the factory has to answer it.
- Nothing the passes could disagree on would change the factory request. The RFQ asks the same questions whichever way a specialist leans on pile ease, seam type or the bird resolution. Per the caller, details are settled with the factory after the RFQ.
- The only judgement calls with a round at stake are PS-22 (pile ease) and PS-08 (the unlined reverse). Neither can be verified from photos or files. They need a human fit session and a fabric photo, so they go to ESCALATE / first sample and not to more agent passes.
- The generalist delivered the feasibility matrix. No gap.

Evidence-floor adjustments:
- **PS-16: high → med.** The pack really does not ask for MOQ per layout or per size, and that part is sourced (J1 asks only "MOQ, lead time"). The claim that a low-MOQ mill "may only run a border repeat" is opinion. The ask stands.
- **PS-19: high → med.** The trim list is sourced. The per-trim MOQ risk is opinion.
- **Opinion tags kept.** PS-07 (that the weight is light) and PS-10 (that flatlock would be better) stay tagged opinion. The missing-spec part of each finding stays high.

## (a) MUST-FIX before sending (Rev G)

### Builder can do from files (no human input needed)

| # | Finding | Fix in Rev G |
|---|---|---|
| B1 | PS-01 | Remove every old-factory statement. That covers the "Factory said …" quotes on F2, the "frames on file / max colours per file (confirmed)" lines on F1 §2, F2 §3 "frames confirmed", and both "factory.json" mentions on G1 and F2. Turn each one into a question (they are in section b). Re-address F1 to "the factory", not "the embroidery factory": the new supplier may do everything in-house. |
| B2 | PS-02 | Drop Q1. Replace it with the TBD one-pager the builder already planned: open points for the factory only, with no founder Q&A, no board/inbox paths and no IP line. |
| B3 | PS-03 | Drop R1. Cut J3 down to the side-by-side image plus one line saying cells cannot follow sub-cell render edges and the designer may touch up the maps. On G2 to G5 keep the colour stops, thread refs, stitch/trim counts, size and placement; remove the gate blocks, the IoU rows and the "IP cleared" sentence. Thread refs read "or your nearest match". |
| B4 | PS-04 | Remove the internal provenance: the T3 PATTERN CHECK row, the "pile ease vs Drum Island" note, the T2 "mockup vs block" note, and the founder dates and block names on the cover, T2, T3, J1 and J3. Keep "fit sample in size M is mandatory before the size set". |
| B5 | C-06 (chair) | Fit-sample wording. Rev F says "blank sherpa is fine", while PS-22 asks for a stock sherpa of the same pile height and weight as the jacquard quality. Use: "Fit sample in M in a stock (plain) sherpa of the same pile height and weight as the quoted jacquard quality." This still allows a blank, as the founder decided, and makes the fit sample valid for the jacquard. |
| B6 | PS-07 | Add a "Shell fabric: please state" block. List fibre content, pile type (curly or straight), pile height, single- or double-face, weight, usable width, shrinkage warp and weft, colourfastness, and finished stitches and courses per cm. Show our current weight as [proposed — confirm]. Our pile-height assumption is in the fleece.py docstring; print it from the engine as [proposed — mill to state]. |
| B7 | PS-10 | Add a per-seam table with columns seam, stitch type, finish and SPI. Stitch types are [proposed]: overlock plus taslan tape on body seams, lockstitch plus folder for the bindings, edge-stitched zip setting, bar-tacks at pocket ends and zip ends. Leave the SPI column as "factory to state", because the engine sets no SPI value yet. Add a pile-shaving line for seam, binding and zip allowances: "factory to advise". |
| B8 | PS-11 | Add a neck-tape carrier piece to the cut list and BOM as [proposed — confirm]: navy taslan over the collar/body seam, carrying the main label, the size label and the hanger loop. Its length comes from the engine's collar/neck seam value, not typed by hand. |
| B9 | PS-14 | Measuring page: a POM diagram plus the rule "measure garment flat, at the base of the pile, not the pile surface". Add a sleeve-opening "stretched" row marked "TBD — factory to measure at the fit sample" [proposed]. The engine re-sets the binding-width tolerance to one that can be measured on a pile edge [proposed]. |
| B10 | PS-15 | G1: "Per-size positions = DXF layer-eight marks (plot PDF)". The E3 reference line must match emb_place.py, which grades E3 by keeping its distance from the cuff seam. As printed, the M coordinate reads "from the underarm line", which is fine as an origin but is not the grading rule. Say both. |
| B11 | PS-21 | One bag-anchoring statement only. T2 says "bar-tacked to the zip facing"; fleece.py says "free-hanging, bar-tacked to the CF facing". Print [proposed — confirm]: "bag free-hanging, top bar-tacked to the CF facing; factory to advise if it should be caught in the side seam". Slit finish: [proposed] bound slit with a taslan facing, factory to recommend. |
| B12 | PS-13 | F1 currently says "on the real shell fabric (washed, as in bulk)", but no bulk wash is defined. Change it to "on the real shell fabric, in the bulk finish" and add the wash placeholder from N3 below. |
| B13 | PS-06, PS-16, PS-08, PS-19 | Replace F2 with the feasibility questions in section (b), word for word. Delete the J1 "for the mill" box, which duplicates them. |
| B14 | C-01 (chair) | STATUS.json still lists "collar outer: taslan or sherpa?" as open. The founder settled it on 21 Oct (sky taslan, brief.md answer six). Close it there so it doesn't come back into the TBD page. The trims question becomes factory question A-trims, and the mill and factory questions become section (b). |

### Needs Nick / founder input (each has a placeholder so sending is not blocked)

| # | Decision | Owner | Placeholder Rev G carries |
|---|---|---|---|
| N1 | Pantone TCX for sky, cream, black (bird), navy (binding/tape/facing/pocket zips), the black CF zip, the blue pulls and the sky collar taslan (PS-09) | Nick | "Colour standard: Pantone TCX to follow. Until then, match the hex values shown, and please propose your nearest TCX / stock card for each" [proposed — confirm]. |
| N2 | Lab-dip order of work (PS-09 + chair). The founder's words are "collar taslan matched to the sky sherpa", but that sherpa does not exist yet. | Founder | "Sky sherpa yarn and sky taslan are dipped to the same TCX in parallel; final taslan approval is against the approved sherpa knit-down" [proposed — confirm]. This keeps the founder's intent and stops the dip waiting on the knit-down. |
| N3 | Wash / care (PS-13) | Founder + Nick | "No garment wash. Care: cold machine wash inside out, no tumble dry or low, do not iron the pile; final care text after the mill's fibre content and the wash test" [proposed — confirm]. |
| N4 | Quantity ladder + size ratio (PS-06) | Nick | Builder's four-step ladder [proposed — confirm]. Size ratio: "quote per size run across XS to 3XL; ratio to follow" [proposed — confirm]. Ask for prices per layout and per size, not only per piece (section b). |
| N5 | Commercial terms (PS-06): Incoterm, payment terms, sample ship-to, reply-by date, target price (none is given now, PS-05) | Nick / Ops | "FOB origin port; payment terms per your standard (please state); samples to Haki Studios, Ohio; reply by [date — Ops]". No target price on the first send [proposed — confirm]. |
| N6 | Labels + packing (PS-12): main-label artwork, RN / manufacturer ID, hangtag, polybag fold, carton marks, barcode | Founder / Ops | "Main label: Haki house label, artwork to follow. Size label woven. Care/content/COO label at the wearer's left side seam, text to follow. Hangtag + single polybag per piece; fold to be advised by the factory so the pile is not crushed; carton marks to follow" [proposed — confirm]. |
| N7 | Chin guard / zip garage at the collar top (PS-20) | Founder | Ask it as a factory question ("do you recommend a zip garage on this pile?"). Do not add it to the design yet. |

## (b) Feasibility questions for the factory (final wording, replaces F2)

Please answer each with YES / NO, or a value plus a unit.

**Knit sherpa (colours knitted in)**
1. Can you knit the design into the sherpa placed per panel, so each pattern piece has its own map as in our files? If not, can you knit a continuous border repeat that we place when cutting?
2. Our maps are one per panel and per size. Do you price set-up per map, per size or per panel? What is your MOQ in metres or pieces per map, per size and per colourway?
3. What machine gauge do you use? After brushing, how many stitches and courses per cm are finished? Which file format do you want (we can supply indexed BMP or PNG, or export others)?
4. Fabric: fibre content in %, pile type (curly or straight), pile height in mm, single- or double-face, weight in g/m², usable width in cm, shrinkage in % warp and weft, colourfastness rating.
5. What is the smallest motif detail you can hold on this pile, in mm?
6. Can you add a third colour (black) in one small area only (the bird)? Is there an extra cost or MOQ?
7. Can you knit the plain cream collar-inner panel in the same run?
8. Please send a daylight photo of the reverse of a similar knitted sherpa with a ruler in shot. Is the reverse acceptable as the inside face of an unlined jacket, or do you recommend a lining or bonding?
9. What are the price and lead time in days for a knit-down of the front-right panel in size M?

**Embroidery on the sherpa**
10. Do you embroider in-house? If you subcontract, will the same shop do bulk?
11. What is your maximum frame size in mm, and the maximum number of thread colours per file?
12. Do you hoop the panel or float it on adhesive cutaway? Do you use water-soluble topping on pile?
13. What are the strike-off price per file and the lead time in days? How do you price embroidery: per thousand stitches, per trim, per hooping or per piece?

**Collar, bindings, zips, pockets, seams**
14. Can you source a smooth sky-blue nylon taslan dyed to our colour standard? MOQ and lead time?
15. Can you make a stand collar with a taslan outer and a sherpa inner and the zip running to the top? What construction do you suggest?
16. Can you bind the hem and cuffs (with an elastic channel) and pipe the neck seam with navy taslan bias binding on this pile? Do you shave the pile in the binding allowance?
17. Navy taslan for binding, tape and facing: in stock? MOQ?
18. Black separating coil CF zip with a blue pull, and navy coil pocket zips with blue pulls: stock or custom? Please send stock colour cards. MOQ and lead time?
19. Can you set the CF zip on this pile without pile catching in the coil (for example by shaving the zip allowance)? Do you recommend a zip garage at the collar top?
20. Can you make a vertical zip pocket with a slit opening in this pile? Which slit finish do you recommend? Will you send a photo of a mock-up on a scrap before cutting?
21. Seams: do you recommend overlock plus taslan tape, or flatlock, on this pile? What stitches per inch do you use for each seam?

**Labels and packing**
22. Can you make the woven main and size labels and the printed care/content/COO label? MOQ?
23. Can you supply the hangtag and polybag? Which fold do you recommend so the pile is not crushed?

**Samples, price, timing**
24. Fit sample in M in a plain stock sherpa of the same pile height and weight as the quoted quality: cost and lead time in days?
25. Jacquard prototype in M with embroidery: cost and lead time in days?
26. Price per piece at each quantity on the cover, with sampling and set-up charges listed separately from bulk.
27. Bulk lead time from approval, your factory closure dates for Chinese New Year, and your latest approval date for goods to land in Ohio in early April.
28. Please also tell us the seam allowance and shrinkage % you used on the samples.

## (c) For the first sample / size set, not the RFQ

- **PS-22 pile ease:** the chest ease probably covers the pile; bicep, armhole and the zipped stand collar may feel tight. The chair adds that the fleece.py docstring pile assumption makes this plausible. Judge it at the M fit sample in a sherpa of matching pile, in a human fit session. Change nothing before then (HOLD).
- **PS-23 collar neck not graded:** try on L and 3XL zipped at the size set. Nick decides whether the neck opening grades for fleece (HOLD).
- **PS-24 grade steps:** body length into 3XL, and shoulder at L. Both are inherited from the approved Drum Island chart. Nick confirms (HOLD).
- **PS-25 motif-to-band gap:** this changes across sizes because the bird and sparkles anchor to the neck while the band anchors to the hem. Nick reviews XS and 3XL maps before the size set. Re-anchoring is engine work, not a factory round.
- **PS-26 mockup vs block:** the render is slimmer than the block, so the sample will look boxier. Nick is aware; no action.
- **PS-17 bird at single-cell resolution:** judge it on the knit-down photo, flat with a ruler. If it blurs, switch to option B. The E1B file is already built.
- **PS-18 sparkles on pile:** check the strike-off on a pile offcut with raking-light close-ups and a ruler.
- **PS-20 / PS-21 zip on pile, pocket slit:** check on the fit sample and the scrap-mock photos.
- **PS-13 wash test of the knit-down:** check shrinkage, navy-on-cream bleed and pile matting.
- **PS-14 measuring:** the factory's measured sheet of the fit sample is a cross-check only. Nick re-measures at the pile base, and adds the sleeve-opening stretched value from the sample.

## (d) Red flags

1. **Cost driver: engineered maps per panel and per size (PS-16, med).** If the factory charges set-up or MOQ per map, the quote can blow up. The fallback is ready in principle: a continuous border repeat placed in cutting, plus option B for the bird. Hold it until question one is answered; don't build it now.
2. **Timeline (C-03, chair, opinion).** The sequence is knit-down, fit sample, jacquard proto with strike-off, size set, then bulk of a custom-knit fabric. Chinese New Year 2027 falls in early February, and the product lead's earliest Ohio landing is early April. That leaves almost no slack: bulk fabric probably has to be knitted before the closure, which means sampling decisions by around mid-December. Ask question twenty-seven and build the calendar back from the factory's answer. If it slips, the options are air freight or a later drop. The product lead decides.
3. **Unlined reverse (PS-08).** Nobody has seen the inside face. If it is unacceptable, a lining changes ease, BOM and cost after sampling.
4. **Seam bulk on high pile (PS-10).** Overlock plus a tape that encloses the seam can be very thick. Let the factory recommend.
5. **Colour circularity (PS-09).** Hex-only colours plus "match the taslan to a sherpa that does not exist yet" is a recipe for re-dips of two to four weeks. N1 and N2 fix it.
6. **Flammability / fibre content (C-04, chair, opinion: verify with compliance).** Raised-pile fabrics are the class US general-clothing flammability rules care about. Fabrics made entirely of certain synthetics, polyester among them, are exempt as I understand it; blends are not. If the mill's fibre content is not entirely polyester, a flammability test is needed before bulk. Question four gives the fibre content.
7. **IP line in the supplier copy (PS-02).** The "resembles a game sprite" wording must not go out. B2/B3 remove it.

## ESCALATE

No finding was disputed, so nothing needs settling between TDs. These open points cannot be settled from the inputs. Each needs the evidence named:
- **PS-22 pile ease:** settled at a hands-on fit session on the M fit sample (base-size wearer; front, side, back, seated and arms raised; zipped collar). Who: Nick, with the freelance human TD hands-on.
- **PS-08 reverse face:** settled by a daylight photo of the fabric reverse with a ruler (question eight). Then Nick judges it by hand on the knit-down.
- **PS-17 bird resolution:** settled by a flat photo of the knit-down with a ruler (question nine). Who: Nick, then the founder picks option A or B.
- **N1 to N7:** the decisions listed in (a). Who: Nick or the founder as marked.

## not-checked

- `not-checked: media index missing` (the pack has no MEDIA.md).
- Page PNGs no TD opened: pg-03, pg-05, pg-06, pg-08, pg-10 to pg-17. Their text was read through all.txt only, so visual layout and legibility are not checked.
- Files no TD opened: pattern_fl.py; the DXF, DST/PES and BMP/PNG map files (only the pack's read-backs were used); jacquard.py beyond a grep.
- Points nobody touched:
  - hanger-loop spec and placement
  - the CF zip length per size against the finished CF length
  - polybag compression of the pile in transit
  - HTS / duty classification for a knit polyester jacket
  - whether the same embroidery files at full size suit XS visually (keep-outs pass; looks were not judged)
  - wearer comfort of the embroidery backing left inside an unlined jacket. Cutaway stays in and touches the body; a soft backing or patch cover may be wanted. This is opinion, for the first sample.

## (e) Merged numeric rows

All rows come from the generalist pass except C-05 (chair). Sources were re-opened and checked against all.txt. No signed master exists.

```json
{"signed_master": false, "rows": [
 {"id": "PS-14", "kind": "tolerance", "point": "Binding width tolerance", "lens": "spec", "severity": "medium", "page": "T3", "size": "M", "value": 0.1, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L157", "comment": "Tolerance cannot be measured on a pile edge; engine to set a realistic value; add a measuring diagram and the pile-base measuring rule"},
 {"id": "C-05", "kind": "comment", "point": "Sleeve opening relaxed on an elastic cuff", "lens": "chair", "severity": "medium", "page": "T3", "size": "M", "value": 15, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L145", "comment": "Only the relaxed value is given; add a stretched point, value to be measured on the fit sample"},
 {"id": "PS-23", "kind": "comment", "point": "Collar neck seam length", "lens": "fit", "severity": "medium", "page": "T5", "size": "3XL", "value": 49.7, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L318", "comment": "Collar neck is not graded and has a pile lining inside a zipped stand; check at the size set on the largest sizes; Nick decides whether neck opening grades"},
 {"id": "PS-22", "kind": "comment", "point": "Bicep half", "lens": "fit", "severity": "medium", "page": "T3", "size": "M", "value": 26, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L141", "comment": "Pile ease on bicep, armhole and neck is small relative to chest; judge at the fit sample made in a sherpa of the same pile height and weight as the jacquard; change nothing before then"},
 {"id": "PS-24", "kind": "comment", "point": "Body length grade between the two largest sizes", "lens": "fit", "severity": "low", "page": "T3", "size": "3XL", "value": 73, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L131", "comment": "Grade step into the largest size is about half the other steps; inherited from the approved chart; Nick to confirm intended"},
 {"id": "PS-21", "kind": "comment", "point": "Pocket zip opening", "lens": "make", "severity": "medium", "page": "T2", "size": "M", "value": 16.5, "unit": "cm", "source": "file+cell", "ref": "/home/devinubuntu/.claude/jobs/70421d6c/tmp/revf/all.txt#L159", "comment": "Specify the slit finish on pile and one bag anchoring statement; scrap-mock photo before cutting"}
]}
```

## (f) Lesson routing (proposals for a techpack-engine session; the chair edits nothing)

| # | Correction that would recur | Route | Proposed change |
|---|---|---|---|
| L1 | Internal QA, provenance and old-factory content in a pack bound for a supplier (PS-01 to PS-04) | craft rule → LESSONS row + red-then-green test | Add a "supplier copy" build mode, plus a gate on the rendered supplier PDF text. It goes red on any of: `factory.json`, `gates_`, `IoU`, `LESSONS`, `status_set`, `Factory said`, `founder`, `IP`, `Rev A`. Plant one string to prove it goes red, then render clean. |
| L2 | Frames and colour limits printed as "confirmed" for a factory that never confirmed them | factory fact → factory.json + `suppliers/<name>-td.md` | Key factory.json per named factory. When the target factory differs or is unknown, F pages print the limits as questions. Create `suppliers/<new-factory>-td.md` once Ops names the trade-show factory. |
| L3 | Pile garments: measure at the pile base, binding tolerance on a pile edge, fabric spec block, reverse-face question when unlined, pile-shaving line | family-wide → family.yaml key | Add a `pile:` family key (measure_at base, a binding tolerance floor, required fabric fields, unlined-reverse question, shave allowances) so the next fleece or sherpa gets these by default. |
| L4 | Elastic cuff given only relaxed | craft rule → LESSONS + test | Extend the existing elastic-waist rule to every elastic opening: the T3 gate fails if an elastic point lacks a stretched row (a TBD placeholder is allowed). |
| L5 | Label placed on a piece that does not exist (neck tape) | craft rule → LESSONS + test | Cut-list/BOM consistency gate: every carrier named in a label or trim placement must exist as a cut-list piece or BOM line. |
| L6 | Hex-only colours, and a dip "matched to" a fabric that does not exist yet | craft rule → LESSONS + test | Pack gate: every colour has a standard (TCX) or a printed "[proposed — TCX to follow]". A "match to X" line fails unless X is an approved standard or approved sample. |
| L7 | RFQ basics missing: cover, seam table, labels/packing, wash line | craft rule → LESSONS + test | An RFQ checklist gate on the supplier copy: a cover with a quantity ladder, a per-seam table, a labels/packing page and a wash/care line, each present (proposed is fine). |
| L8 | Pocket-bag anchoring differs between T2 and fleece.py; the E3 reference wording differs from emb_place.py | product fact → STATUS.json / answers + source | Generate the T2 pocket text from the fleece.py piece note, and the G1 reference line from emb_place's anchor definition. Fix the fleece.py note wording. |
| L9 | Stale open question (collar outer) in STATUS.json after the founder answered | product fact → STATUS.json answers | Move it to `answered` (21 Oct, sky taslan). Re-word the mill, factory and trims questions for the new factory. |
