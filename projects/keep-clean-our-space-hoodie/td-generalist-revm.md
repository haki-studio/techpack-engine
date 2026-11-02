I couldn't write `/mnt/c/Users/devin/Desktop/HakiCode/missions/kcos-hoodie-pivot/td-generalist-revm.md` because I have no write tool in this run. The full findings are below, ready to paste into that file. I edited nothing in the worktree.

**5-line summary**
1. Verdict: SEND-WITH-FIXES. Positions follow the mockup, the read-back sums agree (61,962 stitches, 589 trims, 155 + 13 dropped = 168 mockup stars) and the approved text is kept. Two hooping questions (M1, M2) and the star size (M3) need work before sampling.
2. Biggest sampling risk (M1): on the sleeves, pocket, hood and the neck end of FR-H1, the frame is bigger than the cut piece. Q4 ("if you can") must become a required either/or question.
3. Everything except the back already fits a 400 x 450 frame without turning. Build a back plan B now so Mandy's Q1 answer doesn't force a re-plan (M2).
4. The stars and badges are too small because the mockup isn't to scale: positions were mapped by proportion but sizes stayed at Rev J. The stars read about 1.5 to 2x bigger in the mockup, and some dots read back as specks. The founder should choose sizes from a full-size paper print (M3, M4).
5. Smaller fixes: the empty lower front corners (M5), which half of the sleeve is the front (M6), the script against the pocket opening (M7), and the hood mapping and lining (M8).

---

# KCOS pullover, Rev M (size M), td-generalist review, 2026-10-27

**What I opened myself:** `inputs/mockups-3-2026-10-27.png`, `out/pv/M/plan_allover.json`, `result_allover_SR-SL.json`, `layout_allover.png`, page previews K1/K3/K4/K5, the docstrings of `mock3.py` and `pv_art.py`, and `td-chair-revl.md`. I did not run `dstzoom` or any script; the "not judged" list is at the end. Everything here is a recommendation: Nick confirms spec, the founder signs, Ops sends.

**Arithmetic I checked:** the K1 stitch total matches the per-file stitch counts (61,962), the K1 trim total matches (589), and the stars per piece add up to 155. With the 13 dropped stars that makes 168, which equals `mockup_stars`.

### M1 · block (for sampling; the fix is text plus one gate) · make
**Problem:** on most pieces the frame is bigger than the piece, so a cut piece can't be hooped.
- The 340 x 505 frame (505 x 340 when turned) is bigger than:
  - the hood pieces (about 350 x 400, `pieces_mm.HR/HL`)
  - the pocket (about 467 wide at the bottom, narrower at the top, while the turned frame is 505 wide)
  - both sleeves where they narrow below the elbow (in `layout_allover.png` the SL-H1 and SR-H1 boxes run past the sleeve outline)
- FR-H1 starts 27.8 mm below the HPS, so a 505-tall frame would sit above the shoulder line and across the neck opening.
- So hooping cut pieces only works with oversized blocks or with floating the piece on hooped backing. K1 Q4 and K5 ask for oversized blocks only "if you can".

**Fix:**
- `pv_pack.py` K1 Q4: make it a required either/or question. "(a) Oversized blocks, recut after embroidery: needed for sleeves, pocket, hood and front. (b) If not, do you float cut pieces on hooped tear-away backing? Which?"
- `pv_art.py`: add a gate that centres the frame on each cell and lists every hooping whose frame overhangs the piece (plus the block margin). Print that list on K3.

**Cost if wrong:** one sample round.

### M2 · should-fix · make/spec
**Problem:** the hoop plan only works on the 340 x 505 frame, and Q1 says Mandy's frames are 300 x 300 and 400 x 450.
- Under 400 x 450, every cell except the back fits **without turning**: FR 317x365 and 300x291, PK 359x155, SR 289x376, SL 388x340, HR, HL.
- Only BK-L (486 tall) and BK-R (469 tall) fail.
- Q1's line "the pocket and left sleeve need the frame turned" is only true on 340 x 505.

**Fix:**
- Run `pv_art.py` with `HOOP=[400,450]` as a second variant. The back can stay at two hoopings if the cells are capped at 450 tall, by dropping or nudging the lowest back stars. Otherwise it needs three hoopings.
- Print both plans on K1 as plan A and plan B, so Mandy's answer picks one rather than starting a re-plan.

**Cost if wrong:** days of re-planning after her answer.

