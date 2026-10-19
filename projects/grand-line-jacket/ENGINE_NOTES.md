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

## 7. Max-stitch gate can fail by DST grid rounding
- **Problem:** `make_pattern` splits sewn stitches only when > 7.5 mm, before coordinates are rounded to the 0.1 mm DST/PES grid; XXL/3XL
  FR read back a 7.52 mm stitch (LESSONS B7 gate is ≤ 7.5).
- **Workaround:** `build_size.cap_stitches()` splits any stitch > 7.4 mm in the pattern before `dst2.write`.
- **Proposed fix:** split at > 7.4 in `make_pattern` (and in `turning_satin` / `fixed_satin`, which split at 7.0 already), or round first.
- **Check:** `verify()` max_stitch ≤ 7.5 on every file of a scaled (108 %) test design.

## 8. split_clip y-search range is fixed at 40-60 % of the height (Rev B)
- **Problem:** on tall front pieces the best split (least art cut) can be outside 40-60 %; the reviewer saw the split go through the densest cloud bank.
- **Workaround:** `build_size.py` execs a copy of `split_clip` with the search widened to 12-88 % (77 candidates); still frame-checked. Asserts if the engine source changes.
- **Proposed fix:** `split_clip(..., y_range=(0.12, 0.88), n=77)` parameters; optional penalty for cutting fills of given codes (clouds).
- **Check:** G6 "cloud crossed by split" column; test a design whose bare band is at 25 % height.

## 9. Fidelity-first trims (Rev B)
- A dash-field sea with no ground fill and soft-edged florets cost FR M 283 → ~950 trims. The B14 tricks (dark connected fill sewn last) conflict with "no slab".
- **Proposed fix:** native dashed-run / chained-dash object: consecutive dashes on a row joined by a hidden underpath under the *next* row's dashes, or a 0.4 mm single-run link under a later bean ray. Then dash seas sew as chains, not islands.

## 10. PROCESS: a parallel builder's autostash reset this project's uncommitted files (Rev C, 22:27)
- **Problem:** `commit_project.sh` runs `git pull --rebase --autostash` in the ONE shared working tree. Another builder's pull stashed every
  uncommitted file in the repo (all projects) and the stash was not re-applied (a stale `.git/rebase-merge/` was left behind), so
  grand-line-jacket's scene.py / build_size.py / gl_motifs.py / compare.py silently went back to the Rev B commit while builds were running.
  Recovered from the dangling autostash commit e71be49 (`git fsck --lost-found`).
- **Proposed fix:** one git worktree per builder (like plm-wt.sh), or `commit_project.sh` commits with `git commit -- projects/<slug>` and
  pulls with `--no-autostash` (abort if the tree is dirty outside the project); never autostash other projects' files.
- **Check:** two builders with uncommitted edits commit at the same time; both trees keep their edits.
- Also seen: background jobs of this project killed externally ("Terminated") at the same time (E2/E6).

## 11. Per-stop labels shift when a build stop sews nothing (Rev E)
- **Problem:** a colour stop whose objects all fall below the sewable minimum emits a COLOR_CHANGE with 0 stitches; the DST writer
  drops it, so DST stop *n* is build stop *n+1* from there on. Pairing per-stop labels by position (or by the PES thread list, which
  also folds repeated colours) shifted every later colour label (Rev D/E p4: e.g. "gold 15,573" was really the cloud shadow stop).
  Totals were right; per-stop colours were not.
- **Fix (project):** `build_size.record()` counts stitches per build stop in the pattern before writing, drops empty stops, pairs the
  rest 1:1 with `readback.dst()` and asserts the counts agree (±2 %).
- **Proposed engine fix:** `make_pattern` skips stops with no blocks (no COLOR_CHANGE), and `readback` gains a `labels=` check.
- **Check:** test with an empty middle stop: per_stop colours from the DST match the build.

## 12. Radial tatami leaves gaps at the outer edge (Rev E)
- **Problem:** `build_object` radial tatami uses `SR.radial(p, cx, cy, SP_TAT)` with a ray count from 0.55 x the max radius, so rows
  diverge to ~0.8 mm at the outer edge of a lobe fan: visible navy "ticks" in cloud lobes.
- **Workaround:** fans built as 14-degree sectors, each a plain tatami at its own angle (even 0.45 rows).
- **Proposed fix:** radial tatami adds intermediate short rows where the ray spacing exceeds 1.3 x SP (like radial satin short stitches).
- **Check:** coverage raster of a 20 mm fan lobe: no uncovered pixel > 0.3 mm inside the outline.

## 13. A post-processing pass swallowed a COLOR_CHANGE (Rev E, caught before shipping)
- **Problem:** `build_size.trim_exposed()` (replaces exposed travel runs with TRIM + JUMP) matched a run by its FIRST stitch only and
  then skipped the run's length; on a false match it skipped over a COLOR_CHANGE, so sea teal + sea light sewed as ONE stop in the DST
  (14 DST stops for 15 build stops). The readback-vs-build check passed because `zip()` truncated the longer list.
- **Fix:** match every stitch of the run; assert the number of COLOR_CHANGEs is unchanged; `record()` asserts colour segments ==
  build stops and per-stop counts within ±(4 x trims + 5 %).
- **LESSON proposal (B21):** any pass that edits a stitch stream after `make_pattern` must assert command counts (COLOR_CHANGE, END)
  are preserved; per-stop labels are paired by emitted stitches, never by position or thread list; never `zip()` two lists whose
  lengths are the thing being checked.
- **Check:** unit test: a pattern with two adjacent stops and a travel run ending at the stop boundary keeps both stops.
