# Product families — a new tee is a 20-line file, not new code

Every product used to carry its own 3–6k lines of page builders. A **family** is built once (the block from the
size chart, construction, fabric, labels, packing, the page set). A **variant** is one small file per product: body
colour + the print(s) + anything that differs. No Python per product.

```
families/tee/family.yaml              <- the tee family (Mandy's tee: chart, fabric, stitching, labels, packing)
families/tee/variants/alabasta.yaml   <- one tee
families/tee/variants/<new>.yaml      <- the next tee
engine/family/                        <- the code (loader, tee block, pages, print methods) — shared by every variant
```

## Add a new tee (founder steps)

1. **Copy** `families/tee/variants/alabasta.yaml` and rename the copy, e.g. `families/tee/variants/sky-island.yaml`.
2. **Change these lines** in the copy:
   - `slug:` the file name without `.yaml` (`sky-island`), and `name:` (`Sky Island Tee`).
   - `body:` → `colour:` (e.g. `Black`), `hex:` (a screen colour for the drawings, e.g. `"#1C1C1C"`), `pantone:`.
   - Under `decorations:` one block per print:
     - `name:` what it is (`Front chest print`)
     - `method:` one of `screen`, `dtg`, `dtf`, `puff_print`, `embroidery`
     - `view:` `front` or `back`
     - where it sits: `top_below_neck_cm:` (from the neck seam) **or** `top_below_hps_cm:` (from the top of the shoulder),
       and `centre_from_cf_cm:` (0 = centred; 10 = 10 cm towards the wearer's left)
     - size: `width_cm:` and `height_cm:` (one number for every size, or one per size: `{S: 26, M: 28, L: 28}`)
     - `artwork: {file: art/sky-island.png, label: "..."}` — put the image in `families/tee/variants/art/`
   - `revisions:` one line saying what changed.
3. Anything you are **not sure of**, write as `{proposed: <your guess>}` instead of the plain value. It prints amber with
   "[proposed — confirm]" and goes on the factory question page (F1) automatically.
4. **Run one command** from the repo folder:
   ```
   python3 scripts/family_build.py families/tee/variants/sky-island.yaml
   ```
   The pack is `families/tee/out/sky-island/sky-island_techpack_RevA.pdf`; every page is also a picture in
   `families/tee/out/sky-island/pages/` — open them and look before sending (LESSONS D1).
5. If a print does not fit (too wide, too close to the collar or a seam), page D1 says so in red with the size that fails.
   Make it smaller or move it and run again.

Mistakes are caught with a plain message, e.g. `unknown method 'foil'. Known methods: screen, dtg, dtf, puff_print,
embroidery` or `missing 'width_cm:'`.

## When Mandy answers

Edit `families/tee/family.yaml` once and every tee's pack changes on the next build:
- an answer to an amber value: replace `{proposed: x}` with the real value (and a `source:` if you like);
- **the full new-shape size chart**: paste it under `pom_chart: base:` and delete `deltas:` — the block, every flat
  sketch, every POM table and every print placement follow it (tested: `tests/test_family_tee.py`).

## What is family vs variant

| Family (`family.yaml`, built once) | Variant (`variants/<slug>.yaml`, per product) |
|---|---|
| POM chart (base chart + recorded changes), half measures flagged (LESSONS C2), tolerances | slug, name, style, rev |
| block constants (shoulder slope, hems), fit | body colour, hex, Pantone, wash |
| blank fabric, rib, care | decorations: method, view, placement, size per size, art, ink colours, notes |
| construction + stitching | `spec:` overrides of a method's default spec lines |
| labels (main/size hem label, care, neck), hang tag | `overrides:` anything in the family for this one product (e.g. `labels: {neck: {enabled: true}}`) |
| packing, placement keep-outs, top factory questions | revisions |

Print methods (`engine/family/methods.yaml`) are shared by every family; each has its own spec lines (screen: inks,
mesh, underbase, flash/cure…; DTG: pretreat, underbase, resolution; DTF: film, press temp/time/pressure, hand feel;
puff: ink, cure, min line width). `embroidery` is a stub page today: placement + size here, the stitch files come from
the stitch path (`engine/digitize`, techpack-pipeline) as G pages.

## Pages

T1 cover · T2 flat sketch + POMs · T3 POM chart + grading + tolerances · T4 construction · T5 BOM · T6 labels + trims ·
D1..Dn one per decoration (placement on the flat at true proportion for every size, clearances to every seam, method
spec, artwork) · T7 colourway · T8 packing · F1 factory requests (every amber value) · R1 revisions + approvals.
No prices, quantities or our numbers appear on any page (tested).

## Next: the Drum Island jacket family

The same pattern, with the jacket's existing engine pieces:
1. `families/jacket/family.yaml` — `pom_chart` from `engine/drum.py` `POM_CM` (cm, half flags), the jacket fabric /
   lining / zip / rib BOM and construction from the Drum Island garment pages, labels, packing.
2. A jacket block adaptor: `Spec.flat()` returns a jacket flat built from `drum.Block` / `pattern.draft` (front pieces,
   back, sleeve, collar) with the same interface the pages use (`body`, `sleeve`, `band_poly`, `lines`, `clearances`,
   `neck_seam`, `bounds`). Clearances should read keep-out lines from the drafted pattern (LESSONS C8), as `emb_place` does.
3. A jacket page set (reusing T3/T5/T6/D/T7/T8/F1/R1 from the tee set; jacket-only pages: pattern pieces + cut list, DXF).
4. Decorations with `method: embroidery` connect to `engine/digitize` (`run.yaml` per element) so the D page shows the
   real stitch counts read from the DST (LESSONS B9/B20) instead of the stub. Variants: Grand Line, Forestball, Moon, Castle
   Falls… become one yaml each plus their stitch-file runs.