### M3 · should-fix · make/fit
**Problem:** the stars are smaller than the mockup, and the smallest may not survive.
- The mockup isn't to scale. Measured against body width, its sparkles come out roughly 1.5 to 2x the library's 3.8 to 6.3 mm (photo estimate, not a measurement). Measured against body height they come out closer. You said 1.5x; I agree, and the large sparkles are worse than that.
- The bigger risk is the dots. In the SR-H1 read-back render (K5), several DOT units read as one-to-two-pixel specks or commas. On a 350 gsm garment washed after sewing, sub-minimum dots tend to sink, knot at tie-in/tie-off, or disappear.
- About 34 stitches per star (SR-H1: 1,170 stitches for 34 stars) is a lot of tie-in for a unit that small.

**Fix:**
- `pv_art.py`: replace "translated, never rescaled" for stars with:
  - a per-kind size rule, with SPK size taken from the mockup blob `size_px` times the body-width factor, capped by keep-outs
  - a DOT minimum (TD to set; a number goes in the engine, not here)
  - re-digitising at the new size (`kcstitch`), never scaling the DST
- Add a star swatch (the smallest DOT, the smallest SPK and the largest SPK) to the Q5 strike-off. The back panel carries only the back stars, which are the larger ones.
- The founder or Nick picks the size from a full-size print of one sleeve and the front.

**Cost if wrong:** after the wash the garment reads as "no stars", which costs one round.

### M4 · should-fix · fit (founder look choice)
**Problem:** the badges are placed by proportion but sized at Rev J, so the back reads emptier and more crowded than the mockup.
- Badges are placed with x scaled to body width and y to body height, but kept at their Rev J size (01 is 196x175 mm, 02 is 149x190, 03 is 110x218, 04 is 191x59).
- In the mockup the JP burst spans about 40% of the back width. In Rev M it spans about 27% (photo estimate).
- Because y is squeezed and the sizes are not, the JP-to-CN gap shrinks to about 16 mm by bounding box (01 bottom ≈ 246, 03 top ≈ 262 from the HPS). The mockup shows a clearly larger gap, and K4 shows the JP sticks almost touching the CN top dot.

**Fix:**
- Recommended: keep Rev J badge sizes, since the puff files are proven and scaling puff is a re-digitise. Re-space instead: in `pv_art.py`, set the badge 03 (and 04) target y from a minimum-gap rule rather than raw proportion. There is room above the hem.
- If the founder wants the mockup's scale, it is capped by the BK-L cell width and needs new puff files plus a new strike-off.
- Founder decision from a full-size paper print taped to a Come Over hoodie.

### M5 · should-fix · fit
**Problem:** the lower front corners come out empty.
- The mockup front shows stars beside the kangaroo pocket on both sides.
- Rev M has none on the front below FR-H1 (y 392.5) or FR-H2 (y 360.2) (layout png).
- Three of the four front drops sit in one column at x ≈ -314 (y 299, 391, 473). That is the side-seam edge keep, which a short inward nudge should have cleared, yet the stars were dropped. The two BK drops at x ≈ ±310-322 have the same pattern.
- The FR cells use 365 and 291 of the 505 mm available height.

**Fix:**
- `pv_art.py`: for edge-keep conflicts, search inward along x first, and let drops caused by edge keep use a larger nudge limit (TD sets the number).
- Write each drop's cause (which keep-out) into `plan.stars.dropped` so all 13 can be audited.
- Then extend the FR cells down.

### M6 · should-fix · spec
**Problem:** the pack doesn't say which half of the sleeve is the front.
- The K3 note says "Sleeves: x from the sleeve centre line" but not which sign is the front.
- A drop-shoulder cap is nearly symmetric, so the factory can mirror it.
- SR (x -127..162) and SL (x -195..193) are deliberately asymmetric (`mock3.py`: front view = front half, back view = back half), so a mirror changes the look.

**Fix:**
- `pv_pack.py` K3/K5: state "+x = front notch side" and draw the front notch on the sleeve outlines.
- Once Q6 returns the DXF, key the sign to Mandy's notches.

### M7 · should-fix · make
**Problem:** the end of the pocket script may land in the pocket-opening finish.
- The script runs to x ≈ 198 (centre 97.9 plus half of the 200 mm width), which is the PK-H1 cell edge.
- The slanted pocket edge at y ≈ 179 is about x ≈ 219 (measured off the layout png), so the "..." sits right at the 22 mm pocket keep.
- Kangaroo openings are usually turned back or bound and topstitched. If Come Over's finish is wider than about 12 mm, the ellipsis gets caught.

**Fix:**
- Add to Q6: "pocket opening finish width?".
- `pv_art.py`: make `KEEP_POCKET` per edge (the opening edge = finish + seam allowance), or shift the script left.

**Can't judge:** whether the satin hairlines of the Source Serif Italic hold up at a 9.7 mm cap height. That needs a `dstzoom` crop of PK-H1 and the minimum column width from the read-back.

