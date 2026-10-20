# Wave jacket — Rev B fix round (embroidery sampling, size M) — 20 Oct 2026

Branch `tp-wave-jacket`, worker session a9455991. Goal: close REVIEW_OPEN.md (14 items) and deliver the size-M
embroidery sampling package for Mandy tonight.

## What changed and why
- **Seam tone handover + continuous stripe bands** (`tonematch.py`, runs on `art_M.pkl`, backup `art_M_pretone.pkl`):
  1. stripe patches < 150 mm² merged into the band they share most outline with (81 % of WV regions were render-shading
     patches) -> one continuous cord per stripe (review 5);
  2. bare pockets inside the art filled (grey hollows became thin ridges in Rev B and left navy specks; review 4);
  3. per seam the leader keeps its threads, follower stripes take the leader's thread, whole regions (review 2 + 3).
- **Foam = padded lockstitch in every file; chenille = path plan** (`chenille.py`, `build_size.py`): Rev B shipped
  `_CHENILLE.dst` files although factory.json has no `chenille_format` (LESSONS B33) and the paths were arc-length
  resampled (B32). Now `chenille_plan/*.json + preview` (engine `spiral_paths` + `resample_const`).
- **gates.py**: WIP patch re-applied by hand on top of the engine's `qa.visible_segments` (the patch's own copy is
  superseded); direction gate runs on the 4 ppm reference resampled to 12 ppm (A17 guard) and is reported as INDICATIVE
  (source render ~0.7 px/mm), with a stripes / foam / drops breakdown.
- Docs: G1 collar preview (review 13), G5 fit uses the factory's confirmed 340 × 505 front hooping (was "CHECK"), spec run
  time summed over hoopings (= G4), F1 says full files are reference only (14), chenille wording everywhere.

## Decisions
- Founder (19-20 Oct): collar not hood; seamless wrap across armhole / sides / zip; fabric colour unknown -> threads stay
  PROPOSED and the pack says so.
- Whole-region recolour only: a tone step inside a stripe would be a new cut line (founder hated the Rev B cut lines).

## Final state (size M, read back from the DSTs)
| piece | stitches | trims | stops | hoopings |
|---|---|---|---|---|
| BK | 294,624 | 1,016 | 13 | 2 (S1 157,597 / S2 138,127) |
| FR | 116,468 | 438 | 11 | 1 |
| FL | 186,352 | 838 | 17 | 1 |
| SR | 208,368 | 655 | 11 | 2 (99,844 / 108,381) |
| SL | 141,483 | 540 | 17 | 2 (17,145 / 124,515) |
Total 947,295 st, 3,487 trims, 8 hoopings, 9 threads per file, max stitch 7.41. Foam swatch 100,880 st / 749 trims.
Pack 16 pages (G1-G9, 01 spec 6 pp, F1); copies in C:/Users/devin/Desktop/wave-RevB/. Tests 274 passed.

## Pending / next
- Open gates (G8): A14 39 failing motif rows (mostly spray drops at IoU 0.6-0.7) + 18 unexplained bare areas; A16
  direction indicative only (render 0.7 px/mm). Sleeve centre / seams tone partial (DST continuity 45-92 %).
- Factory answers needed: chenille machine + format, sleeve in one hooping, thread book; founder: shell colour.
- Not mine, left untouched in the worktree: `scripts/dispatch.sh` edit and a `*` symlink at the repo root.
