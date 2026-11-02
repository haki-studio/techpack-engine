# KCOS washed-black pullover hoodie, Rev M (size M, for Mandy): TD chair comment sheet, 2026-10-29

**Inputs judged:** the td-generalist pass (M1-M10), the Rev L chair sheet, and the worktree source as it is now (`pv_pack.py` lines 18-169 and the `pv_art.py` constants and drop logic, both read by the chair). Also opened: the rebuilt `out/pv/M/plan_allover.json` and the pre-rebuild `pages/prev_K4.png`, plus `suppliers/mandy-td.md`.

I had no shell, so I could not run `git diff`. I checked the applied fixes in the source itself.

**Team:** td-generalist + chair, no full loop. Everything here is a RECOMMENDATION: Nick confirms the spec, the founder signs, Ops sends.

## 0. Verdict: SEND-WITH-FIXES (text only, in `pv_pack.py`; no stitch file changes)
- Rev M is gated: K1 is titled "answer before sampling", and Q1 says "answer this before digitizing or sewing". So nothing is sewn before Mandy answers.
- Make three edits to the pack text, add one line to the cover message, and have the founder answer one look question (star size). Then the pack can go tonight.
- None of the must-fix items needs a re-stitch. Re-run `pv_pack` only, once the running rebuild has finished.

## 1. Applied fixes: what the chair checked in the source or the rebuilt plan
| id | Holds? | Evidence |
|---|---|---|
| M1 | yes | Q4 is now "please choose one", (a) blocks or (b) floating, and the overhang list `OVER` is computed (`pv_pack.py` l.23-33, l.75). The chair checked this against the plan: FR-H1, FR-H2, PK, SR, SL, HR and HL overhang their piece, while BK-L and BK-R fit, so "most" is correct. **But K5 still says "if you can" → MF-2.** The gate lives in `pv_pack`, not `pv_art`, and it does not add the block margin (lesson row). |
| M2 | partly | Every cell except the back fits 400x450 without turning (plan cells: FR 317x365 / 300x291, PK 359x155, SR 289x376, SL 388x340, HR 225x93, HL 228x203). The back cells are 486 and 469 tall. **"The back becomes 3 hoopings" is a count nobody planned → MF-1.** |
| M4 | yes | Rebuilt plan: 01 bottom ≈ 245.7 and 03 top ≈ 270.7 (centre y 379.6, half-height 108.9), so the gap is 25.0 by size box. The K4 preview in `pages/` is still the old one (03 at y 371), so re-check it after the rebuild. |
| M5 | yes | `NUDGE_EDGE` is 20 and every drop now has a cause. The rebuilt plan has 2 drops, both "seam / edge keep-out", and FR now has 35 stars against 36 in the mockup. |
| M6 | yes (text) | K3 says "front half = -x on SR, +x on SL"; K5 says "NOT a mirror pair ... towards the front notch". The notch drawing waits for Mandy's DXF (post-Mandy). |
| M7, M8 | yes | Q6 asks for the pocket-opening finish width, whether the hood is lined, and the panel count. The K5 hood lines carry [proposed]. |

## 2. Evidence floor and rulings
- **(a) M3 star size is a founder look choice, not a TD blocker.**
  - The claim that the stars are "1.5-2x bigger" is a photo estimate taken off a mockup that is not to scale. By the rules a photo estimate can never drive a pattern number, and the generalist marked it that way.
  - The real TD risk is the smallest dots sinking after the wash. That is unverified: the "specks" were seen in a downscaled K5 preview, not in a `dstzoom` crop.
  - The proposed strike-off (Q5) would not test that risk. It is the back panel, which has the largest stars (BK mean 4.28 mm), while the smallest are on the sleeve (SR mean 3.65 mm, `plan.stars.per_panel`). → MF-3 adds the sleeve file to the strike-off at no new-file cost.
  - **Do not ask Mandy to sew a "1.5x" swatch by scaling our DST.** Scaling a DST changes its density (craft rule: re-digitise, never scale). If the founder wants a size option, we send a re-digitised star-swatch file as a follow-up before she sews.
  - The fastest settle costs nothing: print one sleeve and the front at 100% on paper tonight and hold them against a Come Over hoodie.
- **(b) M2 plan B is not needed before sending.**
  - Q1 blocks digitising and sewing until Mandy names the frame.
  - If the answer is 400x450, only the back changes, and that is a day of engine work with no lost round.
  - The wrong count in the pack text still has to go, because Q3 may be priced per hooping (MF-1).
