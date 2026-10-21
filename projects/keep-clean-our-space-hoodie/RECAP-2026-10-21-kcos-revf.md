# KCOS hoodie — Rev F (PR #31 fix round 2), 21 Oct 2026

## Why
Reviewer on 02c2a4b (Rev E): BLOCKER — the A14 gate FAILED on the JP top star (IoU 0.70 read back from the size-M DST);
the fix comment had quoted the scene fit (0.73), which is not the gate. SHOULD-FIX — the pack build carried on with
BLOCKING 1; stale "Rev D" labels on the Rev E pack. NOTE — star constants belong in ENGINE_NOTES.

## What changed
- **Top JP star re-traced** (scene.py `_top_star`). Measured on a 32 px/mm mockup crop: the white glint is a STREAK through
  the centre into the upper-left notch (+ short lower-right tail), not a white arm facet, and the pale ring is thin.
  All five arms gold (k 0.34, sharp tips), dark pit r 0.6 in a 0.9 mm white ring, glint streaks (-132°, 4.4 mm, 1.0 w;
  48°, 2.9 mm, 0.8 w). Fit scored on the yellow-family threads only (`best_star(cols=)`), same as the gate.
- Ring = two half-arcs meeting at the glint roots: one closed ring forced a 1.5 mm white travel stitch across the pit
  (found on the DST); now 0 stitches cross the pit.
- **Gate stops the build**: gates.py exits 3 on blocking > 0 (prints the failing rows); build_all.py stops with a message
  and asserts gates.json blocking == 0. Red/green proven (iou_min forced 0.95 → 11 FAIL, exit 3; real run exit 0).
- Labels: Rev F bump (kccore), T9 history row Rev F, stale "Rev D" captions on S1 / G1 note / E03 / E04 / R1 removed.
- ENGINE_NOTES 25 (gate-or-die for every pack), 26 (ringed/glinted star motif, constants listed).

## Result
Gate on the shipped M DST: 01 yellow motif 1 IoU 0.74 (h 0.83), state ok; BLOCKING 0. Numbers: see PR comment.

## Open (founder, unchanged)
Back + hood MISSING; star haze look; puff 2.5 mm rule + flat parts; CN weight 800.

## Rev G — fix round PR #38 (21 Oct 2026)
- Review: 1 should-fix (G1 cover caption showed 污 as a tofu box), 2 LOW notes, 4 founder items unchanged.
- Root cause: no CJK font installed on the box; `sheet.t()` asks for Noto Sans CJK JP and cairosvg falls back to a Latin font. The caption now goes through `kcdoc.auto` (CJK runs as font outlines).
- New `tofu.py` guard: every G/E/S/R/F/T page is checked before svg2pdf; any CJK in a plain `<text>` stops the build. Proven red (raises on the old caption) then green.
- ENGINE_NOTES 26 (cont.): the star constants are one-star tuning. ENGINE_NOTES 27: route CJK in `sheet.t()` + a guard in `sheet.doc()`.
- Stitch files unchanged from Rev F; REV → Rev G for the documents, compare sheets and zip.
