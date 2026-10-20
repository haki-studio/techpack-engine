# RECAP 2026-10-20 — tee FAMILY + data-only variants (builder TEE, branch `family-tee`)

## What / why
Founder: "a tee techpack suite, that'll really only be a print and tee colour … each time". ROADMAP step 1 started as
**product families**: `families/tee/family.yaml` (built once) + one yaml per tee → full PDF pack, one command, no new Python.

| Piece | Where |
|---|---|
| Loader (V values, `{proposed: x}` → amber + F1), POM chart = base + deltas | `engine/family/spec.py` |
| Print methods (screen, dtg, dtf, puff_print, embroidery stub) as data | `engine/family/methods.yaml`, `methods.py` |
| Tee block from the chart (front/back flats, sleeve angle solved from the half bicep, clearances) | `engine/family/tee_block.py` |
| Page set T1-T8, D1..Dn, F1 (multi-page), R1 | `engine/family/tee_pages.py`, `draw.py` |
| Build + shrink + PNGs | `engine/family/build.py`, `scripts/family_build.py` |
| Family data | `families/tee/family.yaml` |
| Variants | `families/tee/variants/alabasta.yaml`, `from-the-shadows.yaml` |
| Template proof (back DTF + left-chest embroidery stub) | `tests/fixtures/tee_example_back_dtf_embroidery.yaml` |
| Tests (18) | `tests/test_family_tee.py` |
| Docs | `docs/FAMILIES.md`, LESSONS D4, ROADMAP step 1 note |

## Decisions
- **Block = the Shadows tee** (founder 2026-10-20). Mandy's 2026-01-25 "POM inch" chart XS–2XL is `pom_chart.base`
  (confirmed numbers); the March 2026 new-shape changes recorded at L only are `pom_chart.deltas` (A 27, F 10 1/4,
  H 7 5/8, inner sleeve 4 new POM P, bicep −1.5 cm half = −3 cm circumference, shoulder +2 in **proposed**: drop
  shoulder width never recorded). Other sizes move by the same amount (= base grade steps) and print amber. When Mandy
  sends the real chart: paste it under `base`, delete `deltas` (tested).
- Bicep / sleeve opening half flag is **proposed** (chart does not say; magnitudes read as half).
- Tolerances in Mandy's format, cm, all proposed (A/B/D ±1, C ±0.75, sleeve/neck ±0.5, BND ±0.3, band ±0.2).
- Placement can be set from the HPS (`top_below_hps_cm`) or from the neck seam (`top_below_neck_cm`). A fixed HPS
  distance of 14 cm hit the rib on XL/2XL (FND grows 1/8 per size) — the check caught it, so Alabasta is set 4 cm below
  the CF neck seam (proposed).
- Embroidery decorations are a stub page (placement + size; stitch files via engine/digitize later). Max threads read
  from factory.json.
- Second variant = the real Shadows tee (black garment-dyed, DTG wide chest print, proposed 34 × 14 cm), per coordinator;
  the made-up DTF/embroidery tee became a test fixture.

## Gaps / caveats
- **Reference photos not embedded**: downloading PLM storage photos needs the service key, and the auto-mode classifier
  refused it (credential exploration). Packs draw a labelled placeholder ("D1 ART") and say in red that the image is not
  attached. Drop the images at `families/tee/variants/art/alabasta_reference.jpg` / `from_the_shadows_reference.jpg`
  and rebuild — they are fitted into the art box automatically. The size-chart numbers were checked against the
  photo's OCR text in PLM (identical), not the photo itself.
- Flats are drafted from the chart, not a pattern; sleeve drawn as a straight trapezoid; the shoulder slope 3.5 cm and
  hems 2.5 cm are proposed.
- Fonts: this box falls back to DejaVu Sans (no Noto CJK) — fine for Latin text.

## Verify
`python3 -m pytest -q tests` → 220 passed. Mutations (each red, restored green): amber off, half chest doubled,
unknown method accepted, F1 drops a group, deltas ignored, placement not read from the chart.

## Next
- Jacket family (docs/FAMILIES.md "Next"): jacket block adaptor over drum/pattern with the same flat interface, family
  yaml from drum.POM_CM, embroidery decorations wired to engine/digitize so D pages show DST read-back numbers.