- **(c) M10: nothing is misleading enough to block. Polish if the file is open anyway.**
  - "07" is the script's element id in the files (`pv_art.py` l.113-115). It is harmless, but Mandy may ask where 05 and 06 are.
  - The Korean text row on K4 has wide gaps (PDF text only). The badge drawing on the same page and the DST hold the real spacing, and K4 tells her to sew "exactly as in the files".
  - The "Self … Brushed on reverse side" line is copied word for word from the Hidden Inventory BOM, after the founder said on 27 Oct "use the same fabric as hidden inventory" (quoted in the `pv_pack.py` comment, l.61). Mandy made Hidden Inventory, so the line is consistent. Rev L's L2 looks closed by that choice; Nick should confirm the chat quote, because the chair did not open it.
  - Not in M10, found by the chair: the K5 rule says stars "moved up to 10 mm, or left out", but seam-keep stars now move up to 20 mm (`NUDGE_EDGE`), and the plan JSON records only `nudge_max_mm`. This changes nothing for Mandy, but it is a false statement about our own files (P-3).

## 3. MUST-FIX before sending tonight
- **MF-1 · `pv_pack.py` K1 Q1 (l.72)**
  - Replace `there the back becomes 3 hoopings.` with `there the back needs more hoopings: we will re-plan it for your frame and send the new count.`
  - Change `(table above); On a` to `(table above). On a`.
  - Why: the back is about 641 wide x 486 tall (`cells.BK`). On 400x450 that is 2, 3 or 4 hoopings, depending on whether the lowest back stars move up and where they sit. Nobody has planned it. A wrong count misprices Q3.
- **MF-2 · `pv_pack.py` K5 last rule (l.165)**
  - Replace `"Please hoop oversized rough-cut blocks and recut to the pattern after embroidery, if you can (question 4)."` with `"Most hoopings are bigger than the cut piece: blocks or floating, please choose in question 4."`
  - Why: it contradicts the required either/or in Q4, and it softens it.
- **MF-3 · `pv_pack.py` K1 Q5 (l.76)**
  - After `...before and after wash)?` insert: ` Please also sew file SR-H1 (right sleeve) on a scrap of the same fabric and wash it with the panel: it carries our smallest stars and dots.`
  - Why: covers the dot-survival risk from M3 with a file that already exists.
- **MF-4 · cover message from Ops (not in the pack)**
  - Add: "Please answer questions 1, 4 and 5 first; do not cut or sew the full sample until we confirm your answers and the star size."
  - Evidence: `suppliers/mandy-td.md`: "She often front-loads (cuts fabric before sign-off)". A full sample sewn before the star size is settled costs one round (her rounds take about 30-45 days door to door).

## 4. Rides with the send (questions or notes, not blockers)
- M9: add to Q3 `(c) the same, without the two hood hoopings (HR, HL)`. Do it now if Q3 is open anyway; otherwise put it in the cover message.
- M7 / M8: already in Q6. Mandy's answers re-place the pocket script and the hood stars before any sewing.
- M4 badge scale (keep the Rev J size or go to the mockup scale): founder look choice, the same paper print as the stars. The default (Rev J size, proven puff files) can be sent.
- P-1: K4 label `07 · Hem script` → `Hem script (file element 07)`.
- P-2: K4 Korean text row: render it with the badge font, or drop the row's extra spaces, so the printed string matches `kccore.TEXT["04"]`.
- P-3: the K5 nudge sentence, rendered from the plan (add `nudge_edge_mm` to `plan.stars`).

## 5. Post-sample / post-Mandy
- Re-plan for her frame (Q1) and her blocks/float answer (Q4).
- Draw the front notch on the sleeves from her DXF (M6).
- Make `KEEP_POCKET` per edge from her finish width (M7).
- Re-map the hood from her hood pattern (M8).
- Star size and DOT minimum, if the founder or the strike-off says so (M3): re-digitise with `kcstitch`, never scale.
- Labels, SPI and tolerances, and the Rev J reference pages (carried from Rev L).

## 6. Escalation decision
**No full loop.**
- The single high finding (M1) is sourced and fixed. M2 and M4 are verified by the chair against the rebuilt plan.
- M3 is a look choice plus an unverified risk that only a strike-off settles; specialist passes can't settle either.
- There was one pass, so there is no disagreement that changes the factory request.
- The generalist delivered the feasibility matrix.

