# S1 SVG drop-in: parity with the hand-configured M5 runs (22 Oct 2026)

`scripts/svg2dst.py` with **no run.yaml**: `--fabric twill --hoop 300x300`, width = the art's own width.
M5 = the hand-written `bench/run_*_svg.yaml` runs. Previews: `bench/s1/<case>_panel.png` (art | stitches),
`<case>_preview.png` for the three unseen files, `logo_crescent_crop.png`.

Reproduce one case (≈5-35 s each, no API calls):

    ~/.venvs/techpack/bin/python scripts/svg2dst.py --svg projects/konpeito-jeans/svg/HAKI_coin-pocket_konpeito_ART.svg \
        --width-mm 76 --fabric twill --hoop 300x300 --out /tmp/s1/coin --name coin

| case | width mm | M5 hand: st / trims / stops, gates | S1: st / trims / stops | hard gates | centreline (per shape) | motifs | fills | open questions | profiled strokes |
|---|---|---|---|---|---|---|---|---|---|
| wb waistband | 80 | 15,069 / 161 / 10, 7/7 | 15,136 / 161 / 10 | 8/8 | 6/6 | 76/76 | coherent | 2 (patch, 60wt black) | 0 |
| coin | 76 | 10,525 / 84 / 11, 7/7 | 10,597 / 88 / 11 | 8/8 | 6/6 | 46/46 | coherent | 1 | 0 |
| spill (facing) | 63.17 | 3,609 / 58 / 7, 7/7 | 3,608 / 58 / 7 | 8/8 | - | 9/9 | - | 0 | 0 |
| starP + starY | 24.23 (one file) | 281+281 / 1+1 / 2+2, 7/7 each | 562 / 1 / 4 | 8/8 | - | 4/4 | - | 4 (star vs petals; default radial) | 0 |
| logo (unseen) | 90 | - | 4,797 / 3 / 4 | 8/8 | 3/3 | 1/1 | coherent | 0 | 1 (the crescent) |
| lettering (unseen) | 100 | - | 1,908 / 32 / 1 | 8/8 | 11/11 | - | - | 0 | 0 |
| illustration (unseen) | 120 | - | 16,507 / 20 / 8 | 8/8 | 5/5 | 4/4 | coherent | 1 (60wt) | 0 |

Hard gates: engine_real, art_read >= 0.98, fits_hoop, threads <= needles, max stitch <= 7.5 mm, has stitches,
exposed_none, uncovered_none. Soft: centreline, motifs, fill coherence, questions answered.

## What changed in this pass (and why the table moved)
- **Logo crescent** (found by looking): it was sewn at one column width and passed because the `[lines]` centreline
  row pooled it with the ring. The S1 centreline gate is now **one row per source shape** (every other shape's art cut
  out of its window), and a tapered reference also has its thick end gated (ratio90). Crescent now: ratio 0.88,
  ratio90 0.89, sewn on a width profile (`extract/svg.py::_taper`). At d0ae3ca the same test sees 1 pooled row.
- Per-shape rows also showed the logo's bottom bar sewn at the ring's width (same colour, they cross): S1 strokes are
  now columns **per source element** at the element's length-weighted median width (coin glyph ぺ would otherwise be
  out-voted by its 0.9 mm ticks and sewn at 0.85 mm, ratio 0.57).
- The 4 Konpeito cases are unchanged from the earlier S1 run except the coin (10,597 = the number the handoff recorded).

## Lettering follow-up (22 Oct, branch engine-s1-lettering): 8/11 -> 11/11
- **i stems + dots (0.80-0.82) were a GATE artefact**: the read-back of a 2.5 mm satin has a zig-zag edge whose skeleton
  spurs (~ half the width) survived the fixed 0.6 mm prune and pulled the median width down. The S1 per-shape row now
  prunes spurs at 0.6 x the shape's own median width: i rows 1.00. The i was sewn right (looked at: only the square
  corners round off).
- **the a bowl (ratio90 0.73) was a real defect**: the whole glyph was sewn at one width (1.5 mm) while its bowl swells to
  2.55 mm. S1 now sews each stroke of a glyph at its own skeleton width: ratio90 0.80, **on the +-0.20 limit** (passes;
  the bowl's taper inside a multi-stroke glyph is still one width per stroke).
- The Konpeito cases are unchanged (same stitch / trim / stop counts).

## Earlier open findings (resolved above)
- **lettering fixture (DejaVu Sans Bold "Haki Studios")**: 3 of 11 shapes miss the per-shape centreline row: both
  `i`s (stem + dot sewn at 0.80-0.82 of the art width) and the `a` bowl's thick end (ratio90 0.73). The old pooled row
  hid all three. Not tuned further tonight; candidates: weight the `i` dot separately from the stem; profile the
  tapered bowl of a multi-stroke glyph (the current detector only profiles a shape that is one open stroke, LESSONS A35).
- The joins of the bold lettering (a, S) read ragged in the preview: pre-existing, same stitch count as before this pass.
