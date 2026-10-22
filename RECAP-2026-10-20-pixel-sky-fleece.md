# RECAP 2026-10-20 — Pixel Sky fleece tech pack (builder, branch tp-pixel-sky-fleece)

## Decisions
- Block: `projects/pixel-sky-fleece/fleece.py` = Drum Island (pattern.draft) on a swapped chart with pile ease
  (B +2, C +1, E +1, F +1, G +2, J +1 cm; D = chest because the hem is bound, not ribbed). Engine untouched (chart swap
  inside a context manager). Pattern QA passes XS–3XL (chart, seam walks, shape checks).
- Mockup scale: S = 0.601 mm/px from CF neck seam (y 368) → hem edge (y 1308) = A − K = 565 mm. The render is slimmer
  than the block (shoulder ~46 vs 53 cm): art keeps mockup sizes / heights; hidden body sides are generated.
- The AI render's pixel grid is NOT regular (edge-phase concentration ~0.2), so the jacquard is redrawn on our own grid.

## State
- inventory, pattern stages done + committed.
- In progress: jacquard cell maps (fronts, sleeves, back) + sparkle / bird embroidery.

## Next
1. jacquard grid per panel + mill files; 2. sparkle + bird SVG → digitize.svgrun → DST/PES + gates;
3. pages (J, G, F1, T) → merged PDF + zip; 4. PR + review dispatch.

## Progress (update 2)
- `pixels.py` colour classes + garment-detail masks (zip, pockets, bindings, collar; background = border-connected bright).
- `jacquard.py`: 2.5 mm cells, clouds traced on a 5 mm grid (global phase 1.25/1.25, purity 0.93), detail cells filled
  by 2-D neighbour majority (FILLED), hidden sides reflected (GENERATED), back = front mirrored (GENERATED), sleeves via
  `mockmap.sleeve_to_img` (back half mirrored). `python3 jacquard.py M` ~22 s. `jq_view.py` draws maps back into the mockup.
- `emb_art.py`: 20 sparkles traced (E1 F02 6, E2 F01 10, E3 S02 4) on own 1.8 mm staircase grids; bird = jacquard cells
  (E1B = bird + E1 sparkles, option B). SVG per file in out/art; `bench/run_E*.yaml` -> digitize.svgrun (sherpa_fill
  kind: tatami 0 deg, 0.40, pull 0.30). E1/E3 all gates pass; E2/E1B exposed-stitch + E1B tiny bird islands (fixed by
  widening the bird sample box to x -20) -> rerun with exact_travel max_ex 0.2.
- Gotcha: `cat > file` with no heredoc blocks forever in a backgrounded Bash call (lost 10 min).

## Delivered (update 3)
- 17-page pack `projects/pixel-sky-fleece/out/HAKI_HK-FL-PIXSKY_TECHPACK_RevA_small.pdf` (2.9 MB) + zip (9.7 MB):
  T1–T5 garment, J1–J3 jacquard, G1–G5 embroidery, F1/F2 factory + mill, Q1 questions, R1 LESSONS checks.
- Stitch (DST read-back): E1 1,037 st / 19 trims; E2 3,782 / 36; E3 1,971 / 17; E1B 7,867 / 69. All A14 motif gates pass
  vs render pixels; keep-outs XS–3XL pass; pattern QA all sizes; 274 tests pass.
- Gate decision: exposed-stitch halo 0.35 for sherpa pull comp 0.30 (svgrun's 0.25 flags pull-comp corners; proven by
  re-running at pull 0.20 → 0). svgrun `gates.exposed` override crashes → ENGINE_NOTES 1.
- Open (founder/factory): fit choice, back design, mill capability + 3rd colour, bird IP, bird side (brief vs mockup),
  embroidery-on-sherpa set-up, trim colours.

