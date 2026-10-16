# Engine notes from the Grand Line jacket (16 Oct 2026)

Problems hit while building this product, worked around in project code only. Each: problem → proposed engine fix → check.

## 1. Palette, region rules and stop order are hard-wired to the plum + pine jacket
- **Problem:** `motifs2.PAL/HEX`, `tech.RULES`, `tech.COLOUR_ORDER`, `tech.LAYER_NAMES`, `dst2.COL_MERGE` all hold Drum Island values.
  `tech.stops()` silently DROPS any region whose colour is not in `COLOUR_ORDER`. `dst2.PULL` is computed at import, so rules added later get
  the 0.2 default. `specbase.TH` is computed at import from whatever `PAL` holds then.
- **Workaround:** `glcore.py` (imported first) adds this jacket's palette/rules into those dicts in place and rebuilds `dst2.PULL`.
- **Proposed fix:** a project palette/rules file (`project.yaml`, ROADMAP step 1) loaded by `tech`/`dst2`; `tech.stops()` should raise on an
  unknown colour instead of dropping it.
- **Check:** test that `tech.stops()` returns every input region (count in == count out).

## 2. Trims on patchwork designs: every island of a colour costs a trim unless something sewn LATER covers its travel
- **Problem:** first pass of the front scene had 625 trims on one front piece (sea dashes on bare fabric, cloud lobes separated by fabric
  gaps, dashed rays, 2-colour stars). `Cover.route()` tolerates only ~0.6 mm of exposed path and every later fill's mask is inset 0.25 mm,
  so a route that crosses the seam between two different later fills usually fails.
- **What fixed it (project side), 625 → ~240 per piece:**
  - sew order designed for hidden travel: light details first, the dark connected tone last (sea: dashes, then a dark sea field around
    them; clouds: rim → shade → body → dark edge band);
  - no fabric gaps between same-tone neighbours (lobes touch; separations are a dark band ON TOP, i.e. an overlay that does not knock out);
  - lines over fills (rays, horizon, lobe edges) as overlays (`ko=False`), so they don't split the fill under them into islands;
  - a big fill with hundreds of holes cut into ~45 × 30 mm cells (long internal moves overflow the router's 900k-px window → intra trims);
  - dashed lines replaced by continuous bean lines (each dash + gap = ~2 trims).
- **Proposed engine fix:** (a) `Cover.add_stop`: merge all LATER stops into one mask before insetting (seams between two later fills are
  covered by pull comp), (b) allow `ko=False` overlay regions natively in the visibility step (`back2.build`/`front.build` knock everything
  out today), (c) auto-section fills with > N holes, (d) a native dashed-run stitch type (`run` with a stitch length + gap pattern in one
  object) so dashed lines don't need trims.
- **Check:** golden test: a 100 × 100 patch of 40 dashes inside a field must sew with ≤ 3 trims.
- **LESSON proposal (B14):** "Design the colour order for hidden travel: details first, the darkest connected tone last; lines over fills are
  overlays. Count islands per colour before stitching — each unhidden island is a trim."

## 3. Hoop splits: registration crosses 12 mm outside the art made wide pieces miss the frame
- **Problem:** `split_marks(ext=12)` puts crosses 12 mm outside the art on both sides (+6 mm arms). A 311 mm wide front piece (3XL) became a
  344.6 mm wide section → fails the 344 mm usable width of a 360 frame although the art itself fits.
- **Workaround:** `split_marks(sp, ext=4.0)`.
- **Proposed fix:** `split_marks` picks `ext` per side from the space left in the frame (frame − 16 − art width) and `split_clip`'s width
  check uses the same value; also make the `split_clip` y-search range a parameter (fixed 40–60 % today).
- **Check:** `fits` true for a 320 mm wide × 2-row split in a test.

## 4. `pattern.py` imports the project module `front` for the welt; materials are hard-coded
- **Problem:** `pattern.draft()` reads `front.WELT_L` (so the welt position is project data — good) but materials/colours
  ("Corduroy — dark brown", "Rib knit — tan") and the welt size are engine constants; `pattern_out.EMB_ON/EMB_NAME/STYLE` are Drum values.
- **Workaround:** `pattern_gl.py` wraps `PT.draft` (materials) and sets `PO.EMB_ON/EMB_NAME/STYLE`.
- **Proposed fix:** pattern materials, welt size/position and embroidery-piece mapping from the project config.
- **Check:** pattern DXF labels for a second project show its own materials.

## 5. Fonts / environment
- `sheet.FONT = "Noto Sans CJK JP"` is not installed on this WSL box (falls back silently). Set to Liberation Sans in `glcore.py`.
  Proposed: `scripts/get_fonts.sh` installs Noto Sans CJK, and `sheet.py` warns when the font is missing (`fc-match`).
- No Python env with the engine deps existed (system python lacks shapely). Built a private venv `~/.venvs/techpack-grand-line`
  from `requirements.txt`. Proposed: `/techpack` creates one shared venv once before launching builders.

## 6. New motifs for the library (live in `projects/grand-line-jacket/gl_motifs.py` + `scene.py`)
- cumulus "lobe packing" from a mask (`pack_var` + `lobe_regions`: rim / body / shade / dark edge band, sew-order tags),
- 4-point sparkle star (single-thread cross, gold+pale big sparkle), sunburst (tapered satin), radial-satin sun, run-stitch glow arcs,
- sea: dark field + light horizontal tatami dashes in perspective rows; glitter path.
- Proposed: move to `engine/motifs3.py` with a render test (one bank, one star, one sea patch).
