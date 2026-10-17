# Engine notes from the Comet City hoodie (16 Oct 2026)

Problems hit while building this product, worked around in project code only. Each: problem → proposed engine fix → check.

## 1. Graded fronts on longer bodies: the scene floats above the hem
- **Problem:** fronts are graded about the CF neck (A 92 / B 100 / C 108 %) so the halves meet at the zip. Body length grows
  ~21 mm per size, so on L/XL (grade B) the city + railing + bicycle ended 33 / 53 mm above the hem-band seam (keep-out 10);
  the mockup has them standing on the hem band. Same on S and XXL/3XL (31 mm).
- **Workaround:** `art_size.py` slides every item down by `dy = hem(size) − hem(M) × scale`, ramped in by the item's reference
  y (0 above y 200, full below y 340 at M); whole motifs move together (per `unit`), cloud tone patches move with their cloud
  silhouette (`cref`), the comet never moves (strands would shear). CF marks (top rail, kerb) shift with it.
- **Proposed engine fix:** `grade_scene(items, size, anchors={"neck": y0, "hem": y1}, ramp=(a, b))` in the engine, with unit / group
  aware translation.
- **Check:** hem clearance on every size within 10–13 (T13 / `emb_place.py`): before 30–53, after 10.4–13.0.
- **LESSON proposal (A12):** "Art that sits on a garment edge (hem, cuff) is anchored to that edge per size, not only scaled about the neck."

## 2. Mockup tone areas pick up garment details (seam topstitching, welts, zip tape, star glows)
- **Problem:** reading clouds as the mockup's own luminance areas also read the side-seam topstitching (a 300 mm tall strip),
  the welt pocket bags, the zip tape edge and the glow around the red falling star / comet fringes as "cloud" fills.
- **Workaround:** cloud masks exclude: 20 mm inside the side/armhole seams, 12 mm around the welt boxes, 17 mm each side of CF,
  a 2–9 mm zone around the comet and every star/meteor head; components < 12 mm² (sky: < 25 mm²) dropped.
- **Proposed engine fix:** `qa.mockup_mask(..., exclude=[seams, welts, zip, motifs])` helper that every tone-trace uses.
- **Check:** compare sheet shows no tone strips along seams; FL lost a 300 mm cloud strip + a welt-shaped haze block.

## 3. Sleeve mapping from a hanging-sleeve mockup
- **Problem:** the mockup shows the front half of each sleeve as a curved, foreshortened band; motifs must land on the flat
  sleeve piece. No engine support.
- **Workaround:** `mockmap.SP / SPinv / swarp`: along the sleeve = shoulder point → cuff seam, across = half cylinder
  (`x = W(y)·(asin(2u−1)/π + ½)`), silhouette tables read from the zooms. The 10–28 mm next to the silhouette edges is background /
  body and is not read.
- **Proposed engine fix:** `mockmap.sleeve_map(silhouette, piece)` in the engine (the 4 hooded products all have sleeve art).
- **Check:** sleeve compare sheets (`out/compare_SR.png`, `compare_SL.png`).

## 4. Palette / rules / stop order still hard-wired (same as Grand Line note 1)
- Worked around in `cccore.py` exactly like `glcore.py`. A project palette file (ROADMAP step 1) would remove ~60 lines per project.

## 5. Motifs for the library (`cc_motifs.py`)
- comet strand bundle (`strand`: offset ribbons along a spline spine, tapered both ends), tapered meteor with head dot,
  8-ray falling star, 4/8-point sparkles with white centres, palm / fern plant (`palm` + `pinna`: arching pinnate fronds,
  two-tone leaflets), bicycle line art, figure seen from behind (original pose), lamp post.
- Proposed: `engine/motifs3.py` with a render test per motif.

## 6. Hood variant timing
- The hooded block (`origin/hooded-variant`) changes the cuff to a 60 mm self-fabric band with cuff = opening 1:1, so the sleeve
  pieces get longer + narrower at the cuff. `front.pieces()` switches to `draft(size, variant="hooded")` automatically once the
  engine has it; re-run `sleeve_scene.py`, `art_size.py`, `build_size.py` for all sizes, then the documents.
