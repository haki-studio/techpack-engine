---
name: techpack-pipeline
description: End-to-end garment tech pack from mockups + a fit chart — embroidery art, DST/PES stitch files, hoop splits, graded pattern (DXF), garment pages — using the techpack-engine repo. Use for any new Haki garment with embroidery.
---

# Tech pack pipeline (techpack-engine)

Read `LESSONS.md` first. Work in `projects/<style>/` with `source scripts/env.sh projects/<style>`.

## 0. Intake (first reply)
Inventory: garment, fit chart (POM, half-measures!), fabric + hardware, every embroidery/print/trim element with
its pattern piece, process and keep-outs. List what's PROPOSED. Ask only what blocks (usually: fit chart, frame size
at the factory, number of needles).

## 1. Block + pattern
Fill the POM chart into the block; draft all pieces; run `pattern_out.py qa` — every POM within tolerance, seam walks
equal, cap ease 10–15 mm, rib ratios sane. Render the pieces and look at them (neck curves scoop inward, cuff widths).

## 2. Art
Reuse library motifs; author new ones with a render-compare loop against the mockup crop (ROADMAP §2). Compose on
the size-M block with keep-outs (LESSONS A3). Wrap-around art: split per piece with match marks (A4).
Check against the mockup side by side; density matched (A2); nothing floating (A1).

## 3. Stitch files
`clean_vis` → `merge_colours` (≤ 15 threads) → stops → `merge_stops` → `make_pattern` → write DST + PES → verify.
Fronts: one file per art grade. Wrap pieces: one file per size (A5). Back > frame: `split_clip` + basting crosses.
Gates: max stitch ≤ 7.5, trims from DST read-back, stitch count + run time recorded, every preview looked at.

## 4. Placement per size
`emb_place.clearances()` for all sizes — all keep-outs pass, wrap marks aligned.

## 5. Documents
Element specs → embroidery pack (G1–G5) → garment pack (T1–T16) → merge → `shrink.py` → zip with README.
Every number comes from files. Render every page and look at it.

## Parallelism
Independent: art per element, stitch files per element/grade/size, pattern outputs, page builds. Run them as
parallel background jobs / subagents; keep one coordinator that runs the gates and assembles the pack.

## Report back
One line per deliverable; the before/after numbers that matter (stitches, trims, threads, stops, keep-out table);
what's PROPOSED; what needs a sew-out.
