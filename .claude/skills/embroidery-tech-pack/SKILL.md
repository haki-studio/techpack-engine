---
name: "embroidery-tech-pack"
description: "Turn garment flat lays plus element screenshots into a full tech pack: production-ready vector art and spec sheets for every patch, embroidery and trim, stitch-checked at real size."
---

# Garment tech pack builder (embroidery, patches, trims)

Use when Devin shares a garment's front and/or back flat lay (mockups, often with AI-rendered details) and/or screenshots of individual elements: waistband label, back label, coin pocket, front embroidery, pocket stars, prints and so on. **The job is the whole garment.** Devin should not have to say "now do the waistband, now do the coin pocket": inventory every element, build each one to production standard, and finish with the garment-level pages that tie the pack together.

The standard: a factory digitizer and sewing room can build every element with no follow-up questions, matching elements really match when produced, and every deviation from the mockup is explained with numbers.

## How a run goes

Use a task list: one task per element, plus the garment pages and final assembly.

### Phase 0: Inventory (always first, in the first reply)

Study the flat lays and every screenshot, then post one short message with:
1. **Element list**, numbered in tech-pack order. For each: name, location (front/back, which side as worn), process (sew-on patch, direct embroidery, woven label, print, hardware note), and which screenshot covers it. Include elements visible only in a flat lay (no close-up): note that you'll work from the flat lay and what detail is guessed.
2. **Shared system:** components that repeat across elements (border, motif, thread colours, character, lettering style). These get defined once, in mm, before anything else.
3. **Build order:** start with the most detailed element that defines the shared system, then its siblings, then direct-embroidery placements, then the garment pages.
4. **Assumptions and blockers:** garment size or pattern (flat lays have no scale), element sizes, anything that can't be produced as shown, and elements that can't be built for IP reasons (below). Ask only what genuinely blocks; otherwise state the assumption and continue.

Then start element 1 in the same turn.

### Phase 1: First element, then check in

Build element 1 completely (art, QA, spec sheet), deliver it, and **stop for Devin's go-ahead.** This is where he confirms direction: scale, style deviations from the mockup, sheet format, house-spec choices. Fold his corrections into the shared system.

Skip this check-in if Devin says to run it all, or the session is unattended (then state assumptions at the top and keep going).

### Phase 2: Everything else, without being asked

