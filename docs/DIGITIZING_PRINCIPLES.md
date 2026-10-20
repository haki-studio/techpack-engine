# Digitizing principles (house rules), founder-approved 2026-10-19

Source: a research pass of 43 sources (Wilcom/Hatch docs, Impressions, Graphics-Pro/Erich Campbell, Madeira, Ink/Stitch,
Liu et al. 2023 "Directionality-Aware Design of Embroidery Patterns", and others), confirmed by the founder, who is a
digitizer. Every design follows these rules, and the engine enforces them (LESSONS A11–A16, qa gates).

## The 10 rules
1. **Digitize parts, not colours.** Merge tone blobs into their semantic part (roof tier, cliff stratum, cloud lobe, fall cord) before choosing stitches. Tone inside a part comes from layers and blends, not fragments.
2. **A deliberate direction for every part.**
   - Constructed parts follow rule tables: walls take one angle per plane, roofs run down the slope, members run across their width.
   - Organic parts follow a direction field read from the reference grain (structure tensor or guided fill).
   - Never random, never "fewest fragments", never auto on a blob.
3. **Separate neighbours.** Same-colour neighbours differ by ≥ 15–25° or use a different texture. Depth goes from near-horizontal (far) to near-vertical (near).
4. **Type follows shape.**
   - Satin only on stroke-like parts 1–7 mm wide; split it above 7 mm.
   - Fill only where the part is ≥ ~5 mm wide.
   - Run or bean below 1 mm.
   - Radial only for face-on florets.
5. **Back to front with hidden travel.** The overlapped part sews first. Entry and exit points are planned. Knocked-out details sew before their fill.
6. **Cut what is covered.** Remove overlaps, keeping ~1 mm. Use a minimum fragment size. Never more than 2 stacked top layers. Keep a stitch budget (a full jacket back is ~250–350k).
7. **Underlay and compensation per object.**
   - Tatami 90° plus edge run on big fills.
   - Centre run on narrow parts; edge run plus zigzag on wide ones.
   - No underlay on shading layers.
   - ~0.2 mm pull compensation on duck, less on the side that lies over a fill.
8. **Gradients from density, not threads.** Accordion or two-colour blends, open layers and angle-driven sheen. Each thread serves several motifs.
9. **Simplify to readable minimums.** Satin ≥ 1 mm, text ≥ 5 mm, windows as bands, tiles as run lines, studs 1–1.5 mm. Drop or suggest anything smaller.
10. **Gate on the file, then sew.** Run the DST read-back gates (stitch length, width, density heat-map, trims, colours, hoop fit), angle coherence, direction match against the reference and the live sheen view, then a strike-off on the real fabric and backing.

## Motif playbook
| Motif | Type | Direction | Notes |
|---|---|---|---|
| Sky | horizontal tatami bands with blends | 0° | sew under the clouds, cut away (no bare duck) |
| Clouds | one object per lobe; contour/turning fill or near-vertical split satin; shade as an open layer | follow the lobe | wisps at the sky angle, half density |
| Mountains | random tatami | 10–20°, opposite per face | caps at the face angle |
| Cliffs/strata | one object per band, guided tatami | along the bedding plane, ±15–25° between bands | cracks as run on top |
| Water/falls | falls = 4–10 cords of split satin, alternating tones; pools horizontal | vertical (falls), 0° (pools) | mist as an open fan |
| Buildings | wall tatami; eave satin; roof down-slope with bean tile lines; windows as satin bands | one angle per plane | build walls → roofs bottom-up, studs last |
| Trees | trunk as split-satin strips along the axis; crowns as clumps (dark, then lit) | clumps fan from the branch | every clump touches a branch |
| Blossoms | canopy random tatami → florets (5 notched satin petals + knot) → branches | radial florets | match motif counts |
| Lettering | satin columns along the stroke | across the stroke | ≥ 5 mm, from vector/font, never from pixels |

See the conversation of 19 Oct 2026 (coordinator session d3fafdf9) for the full sourced report.