## 7. ESCALATE
| Item | What settles it | Who |
|---|---|---|
| Star size (and badge scale) | A full-size paper print of one sleeve and the front, held on a Come Over hoodie: keep or go bigger | Founder (Nick checks) |
| Smallest dots surviving the wash | Strike-off photos of SR-H1 on a scrap, before and after the wash, daylight, ruler in shot | Mandy sews; Nick judges |
| Frame for the back (two hoopings or more) | Mandy's Q1 answer | Ops asks; engine re-plans |
| Blocks or floating | Mandy's Q4 answer | Ops asks |
| Fabric line = Hidden Inventory BOM | Nick confirms the founder's 27 Oct message | Nick |

## 8. What changes in the plan (product-lead)
- Make MF-1 to MF-3 in `pv_pack.py`, re-run `pv_pack` on the finished rebuild, and check the refreshed K4 (03 centre y ≈ 380) and the Q4 overhang list.
- Send with the MF-4 line in the cover message.
- Founder card tonight: the star-size question (the paper print).

## 9. not-checked
- The rebuilt PDF and pages (the rebuild was still running). The chair opened only the old K4 preview.
- The K1/K2/K3/K5/K6 previews this round.
- The mockup PNG, the DST files and any `dstzoom` crop (dots, script hairlines, puff edges, the BK-L CB split).
- `git diff` (no shell; the source was read instead).
- `mock3.py`.
- Sizes other than M.
- Media index: `not-checked: media index missing`.

## 10. Lessons (proposals for a techpack-engine session; the chair edits nothing)
| Correction | Route | Proposal |
|---|---|---|
| Pack text stated a hooping count no plan produced (MF-1) | craft rule → LESSONS row + red-then-green test | A gate: every hooping count in K1 prose must equal a count in a written plan variant. Red on Rev M Q1, green after the fix. |
| One rule's wording was updated on K1 but not on K5 (MF-2) | craft rule → LESSONS row + test | Render the blocks-or-float sentence from one constant used by both pages. |
| The strike-off covered the largest stars, not the smallest (MF-3) | family-wide → family.yaml key | `strike_off_must_include: smallest-unit file`; the pack picks it from `per_panel.mean_mm`. |
| The overhang gate checks bounding boxes, with no block margin | craft rule → test on the written plan | Check the frame against the piece outline plus `block_margin`, in `pv_art`, and print the list on K3. |
| Mandy cuts before sign-off | factory fact → `suppliers/mandy-td.md` | Already recorded. Ops' cover template should carry the "answer first, then sew" line for every gated pack. |

```json
{"signed_master": false, "rows": [
 {"id": "MF-1", "kind": "comment", "point": "back left hooping height exceeds the shorter listed frame; back hooping count on that frame not planned", "lens": "chair", "severity": "high", "page": "K1", "value": 486.0, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#cells.BK[0].h"},
 {"id": "MF-1", "kind": "comment", "point": "back right hooping height exceeds the shorter listed frame", "lens": "chair", "severity": "high", "page": "K1", "value": 469.4, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#cells.BK[1].h"},
 {"id": "MF-3", "kind": "comment", "point": "right sleeve carries the smallest mean star size, not covered by the back-panel strike-off", "lens": "chair", "severity": "medium", "page": "K5", "value": 3.65, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#stars.per_panel.SR.mean_mm"},
 {"id": "MF-3", "kind": "comment", "point": "back mean star size, the panel the strike-off tests", "lens": "chair", "severity": "medium", "page": "K5", "value": 4.28, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#stars.per_panel.BK.mean_mm"},
 {"id": "M4", "kind": "comment", "point": "Chinese capsule badge centre after the gap rule, from the neck point line", "lens": "chair", "severity": "low", "page": "K4", "value": 379.6, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#badges.03.placed_centre_mm[1]"},
 {"id": "M5", "kind": "comment", "point": "front hooping one bottom edge", "lens": "fit", "severity": "medium", "page": "K3", "value": 392.5, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#cells.FR[0].box[3]"},
 {"id": "M7", "kind": "comment", "point": "pocket script width", "lens": "make", "severity": "medium", "page": "K4", "value": 200.0, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#script.width_mm"},
 {"id": "M1", "kind": "comment", "point": "hood piece height versus frame", "lens": "make", "severity": "high", "page": "K3", "value": 390.0, "unit": "mm", "source": "file+cell", "ref": "out/pv/M/plan_allover.json#pieces_mm.HR[3]"}
]}
```
(The generalist's M3 row, front mean star size, was dropped: the rebuilt plan no longer holds that value. The current front value is in `stars.per_panel.FR.mean_mm`.)