### M8 · should-fix · fit/make
**Problem:** the hood mapping is a guess, and the hood construction is unknown.
- HR is a 225x93 band with 7 stars; HL is 228x203 with 8. The back view of the hood in the mockup looks roughly symmetric (photo).
- `mock3.py` maps the front view as "the strip just behind the face turn-back", which is a proportion guess onto a two-piece hood.
- Hood construction is unknown: lined or single, two-panel or three-panel. On a single-layer hood the backing shows inside when the hood is down.

**Fix:**
- Add to K1: "Is the Come Over hood lined? How many panels?"
- Re-map the hood from Mandy's hood pattern.
- Until then, keep HR and HL marked [proposed] on K5 (they are not marked there now).

### M9 · note · spec (cost)
**Problem:** most of the hoopings are for a few stars each.
- Seven of the nine hoopings are star-only, at 266 to 1,220 stitches each.
- The two hood hoopings carry 15 stars between them.
- If Mandy prices per hooping, the stars outside the back cost more than the back badges.

**Fix:** Q3 should ask for the price with and without HR/HL (and with a single front hooping, if plan B allows it), so the founder can trade stars for cost.

### M10 · note · spec
- **K4 numbering:** still 01-04 then 07 (CR-4 from Rev L, not fixed).
- **K4 Korean line:** renders with wide word gaps. Check that the PDF text matches the file's string exactly.
- **K1 Self line:** still reads "Brushed on reverse side". Rev L founder choice L2 (fleece vs French terry) shows no visible resolution.
- **Badge colour count:** BK-L has 10 colours and 14 stops, within the max 12 colours per file stated on K3.

### Feasibility matrix (closed questions for Mandy)
- 340 x 505 frame: YES/NO? If NO, plan B (M2).
- Oversized blocks: YES/NO? If NO, can you float cut pieces on backing: YES/NO? (M1)
- Kangaroo pocket opening finish: width in mm (M7).
- Hood: lined YES/NO, panel count (M8).
- Max colours per file: 12 is on K3; BK-L uses 10.
- 3 mm puff foam through the garment wash, plus the star swatch: YES/NO, and how many days (Q5 + M3).
- Special trims: none.
- Labels (content, COO, care, size, placement): still missing. Carried from Rev L to the post-Mandy rebuild.

### Not judged
- **Zoom crops:** none run (no tool). Need `dstzoom` crops of the smallest DOT and SPK units, the pocket script hairlines, the puff edges, and BK-L at the CB split.
- **Pages:** K2 and K6, plus the Rev J reference pages, were not opened this pass.
- **Other sizes:** only M checked; grading not looked at.
- **Media:** `not-checked: media index missing`.
- **Fit:** none; there is no garment yet.

```json
{"signed_master": false, "rows": [
 {"id": "M2", "kind": "comment", "point": "back left hooping height exceeds the shorter frame", "lens": "make", "severity": "medium", "page": "K3", "value": 486.0, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#cells.BK[0].h"},
 {"id": "M2", "kind": "comment", "point": "back right hooping height exceeds the shorter frame", "lens": "make", "severity": "medium", "page": "K3", "value": 469.4, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#cells.BK[1].h"},
 {"id": "M3", "kind": "comment", "point": "front star mean size", "lens": "make", "severity": "medium", "page": "K5", "value": 3.6, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#stars.per_panel.FR.mean_mm"},
 {"id": "M5", "kind": "comment", "point": "front hooping one bottom edge", "lens": "fit", "severity": "medium", "page": "K3", "value": 392.5, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#cells.FR[0].box[3]"},
 {"id": "M7", "kind": "comment", "point": "pocket script width", "lens": "make", "severity": "medium", "page": "K4", "value": 200.0, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#script.width_mm"},
 {"id": "M1", "kind": "comment", "point": "hood piece height versus frame", "lens": "make", "severity": "high", "page": "K3", "value": 390.0, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#pieces_mm.HR[3]"}
]}
```

Files I worked from:
- `/home/devinubuntu/te-kcos-revm/projects/keep-clean-our-space-hoodie/out/pv/M/plan_allover.json`
- `/home/devinubuntu/te-kcos-revm/projects/keep-clean-our-space-hoodie/out/pv/M/layout_allover.png`
- `/home/devinubuntu/te-kcos-revm/projects/keep-clean-our-space-hoodie/out/pv/M/pages/prev_K1.png` (also K3, K4, K5)
- `/home/devinubuntu/te-kcos-revm/projects/keep-clean-our-space-hoodie/pv_art.py`
- `/home/devinubuntu/te-kcos-revm/projects/keep-clean-our-space-hoodie/mock3.py`
