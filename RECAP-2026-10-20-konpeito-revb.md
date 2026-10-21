# RECAP 2026-10-20 — Konpeito jeans Rev B (tech pack, due tonight)

## What changed (founder review of Rev A, 15 items + coordinator overrides)
- T2/T4/T6/T8/G4: no back yoke, no knee seam (one-piece legs), 2-pc waistband joined at CB, "2 back patch pockets (sewn on the outside)", construction in plain words as HI.
- Wash: target described from the mockup pixels (mean ~#2B2A2A, highs ~#444343-#555353, where lighter/darker), factory to match the mockup (override: not "as HI"). MISSING box removed.
- 07 front leg: "artwork to follow [MISSING]"; licensed-lookalike notes removed. Star map re-derived (kjfront.py): scale from the front waistband (436.8 px = 420.4 mm), origin WB top at side seam, pocket opening traced. Root cause of "stars inside the pocket": the flat's scoop line was guessed ~60 mm too low; now traced. 0/14 stars inside the opening; stars moved up 5-12 mm; 07a/07b DSTs rebuilt (2,962 st / 17 trims; 810 st / 1 trim). New page C5 = overlay check with the maths.
- Labels: size LOOP labels recreated (kjlabels.py, Neue Metana ExtraBold outlined, 11 sizes, SVG+PDF 1:1 in zip labels/), shown on T7b; hang tag hangs from the size label; main label sewn on all 4 sides; main/care art = reference, new art [MISSING].
- BOM: one embroidery-threads line, method note on G1; packing + barcode lines [MISSING]. Patch 03 position confirmed. T1 legend plain. Flat-scale note removed.
- Size run = founder list 26-40 incl. 29/31/33 (24 dropped); T3 29/31/33 half-way PROPOSED.

## State
- Deliverables: projects/konpeito-jeans/out/HAKI_konpeito-jeans_TECHPACK_RevB.pdf (22 pages, 6.8 MB) + .zip; copied to C:/Users/devin/Desktop/konpeito-RevB/.
- Open questions (status board): size run, loop-label size, hammer loop.
- Left: untracked symlink named `*` at the worktree root (env.sh glob, ENGINE_NOTES 17) — the safety check blocked deleting it; not committed.