After the go-ahead, build every remaining element in order. Deliver each spec as it's finished so Devin can redirect early, but don't stop between elements unless something changes direction (an element that can't be produced, a conflict with an approved choice). Keep cross-element consistency: reuse shared components exactly, and re-run the comparison checks whenever a sibling is added.

### Phase 3: Garment pages and assembly

1. **Placement overview** (front and back): the flat lays with numbered callouts for every element, each placement dimensioned from garment reference points (centre back, side seam, waistband top edge, pocket edges, fly) with tolerances.
2. **Thread and trim summary:** every thread colour across all elements (hex, weight, which elements use it), patch and trim counts per garment, backing and edge-finish types.
3. **Stitch-check summary:** one row per element with its result.
4. **Open questions:** everything still to confirm, in one place.
5. **Cover and index:** garment name, Rev, date, element list with page numbers.
6. Merge everything into one tech-pack PDF (cover, overview pages, then element sheets in order) with pypdf, and keep the per-element files too.
7. Deliver the merged PDF plus a folder: `HAKI_<garment>_TECHPACK_RevA.pdf` and `elements/NN_<element>/` (ART.svg, ART+guides.svg, ART.png, SPEC.pdf). If the computer is linked and Devin asks, save it to a named folder in his Downloads.

## Working principles

1. **Physical mm, never percentages.** Renders have no scale. Shared components are fixed mm values reused on every piece.
2. **Measure before drawing.** Crop details, add coordinate grids, sample thread colours, deskew rotated renders.
3. **Stitch-check everything at real size** (thresholds below). If something fails, change the design (size, spacing, thread weight, hand-redraw) rather than hoping the digitizer fixes it. AI renders routinely show lettering that can't be stitched; say so with numbers.
4. **Look at every render.** View each PNG, zoom in on lettering and tight areas, fix collisions, re-run QA.
5. **Explain every change from the mockup:** what moved, by how much, and why (topstitch clearance, rivet zones, legibility).
6. **Flag assumptions** (sizes, patterns) as items to confirm, and say what changes if they're wrong.
7. **No copyrighted characters, logos or brand marks** (e.g. Ghibli soot sprites, Sanrio characters). Flag them in the inventory, decline that element in one sentence, note the licensing risk on a product being sold, and offer original replacements. Never draw a lookalike. Build every other element as normal; one blocked element never stalls the pack.

## Haki house spec (Rev A, Oct 2026: black konpeito jeans)

Shared patch border: everything is a fixed mm value.
- Satin edge 2.0 mm, heat-cut, corner radius R2.5
- Flower band 4.5 mm, so the total border is **6.5 mm** on all sides
- 5-petal white flower Ø4.0 mm with a tiny red centre; white dot Ø1.5 mm
- Flower → dot pitch 5.8 ±0.2 mm, flower on every corner; an even number of intervals per side so both ends land on a flower
- Rivet corners: no motifs, cap Ø8 mm centred 4.25/4.25 mm from the edges

Thread palette (40wt polyester unless noted):
| Name | Hex | Use |
|---|---|---|
| red | #C8162B | edge, band, lettering, frame, accent dots |
| cream | #F2E9D8 | patch field |
| white | #FBF8F1 | border motifs, sparkles, flower centres |
| black | #1C1A1A | small lettering, line art (**60wt**) |
| pink / pink tint | #EF7FAC / #F8B5CF | |
| yellow / yellow tint | #F5C230 / #FCE27E | |
| blue / blue tint | #35A6D6 / #8ED2EE | |
| rose | #E8457A | cheeks |

Konpeito jeans pieces built so far: coin pocket 76 × 56 mm (patch, rivet corners), waistband patch 80 × 54 mm, back-pocket stars 10 mm (direct embroidery). The front-leg trail is open: the mockup used soot sprites, so it needs an original replacement. For a new garment, start a new house spec, or reuse this one if Devin says it's the same family.

## Stitchability thresholds

| Check | 40wt satin | 60wt / fine detail |
|---|---|---|
| Min stroke (satin column) | 0.8 mm | 0.6 mm |
| Min gap between separate parts | 0.5 mm | 0.35 mm |
| Min enclosed counter (inscribed Ø) | 0.6 mm | 0.45 mm |
| Min dot | 1.1 mm | 1.0 mm |
| Clearance between design elements | 0.7 mm | 0.7 mm |
| Line art (triple-run / bean stitch) | 0.7 mm | 0.6 mm |

Lettering:
- Kana at ~6–7 mm tall needs a rounded font with real stroke weight (Zen Maru Gothic Bold/Black); thin handwriting fonts (Yusei Magic) fail. Small black lettering goes to 60wt.
- Dense kanji (理, 砂, 気, 会) under ~9 mm usually fail in any font, so hand-draw them as uniform-width strokes with counters at least 0.8 mm open.
- Kern by true outline distance between glyphs, not by advance width.
- Embolden only by a measured amount; then nudge or slim small parts (dakuten, dots) that end up under the min gap, never below the min stroke. Fill tiny junction pockets (< 0.12 mm²) rather than widening them.

Placement on the garment:
- Keep embroidery ≥ 3 mm clear of topstitching (drawn as an orange keep-out zone), and clear of rivets and bartacks.
- Embroider flat on cut pieces before assembly; give positions from finished edges and tell the factory to convert to cut-piece coordinates using their pattern.
- Embroidery spanning a seam (e.g. a trail down the leg crossing the side seam) must be split per pattern piece, or sewn after assembly. Say which.
- Tolerance ±2 mm, rotation ±5°, unless the element needs tighter.

## Building each element

1. **Measure** the reference: note what won't produce as shown.
2. **Size test:** run the stitch check at candidate sizes before committing to one.
3. **Vector art in Python** (shapely for geometry, fontTools for outlines, cairosvg to render, pypdf to merge). SVG user unit = 1 mm, `width="Wmm"`. All text converted to outlines. One named group per thread colour in stitch order (`01_edge_satin_and_band_RED`, ... `99_GUIDES_do_not_stitch`).
4. **QA loop:** (a) raster stitch check per layer (opening for thin strokes, closing for merging parts, inscribed circle for counters); (b) pairwise clearance between elements; (c) for shared components, measure the final files directly (e.g. border width on all four sides of every patch) and show the comparison.
5. **Spec sheet**, A4 landscape PDF, sections lettered A, B, C...:
   - Header: element name, process, Rev, date, "all dimensions in mm, finished size, art files are 1:1", which elements it pairs with
   - Art at a stated scale with overall and border dims
   - Shared-component detail (zoomed corner, callouts) and a side-by-side against sibling elements with a measured comparison table
   - Placement drawing for direct embroidery: schematic garment part, keep-out zones, dimensioned detail, tolerance
   - Mockup reference with a "what changed" note
   - Thread table: swatch, role, hex, weight; mark threads shared with other elements
   - Stitch-check table: element, size, stitch/thread, min stroke, min counter, gap, PASS
   - Notes: edge finish, backing, field coverage, wash test, "don't re-set text from a font", sew-out before bulk
   - Check rendered sheets for overlapping text, clipped labels and unescaped `&` in SVG text

## Replies

One line on what's done; the files, sent as they're ready; bullets for what changed from the mockup (with numbers and reasons) and what to confirm. No recap of steps. At the check-in, ask one clear question about direction.

## Reference: stitch-check core (Python)

```python
import numpy as np
from scipy import ndimage as ndi
PX = 40  # px per mm
def disk(mm):
    r = mm*PX/2; n = int(np.ceil(r)); y, x = np.ogrid[-n:n+1, -n:n+1]; return x*x + y*y <= r*r
def stitch_check(ink, min_stroke=0.8, min_gap=0.5, min_counter=0.6):
    thin = ink & ~ndi.binary_opening(ink, structure=disk(min_stroke))
    bg = ~ink; lab, n = ndi.label(bg)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bdt = ndi.distance_transform_edt(bg)
    counters = [2*bdt[lab == i].max()/PX for i in range(1, n+1) if i not in border]
    parts_before = ndi.label(ink)[1]
    parts_after = ndi.label(ndi.binary_closing(ink, structure=disk(min_gap)) | ink)[1]
    return dict(thin_pct=100*thin.sum()/ink.sum(),
                small_counters=[c for c in counters if c < min_counter],
                merges=parts_before - parts_after)  # pass: thin_pct < 1, no small counters, merges == 0
```

## Reference: border motif placement

```python
def side_positions(a, b, pitch=5.8):
    L = b - a; n = max(2, round(L / pitch))
    if n % 2:  # even intervals => flower at both ends
        n = n + 1 if abs(L/(n+1) - pitch) < abs(L/(n-1) - pitch) else n - 1
    return [a + L*i/n for i in range(n+1)], L/n
# even index = flower, odd = dot; skip corners listed as rivet corners
```