## Fix round 1 (PR #28 review: 1 blocker + 3 should-fix) — Rev B
| Review item | Fix |
|---|---|
| BLOCKER R1 PASS for gates never run | `gates_fl.py` now runs qa.uncovered (A15), qa.angle_coherence on visible stitches per part (A16), chaos half of qa.direction_match (A16/A17; "vs reference" NOT RUN, no close-up), plus a colour row per motif. R1 + G pages + compare sheets read gates_fl.json. `gates_selftest.py` proves each guard goes red on a planted defect. |
| E2 gold sparkle sewn yellow | colour from core pixels (blue<110, red>195, g/r<0.93 = gold); E2 now 4 gold / 6 yellow; colour gate added |
| Small sparkles simplified, wing pair merged | touching pair split by core colour (+1 px opening); sparkles < 16 mm drawn as the family's sparkle fitted with a blur model (`star_fit.py`); 21 sparkles (E1 7, E2 10, E3 4) |
| Jacquard simplified | trace per 2.5 mm cell (band 91.8 → 94.4 %, sleeves 97.7 %), mirror-fill under zip/pockets (no stripes), sky under sparkle rims, view slivers fixed, J3 diff map + list |
Dead end: IoU-based fits (hard or soft) on the blurred render always prefer blobs/diamonds; only comparing blurred-candidate vs render (forward model) recovers 4-arm shapes.
Open: wingtip sparkle above the bird still comes out a diamond (render too blurred); founder items unchanged (bird IP, bird side, back design).

## Fix round 2 (PR #28 round-2 review: 3 should-fix) — Rev C
| Review item | Fix |
|---|---|
| Big sparkles drawn as stepped diamonds | `star_fit.fit_tiers`: each sparkle = 1-3 concentric D4 crosses fitted by the blur forward model (coordinate descent, fewest tiers within 0.004 rmse; big ones may free edges when rmse drops >= 10 %; edges snapped < 1.25 mm; arms w <= 0.5 L and stick out >= 25 %). Small (< 16 mm) = one tier = plain plus. Replaces the 2.5 mm staircase + resampled exemplar. |
| Jacquard checker = scattered specks | `jacquard.checker_px`: windowed 2-D checker filter on blueness (8-12 px squares) -> checker areas; `regularise_checker`: regular lattice of q cells (q=3 by agreement), phase per cell (+-2 squares) majority-smoothed. |
| closeup_request.md missing | written (7 prompts + optional back), Q1 question added via status_set. |
| Minor | R1: distinct motifs = 22 (E1B repeats E1), process rows print DONE not PASS, D2 reads the small PDF size; Rev C. |
Dead ends: a uniform coarse grid (2.5-9 mm) for the big sprites - the fine cell always wins on rmse (render unit drifts); free-edge fits on small sparkles overfit into lopsided shapes; label-based checker detection fails (squares joined at corners by anti-aliasing).
Repo root has a stray symlink `*` -> `inputs/*` (made by `source scripts/env.sh .`); safety check blocked removing it - not committed.

## Fix round 3 (PR #28 round-3 review: 4 should-fix + 1 nit) — Rev D
| Review item | Fix |
|---|---|
| Stray cream specks in the sky around sparkles (F01, mirrored to B01) | Root cause: the sparkle rim alternates cream/blue, so the checker filter regularised it into lattice cells. Sparkle/bird footprint (pixels dilated 9 px; bird = largest black component, not zip tape) is never checker and its cream islands go sky (`foot`, `sky_rims`). |
| <=2-cell fragments in generated areas; sleeve "butterfly" | `despeckle` in `raster_panel` (islands <= 4 cells, bird protected). Sleeves: hidden half = traced half mirrored about the centre line (Rev C used sleeve_to_img samples, unregularised); hidden strips of the traced half mirrored about ONE fixed column (A_IN/A_OUT, >= 80 % coverage) - per-row axes caused the shear. Checker squares snapped to whole squares (418 cells completed, 601 dropped). Gate `gates_jq.py`: 0 islands in 42 maps, 2/2 planted caught; R1 row J-isl, J3 text. |
| 41 MB scratch in work/ | `git rm --cached`, `projects/pixel-sky-fleece/.gitignore` = work/ (history keeps it; squash merge drops it). |
| G4 small/unreadable | compare_E3 landscape (mockup + preview left, 2x2 zooms + one-column gate table right). |
| Nit E1 45x59 vs 45x60 | placement line reads the DST size (gates_fl.json) like the G1 table. |
Numbers: band agreement 92.2 % (Rev C 92.4), front 96.8 %, sleeves 94.5 %. Stitch files unchanged (E1 1,019 / E2 3,729 / E3 1,953 / E1B 7,872). 274 tests pass. ENGINE_NOTES 11.
Dead end: 2-D majority growth for the sleeve's centre gap -> horizontal stripes (same failure as row-nearest fill).

