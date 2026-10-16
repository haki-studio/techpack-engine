# techpack-engine

Haki Studios' tech pack generator: garment mockups + a fit chart in, factory pack out.

What it produces for a garment:
- **Embroidery**: stitchable region art (SVG with digitizing attributes), production-intent **DST + PES** stitch
  files (hidden travel, turning satin, underlay, pull compensation, density blends, merged colour stops, ≤ 15
  threads), graded art sizes, per-size files where art wraps across a seam, **360 × 360 hoop splits** with basting
  registration crosses, thread charts (Madeira Polyneon / Isacord, ΔE2000 matched).
- **Pattern**: every piece XS–3XL drafted from the POM chart — seam allowances, notches, grain, drill holes,
  fusing, lining, embroidery placement — as **AAMA-layer DXF** (per size + all sizes) and a **1:1 plot PDF**, with a
  measurement check against the chart and seam walks.
- **Tech pack PDF**: flats, construction details, size chart + grading, BOM (consumption from the pattern),
  seams/assembly, labels/packaging/QC, colourway, pattern pages, inside view, operations, revision log, open
  questions, then the embroidery section (placement, threads, stitch summary, production files, element specs).

Start with `CLAUDE.md` (how to run, conventions) and `LESSONS.md` (rules + checks). `docs/ROADMAP.md` covers the
path to batch runs. Projects: `projects/drum-island-plum-pine` (embroidered work jacket),
`projects/konpeito-jeans` (patches + direct embroidery, see `skills/embroidery-tech-pack`).

```bash
pip install -r requirements.txt
source scripts/env.sh projects/drum-island-plum-pine
python3 pattern_out.py qa
```
