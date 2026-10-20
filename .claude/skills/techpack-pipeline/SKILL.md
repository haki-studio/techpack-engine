---
name: techpack-pipeline
description: End-to-end garment tech pack from mockups + a fit chart — embroidery art, DST/PES stitch files, hoop splits, graded pattern (DXF), garment pages — using the techpack-engine repo. Use for any new Haki garment with embroidery.
---

# Tech pack pipeline (techpack-engine)

Read `LESSONS.md` first. Work in `projects/<style>/` with `source scripts/env.sh projects/<style>`.

**Fidelity first (founder rule, 2026-10-16).** Rev A/B of every design matches the mockup detail for detail, as close as
embroidery can physically sew — push the limit, don't optimise early. Stitch count, density, trims, stops and run time are
REPORTED, not limits, until a strike-off says what to clean up. Hard limits only: keep-outs, max stitch < 7.5 mm, ≤ 12
threads per file (manufacturer, factory.json — basting included), licensed areas empty, every number read from the files, an honest spec. Cleanup (density, trims, stop
merges, simplification) is a separate, later pass — never trade away a visible mockup detail to save stitches.

## 0. Intake (first reply)
Inventory: garment, fit chart (POM, half-measures!), fabric + hardware, every embroidery/print/trim element with
its pattern piece, process and keep-outs. List what's PROPOSED. Ask only what blocks (usually: fit chart, frame size
at the factory, number of needles).
**Ask for the founder's vector art first** (true-size SVG in mm, one layer per thread, layers in stitch order): with it
the parts engine digitises straight from the file (`digitize.run <run.yaml with source: svg>`, ENGINE_PLAN M5,
`projects/konpeito-jeans/bench/run_*_svg.yaml`) and the mockups are placement / colour reference only. Konpeito: the
lettering gates went from "pass after a lot of fitting" to a mean centreline distance of 0.05-0.14 mm on every string.

## 0b. Low-resolution sources (the normal case)
There are usually no originals: the mockup is an AI render ~1–1.5k px for the whole garment (≈1 px per mm of art).
A bigger frame does NOT help — frame size decides hoopings, not detail. What does:
1. **Close-ups from the same image tool** — one prompt per decorated panel, saved as `inputs/closeup_request.md`:
   > "Same jacket and embroidery as the attached image. A straight-on, flat, evenly lit close-up of ONLY the
   > <element> embroidery on the <piece>, filling the whole frame edge to edge, no perspective, no folds, no model,
   > highest resolution available (≥ 3000 px wide). Keep every motif, colour and position exactly as in the original;
   > do not add or remove anything."
   Close-ups are the tracing reference when they exist; the full mockup stays the reference for placement and scale
   (the generator may drift — compare motif positions and reject a close-up that moved things).
2. **Count, don't trace** (A2): count motifs per area (leaves, blossoms, stars, cloud lobes) on the mockup and match
   the count in the art; detail comes from the motif library at stitch resolution, not from mockup pixels.
3. **Upscaling** (Lanczos ×4 + light sharpening) only for reading shapes and colour boundaries — it adds no detail; never
   claim traced accuracy from an upscale.
4. Say on the spec page which reference the art came from (mockup / close-up) so the factory knows what was redrawn.

## 0c. Factory profile
Read `factory.json` (repo root) via `factory.load()`: frames (`factory.largest_frame()` → `split_clip(frame=...)`),
needles (thread limit), speed (machine hours). Never hard-code 360 x 360. Unconfirmed values are PROPOSED.

## 1. Block + pattern
Fill the POM chart into the block; draft all pieces; run `pattern_out.py qa` — every POM within tolerance, seam walks
equal, cap ease 10–15 mm, rib ratios sane. Render the pieces and look at them (neck curves scoop inward, cuff widths).

## 2. Art
Reuse library motifs; author new ones with a render-compare loop against the mockup crop (ROADMAP §2). Compose on
the size-M block with keep-outs (LESSONS A3). Wrap-around art: split per piece with match marks (A4).
Check against the mockup side by side; density matched (A2); nothing floating (A1).
**Compare sheets:** `out/compare_<element>.png` = mockup crop and stitch preview at the same scale + 3–4 zoomed regions.
Iterate until no mockup detail is missing or simplified (every lobe, crater, leaf, star, texture line, tone step).

## 3. Stitch files
`clean_vis` → `merge_colours` (≤ `factory.max_threads()` = 12 threads) → stops → `merge_stops` → `make_pattern` → write DST + PES → verify.
Fronts: one file per art grade. Wrap pieces: one file per size (A5). Back > frame: `split_clip` + basting crosses.
Gates: max stitch ≤ 7.5, trims from DST read-back, stitch count + run time recorded, every preview looked at.
Cost: report trims per piece, trims per 10k stitches and machine hours — reported, not a gate (fidelity first). Sew-order
work that cuts trims without losing detail (LESSONS B1, B2, B14, B15) is always welcome.

## 4. Placement per size
`emb_place.clearances()` for all sizes — all keep-outs pass, wrap marks aligned.

## 5. Documents
Element specs → embroidery pack (G1–G5) → garment pack (T1–T16) → merge → `shrink.py` → zip with README.
Every number comes from files — per-file and per-stop counts via `readback.dst()` (LESSONS B20). Render every page and look at it.
Every pack includes **F1 Factory requests** (`factory.requests_page`, after the G pages): size-M strike-off files with
their stitches/trims, pieces that need > 1 hooping on the current frame, threads with ΔE > 3 for a lab dip, quote basis.
G pages state machine hours per piece (`factory.machine_hours`, incl. trims + colour changes) and trims per piece.

## 5b. Independent review
The coordinator has a separate reviewer check every delivered pack; fix every blocker + should-fix it returns, then the
pack is `reviewed`. Don't send a pack to the factory before that.

## 6. Strike-off feedback + cleanup pass (after the factory sews size M)
Photos + notes go in `inputs/strikeoff/`. For each issue: measured design size vs spec → pull comp / shrink per stitch
type; puckering → density / underlay; fabric show-through → density; colour off → thread swap (update the palette);
digitiser comments → rule change. This is also when the cleanup pass happens: cut density / trims / stops only where
the sew-out shows it's needed, keeping every detail that read well. Rebuild, bump the revision, add a LESSONS row with the measured numbers (this is the
only real calibration the engine gets — keep the numbers).

## Parallelism
Independent: art per element, stitch files per element/grade/size, pattern outputs, page builds. Run them as
parallel background jobs / subagents; keep one coordinator that runs the gates and assembles the pack.

## Report back
One line per deliverable; the before/after numbers that matter (stitches, trims, threads, stops, keep-out table);
what's PROPOSED; what needs a sew-out.