## Fix round 4 (2026-10-21, PR #28, pack Rev E)
- Reviewer round 3: only one item left, should-fix: G4 (E3) not legible. Cause: the landscape sheet had an aspect of 1.5, but the G-page box is 273 × 104 mm (aspect 2.6), so the sheet was height-limited at about 0.05 mm/px and its 22 px text printed at about 3 pt.
- Fix in `compare.py`: the E3 sheet is now 3566 × 1112 px.
  - Mockup and preview share one lower scale (about 9.7 px/mm).
  - The mockup is cropped to the sparkle run.
  - The 4 zooms sit in one row at 560 px.
  - The DST line and the gate table use 30 px text, which prints at about 2.3 mm. That is larger than G5's.
- Stitch files and gates are unchanged. Rev E small PDF: 17 pages, 3.3 MB. Zip: 12.0 MB.
- pytest has to run in the `scripts/env.sh` venv (`~/.venvs/techpack-grand-line`); system python3 has no shapely, which explains the reviewer's 20 collection errors.

## Rev F (2026-10-21) — founder answers, one rebuild on PR #28
| Answer | Change |
|---|---|
| Fit CONFIRMED (Drum Island + pile ease, bound hem) | T3 ease rows black "confirmed 21 Oct"; fit sample line red/mandatory; cover Block row black |
| Back CONFIRMED (band continued, no motif) | cover/T2 back labels + J1/J3 GENERATED text black |
| Mill + factory OPEN | F2 unchanged; still on Q1 |
| Bird IP CLEARED | R1 A7 DONE; G5 note; question closed |
| Collar outer SKY BLUE matched to the sherpa (taslan kept) | fleece.py C01 material, T2 note 1, T5 BOM, F2 trims, flats collar colour = JQ.COL[0]; new Q1 line "taslan or the sky sherpa itself? [proposed: taslan]" |
| Bird position = wearer's RIGHT | brief wording fixed; Q1 assumption removed |
| Close-ups NOT NEEDED | Q1 + R1 A10 + J3 text; closeup_request.md kept with a "NOT NEEDED" header |
STATUS.json now has `answered` (closed questions with the answer + date); Q1 prints them in green under "ANSWERED". Binding/tape navy + zips stay PROPOSED.

## Rev G (2026-10-22): the "RFQ edition" for the new low-MOQ factory from Texworld
The founder wants to send this pack as an RFQ to a different factory (one that can knit colours into sherpa). His words: "doesn't need to be perfect, but good enough to send". Rev G folds in the lead's brief, two lead TASKs, td-generalist's PS-01..26 and the TD chair's merged sheet (`projects/pixel-sky-fleece/td/`: B1–B14 from files, N1–N7 as placeholders).

