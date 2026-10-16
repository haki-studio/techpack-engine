# Engine notes from the moon build (problem → proposed fix → check)

For the coordinator to merge into `engine/` / `LESSONS.md`. Nothing in `engine/` was edited by this build.

| # | Problem | Proposed fix | Check |
|---|---|---|---|
| 1 | The thread palette is hard-wired in `motifs2.PAL`, and `tech.stops()` silently DROPS any region whose colour is missing from `tech.COLOUR_ORDER`. A new palette has to be injected (see `moonpal.install()`). | Add a per-project palette (`project.yaml` or `pal.py`), and make `tech.stops()` raise on an unknown colour instead of skipping it. | Test: region with an unknown colour → `stops()` raises. |
| 2 | Densities are global knobs in `dst2` (`SP_TAT`, `LATTICE_MIN`). A low-density element (the moon: 0.55 rows, light 4 mm underlay) needs a per-code override, done here by wrapping `dst2.build_object` (`moonpal.patch_dst2`). | Add `RULE_DENSITY = {code: (row_sp, stitch_len, underlay)}` read by `build_object`. | Stitches per mm² by code in the results JSON. |
| 3 | `absorb_slivers()` (plum `back2.py`) hands slivers of LINE regions (bean wires) to the neighbouring FILL. A wire clipped at 3 mm from the side seam gave its end sliver to a crossarm satin, which then sat 12 mm from the seam (keep-out 15) on XL. | Line regions keep their own slivers (`if line: continue`), as in `scene.absorb_slivers`. Move `absorb_slivers` into the engine with that rule. | `emb_place.clearances()` side ≥ 15 for non-wire art on every size (the XL failure is now a pass). |
| 4 | `dst2.split_clip` only splits 2 × 2. Art that runs side seam to side seam (wires) is 593–695 mm wide: L–3XL do not fit 2 × 2 with the cross extension. | `moonsplit.grid_split`: nx × ny grid (fewest hoopings, then least fill cut), crosses on bare fabric ON the split lines inside the art bounds (no 18.5 mm extension needed), frame check incl. crosses. Proposed for the engine. | `fits` per section: 30/30 sections pass, XS–3XL. |
| 5 | A licensed-figure area has to be "marked in the stitch file" without stitching it. | `moonstitch.add_placeholder()`: last colour stop = basting outline (water-soluble, pink) of the box; when the box straddles a hoop split, each section bastes its own part of the outline. Proposed as an engine feature (`placeholder=` on `make_pattern`). | Thread chart lists the PLACEHOLDER stop; G5 shows which split sections carry it. |
| 6 | `pattern.py` hard-codes collar/rib materials ("dark brown", "tan") and `pattern_out` hard-codes `STYLE` + `EMB_ON`. | Material/colour + style code from the project config; `moonpattern.py` / `pattern_moon.py` override them today. | DXF piece text shows the moon materials. |
| 7 | `sheet.header()` footer hard-codes "plum + pine work jacket". | Footer from a module variable (as `specbase.FOOT`). | — |
| 8 | Wrap check across a side seam (not an armhole): heights above the hem seam must agree on back + front per size. | Generic seam-wrap helper: wires defined by (seam, height above hem) so both pieces are built from the same number; check = every end visible 3.0 ± 0.6 mm from the seam on both pieces (`scene.seam_check`). | `emb_place` wrap 8/8 on every size. |
| 9 | LESSONS E2 again: `pkill -f <pattern>` killed the calling shell during this build. | Keep the lesson; maybe add a `scripts/killjob.sh <exact argv>` helper. | — |

New motifs (proposed for the library, with a render test): `moonmotifs.cloud` (scalloped Japanese cloud), `moon`,
`pole` / `crossarm` / `insulator` / `string_insulator` / `can` / `bracket`, `wire`.
