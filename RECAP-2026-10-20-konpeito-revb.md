# RECAP 2026-10-20 — Konpeito jeans Rev B (tech pack, due tonight)

## What changed (founder review of Rev A, 15 items + coordinator overrides)
- T2/T4/T6/T8/G4: no back yoke, no knee seam (one-piece legs), 2-pc waistband joined at CB, "2 back patch pockets" (no explanation, founder later), construction in plain words as HI.
- Wash: target described from the mockup pixels (mean ~#2B2A2A, highs ~#444343-#555353, where lighter/darker), factory to match the mockup (override: not "as HI"). MISSING box removed.
- 07 front leg: "artwork to follow [MISSING]"; licensed-lookalike notes removed. Star map re-derived (kjfront.py): scale from the front waistband (436.8 px = 420.4 mm), origin WB top at side seam, pocket opening traced. Root cause of "stars inside the pocket": the flat's scoop line was guessed ~60 mm too low; now traced. 0/14 stars inside the opening; stars moved up 5-12 mm; 07a/07b DSTs rebuilt (2,962 st / 17 trims; 810 st / 1 trim). New page C5 = overlay check with the maths.
- Labels: size LOOP labels recreated (kjlabels.py, Neue Metana ExtraBold outlined, 11 sizes, SVG+PDF 1:1 in zip labels/), shown on T7b; hang tag hangs from the size label; main label sewn on all 4 sides; main/care art = reference, new art [MISSING].
- BOM: one embroidery-threads line, method note on G1; packing + barcode lines [MISSING]. Patch 03 position confirmed. T1 legend plain. Flat-scale note removed.
- Size run = founder list 26-40 incl. 29/31/33 (24 dropped); T3 29/31/33 half-way PROPOSED.

## State
- Deliverables: projects/konpeito-jeans/out/HAKI_konpeito-jeans_TECHPACK_RevB.pdf (22 pages, 6.8 MB) + .zip; copied to C:/Users/devin/Desktop/konpeito-RevB/.
- Open questions (status board): size run, loop-label size, hammer loop.
- Left: untracked symlink named `*` at the worktree root (env.sh glob, ENGINE_NOTES 17) — the safety check blocked deleting it; not committed.

## Rev B2 (20 Oct, evening) — PR #29 review (7 should-fix) + founder changes
- Every konpeito = the 02 facing konpeito (kjsvg.konpeito_regions: front-row candy of HAKI_facing_konpeito_ART.svg, 10 mm,
  same digitising as 02, white specks thread added) on 04/05/06/07a/07b. 05/06: 462 st, 8 trims; 04: 1,784 / 25; 07a 5,095 / 104; 07b 1,390 / 24.
- A14 per konpeito (kjsvg.candy_masks + kjcompare.candy_gate): 01 = 3 rows, 02 = 9 rows, 04-07 = 18 rows, all pass. Red test:
  the old 5-point star PASSED IoU 0.85 vs the konpeito DST, so an outline gate (p90 <= 0.7 mm) was added (star 1.3-1.5, konpeito 0.3).
  New compare sheet + page C6.
- Size labels: the 15 x 60 strips are withdrawn; HI centrefold label 30 x 10 mm with our waist numbers (kjlabels, T7b, zip labels/).
- F1: chenille + quote basis + price clause removed, size-32 strike-off (project-side filter, ENGINE_NOTES 18).
- C3 cuts on blank rows above the footer; T2 2nd front loop visible + light seams/topstitch; G3 white = bead dots (PASS); gates_log removed.
- Deliverables: out/HAKI_konpeito-jeans_TECHPACK_RevB2.pdf (23 pages) + .zip, copied to Desktop/konpeito-RevB (Rev B files replaced).
- PR #29 was merged by the founder before this round; Rev B2 goes in a new PR.

## Rev B3 (20 Oct, late) — PR #30 review (4 should-fix + nits); PR #30 was already merged -> branch tp-konpeito-jeans-b3, new PR
- Item 1 (L/R): NOT a defect — on a back view the viewer stands behind, image right = wearer's right; the mockup has 03 + pink
  konpeito on the image right = wearer's right, as written. Added explicit orientation notes (T2, T8, G4, G5, G6) instead of flipping.
- Item 2: border flowers (18 / 20) + border dots (20 / 20) gated per motif from SVG layer 03; band / field / edge A15 areas. All pass.
- Item 3: 04-07 position vs independent centres (max 0.05 mm) + A15 per file (100 %, 0 blobs); C6 + G pages show it.
- Item 4: tests/test_konpeito_gates.py (4 tests), proven red by source mutation.
- Nits: legacy puffy_star / candy2 deleted from kjart (border_flower, kjart.spill marked LEGACY); G6/T8 "moved N mm" computed.