**Two PDFs from one build** (`pack.py`, mode `rfq` / `internal`):
- `HAKI_HK-FL-PIXSKY_RFQ_RevG.pdf`, 20 pages, for the factory: T1 cover ("Prepared for: ____"), Q1 quote sheet, T2–T7, J1–J3, G1–G5, F1, F2–F3 (the chair's 28 questions word for word), Q2 open points.
- `..._TECHPACK_RevG.pdf`, 22 pages, internal: the same pages, but with the full J3 and G pages, plus Q3 (decisions log and the chair's section (c) holds) and R1.
- `rfq_text_gate`: a regex list scanned over the rendered RFQ PDF text (factory.json, gates, IoU, founder, Rev A–F, .py/.json, Drum Island, IP, PS-ids …).
  - The build fails on any hit in the RFQ copy.
  - It also fails if the same scan finds nothing in the internal copy, which proves the gate is not blind. First run: 154 internal hits, 0 in the RFQ copy.
  - Result goes to `out/rfq_text_gate.json` and to an R1 row. LESSONS E14 and ENGINE_NOTES 12 propose moving it into the engine.

**What changed, and why**

| Item | Change |
|---|---|
| Old factory content (PS-01) | The engine's F1 (`factory.requests_page`) prints the old factory's frames as "confirmed" and says "washed, as in bulk", and the engine is off-limits to this session. So F1 is now written in the project: strike-off, a wash test, threads ("your nearest match"). Frames and colours per file are now questions (q11). |
| RFQ basics (PS-06) | Q1 quote sheet: knit-down / fit sample / strike-off / proto prices and days; bulk FOB at 100/200/300/500 for options A and B; the lead's blanks for MOQ, 3rd-colour MOQ, sample and bulk lead times and CNY dates. **Our 21/45-day targets are not printed.** |
| Fabric + colour (PS-07/09, N1/N2) | Shell "please state" goes to q4. Pile "~8-10 mm" is taken from the fleece.py docstring and marked proposed. T5 colour standard: hex + "TCX: ____", plus the line "both fabrics dipped to the same TCX in parallel". |
| Seams + neck (PS-10/11) | New T7: per-seam stitch type / finish / "SPI: factory to state", plus the assembly order. New piece **NT1 neck tape** in fleece.py: length = neck seam (49.7 cm at M), with a seam walk. It carries the main and size labels and the hanger loop P04. |
| Labels + packing (PS-12, N6) | New T6, with `fflat.labels_key()` back-view markers. Care/content text is all placeholders ("[mill to state]"), because fleece.py states no fibre. The brand is written "Haki Studios". |
| Measuring (PS-14) | `fflat.measure_key()` puts the POM letters on the M front flat. Rule: measure at the base of the pile. New H2 "stretched": TBD at the fit sample. Binding tolerance Q changed in fleece.py from ±0.1 to ±0.3 [proposed]. |
| G1 (PS-15) | The E3 line now gives both the underarm origin and the grading rule (kept from the cuff seam: 323.7 mm at M), plus "per-size positions = DXF layer-8 marks". |
| Pocket bag (PS-21) | fleece.py and T2 now say the same thing: "sewn to the zip tape round the opening, free-hanging [proposed]; factory to advise CF facing or side seam". **This deviates from chair B11** ("top bar-tacked to the CF facing"): the bag sits about 20 cm from CF, so it cannot reach the facing. The lead accepted this. |
| Chin guard (N7) | Asked as q19 only; not designed in (chair over the lead's earlier "optional detail"). |
| STATUS.json (B14) | The collar question is moved to `answered`. The open questions are re-worded for the new factory and for the N1–N6 owners. |
| J1 stale line | "clouds drawn in 2 × 2 blocks (2.5 mm)" dated from Rev A. It now reads "drawn per cell; checker lattice 3 × 3 cells (7.5 mm)". |

**Other outputs:** `out/TBD_RevG.md` + `.png` (`tbd.py`) with three groups: decided by us, with the factory, at sampling (incl. the sleeve-backs line and the chair's holds). The supplier zip has no json and no QA sheets (compare previews are the `*_rfq.png` versions), and its README is clean.

**Pending:** the founder fills in "Prepared for"; Nick picks the TCX colours, ladder and size ratio; Ops sets the reply-by date and terms. Engine follow-ups are in ENGINE_NOTES 12 (requests_page new-factory mode + wash parameter; supplier-copy gate as an engine test).
