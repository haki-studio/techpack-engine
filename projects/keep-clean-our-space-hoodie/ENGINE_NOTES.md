# Engine notes — Keep Clean Our Space hooded jacket (16 Oct 2026)

Problems hit on this product, worked around in project code only. Each: problem → proposed engine fix → check.

## 1. Lettering from real fonts (no engine support)
- **Problem:** the engine has no text object. A whole glyph polygon sent as one satin region sews only along the
  skeleton's longest path (`dst2.centreline`): side strokes get no coverage; rings (O, ㅇ, 口) get half a satin.
- **Workaround:** `kclettering.py`: font outline (fontTools, variable fonts instanced) → glyph polygon (nonzero:
  union of outer contours minus holes) → `strokes()`: skeleton, junctions removed, spurs pruned, straight-through
  branches re-joined across junctions, every pixel to its nearest branch, exact tiling of the outline; rings cut in two;
  `split_corners()` cuts strokes on the mitre where the centreline turns > 50° (otherwise turning satin fans round
  L / 冖 / ㄱ corners — seen in the first DST read-back).
- **Proposed fix:** move to `engine/lettering.py` (`glyph`, `set_line`, `set_column`, `strokes`) with a render test.
- **Check:** test: every stroke of 口 / O / 田 is covered by its turning satin (coverage of the satin hull ≥ 98 % of
  the glyph area), no satin fans (max angle between consecutive satin rows < 25°).

## 2. 3D puff (foam) stops
- **Problem:** no puff object: puff needs dense satin with no underlay, extra pull, and a machine pause before the
  first puff stop (lay foam) and before details sewn on top (tear foam). `merge_stops` could pull a puff region into
  an earlier flat stop of the same colour (before the foam).
- **Workaround:** `kccore.patch_dst2()` wraps `dst2.build_object` for `PF-*` codes (sp 0.30, pull 0.35, no underlay);
  `kcstitch.stops_for()` builds flat / puff / on-top blocks separately and merges stops inside each block only;
  `result_*.json` records `foam_pause_before_stop` / `foam_tear_before_stop` (read on the stop tables).
- **Proposed fix:** region flag `puff=True` (or rule column "process") handled in `tech.stops` + `make_pattern`, and
  an optional pe.STOP command written before the first puff stop.
- **Check:** test that no PF region is in a stop before the first puff stop after `merge_stops`.

## 3. Sheer glow under text: knockout must not cut it
- **Problem:** the scene knockout (`visible()` in the art builders) cuts every lower region where a higher one sits;
  a serpentine run cut by the letters falls into dozens of pieces = trims.
- **Workaround:** `nok=True` regions (never knocked out, sewn first) in `art_size.visible()`.
- **Proposed fix:** native overlay/underlay flags in the engine visibility step (ROADMAP item 6 already lists `ko=False`).

## 4. Stars in keep-outs: nudge, don't drop
- Dropping whole stars that land in a keep-out lost ~40 % of the mockup's front star count (the AI render's sleeves /
  side seams sit where the Drum Island keep-outs are). `art_size.place_stars()` moves each to the nearest free spot
  inside the clip (≤ 8 mm, ≥ 2.5 mm from other stars). Proposed: `qa.place_whole(motifs, clip, max_move)` in the engine.

## 5. Small dots vanish in `clean_vis`
- `clean_vis(min_area=1.5)` drops satin dots < Ø 1.38 mm (house spec min dot is 1.1). Dots set to ≥ Ø 1.45 here.
  Proposed: `clean_vis` keeps regions whose code is a dot (`DOT*`) down to the house-spec minimum.

## 6. split_clip search range (also Grand Line note 8)
- x/y split search widened to 25–75 % / 15–85 % by an exec'd copy of `split_clip` in `kcstitch.py` (asserts on
  engine change). Sleeves need a 2 × 2 split. Proposed: `split_clip(..., x_range, y_range, n)` parameters.

## 7. Lesson proposal (A12)
"Text is set from a font with the client's exact characters, split into strokes (one turning satin per stroke,
cut at corners), never traced from an AI render — AI glyphs are garbled (this mockup: 7 glyphs for a 6-character
Chinese phrase, upside-down mirrored Hangul)." Check: the spec page prints the string and the font; reviewer compares.

## 8. Background builds killed by other sessions (E2/E6 again)
- Twice my `build_size.py` jobs died with SIGTERM (exit 143/144) while other product builders were running — a
  `pkill -f build_size` style kill elsewhere matches every project's builder. Renamed this project's builder to
  `kcstitch.py` and launch it with `setsid`. Proposed: builders get a project-unique process name, or heavy.sh
  records PIDs in a per-project file so a session only kills its own.

## 9. Text satin quality (project `kccore.stroke_satin`)
- Turning satin on font strokes fans at junction blobs and tight inner curves. Project fix: rows that cross the previous
  row or pivot on an inner corner are skipped; a stroke whose rows cover < 95 %, turn > 75° within one stroke width,
  or have > 12 % rows longer than 1.6 × median falls back to a fixed satin at the most "across" angle. Junction crumbs
  (< 1.3 w²) merge into a neighbour. A few CJK junction pieces still sew as fixed-angle satin — the digitizer may hand-
  edit those (noted on R1). Proposed: engine lettering module with these rules + a golden test glyph set.

## 10. Hooded block (origin c026934, engine/hoodie.py): welt position must be overridable — BLOCKER for the pattern stage
- **Problem:** the merged block reads the welt from `drum.WELT_L_M` (Drum Island welt, 38°, centre ≈ ±175 / 364). This
  mockup has steep slash welts beside the side seams (58°, centre ±245 / 360, `front.py WELT_*`). With the Drum welt the
  CN badge (03, FR x −192…−76, y 230…438 at M) sits on top of the pocket opening; every size fails the 6 mm welt keep-out.
  The stitch files in this delivery were cut against the project welt (the shared working tree still has the pre-merge
  `pattern.py`, which read `front.WELT_L`).
- **Proposed fix:** `pattern.draft(size, welt=(centre_xy, angle_deg, length, width))` (and `hoodie.draft(..., welt=...)`),
  defaulting to `drum.WELT_L_M`; the project passes its `front.WELT_C/WELT_ANG`.
- **Check:** `emb_place.clearances()` welt ≥ 6 on every size with the hoodie pattern; test that a welt override moves
  `F01.internal[0]` and the drill holes.
- **Then (builder):** sync the shared tree, run `pattern_out` for the hoodie block, rebuild `art_size.py` + `kcstitch.py`
  if the hood changes the front neck line (keep-out 10 from the neck seam), build the T pages.

# Rev B (19 Oct 2026) — from the first independent review

## 11. make_pattern: travel hid under satins that were ALREADY sewn (visible lines across letters) — engine bug
- **Problem:** `make_pattern` builds the stop's hidden-travel mask from `own_mask` (every FILL_ST object of the stop,
  satins included) and `merged(si)` (this stop's own footprint), once per stop. An object stays "hidden" after it is
  sewn, so travel to the next stroke ran ON TOP of finished satin: the straight lines across 宇 / 要 in the Rev A DST.
- **Workaround:** `kccore._patch_make_pattern()` execs a copy of `make_pattern` with a per-object count raster: hidden =
  later stops (`later > si` | `merged(si + 1)`) | objects of this stop not yet sewn; an object's footprint is removed
  the moment it is sewn (asserts on engine change).
- **Proposed fix:** the same in `dst2.make_pattern` (sewn tatami of the same colour may stay hidden, as now; sewn
  satin may not).
- **Check:** test: three satin columns A, B, C in one stop, A sewn first; no travel segment after A may lie inside A
  (DST read-back) — today it does.

## 12. Satin columns (kcsatin.py) — replaces notes 1 + 9
- **Problem:** satin on font OUTLINE tiles (Rev A) gave skipped rows (long diagonal stitches), fans at round ends, gaps at
  junctions and fixed-angle fallbacks (review item 1/6: "scribbled CN/JP strokes").
- **Fix (project):** every stroke is a COLUMN: skeleton graph of the glyph → branches (spurs pruned by reach, end forks
  pruned, short crossing bars kept, straight-through branches joined) → split at corners > 50° → one satin per stroke at
  the font's stroke width, free ends run to the outline (ray cast), junction ends stop on the crossing stroke's
  centreline (strokes overlap, no crumbs); zig-zag satin perpendicular to the smoothed centreline, an inner end that
  would move backwards pivots (rows never cross), round caps shrink as a semicircle, width profiles (tapered sparkle
  arms), rows > 7 mm split at staggered points. Used for text, rims, bars, dots (a disc = one round-capped column),
  oval ring (one closed column), sparkles.
- **Proposed fix:** `engine/columns.py` (`glyph_columns`, `ring_columns`, `column_pts`, `column_geom`) + region type
  `st="column"` in `build_object`, `art` transforms that move `col_cl` with the geometry.
- **Check:** golden glyph set (口 O 田 宇 要 球 ㅇ K): (a) no two consecutive stitches cross, (b) every satin stitch within
  20° of its centreline normal, (c) union of the columns covers ≥ 98 % of the glyph and spills ≤ 3 %.

## 13. Pattern welt (note 10) — still a BLOCKER for the pattern stage; keep-outs now pinned to the project welt
- The shared tree now has the merged hoodie block: `pattern.draft` drafts the Drum Island welt (38°, centre ≈ ±170 / 364),
  which lies on badges 03 and 04. `front.keep_geoms()` uses THIS mockup's slash welt (`front.WELT_R/L`) for the keep-out,
  as Rev A did, and keeps the engine welt as `welt_engine` for reference. Same proposed fix as note 10
  (`pattern.draft(size, welt=...)`).

## 14. Star placement: group regions per star, escalate, never drop on fronts (replaces note 4)
- A Rev B star is 2-3 regions (two arm columns + haze); `place_stars` moves all regions of a unit together, uses the
  bounding radius (concave sparkles), tries ≤ 8 mm, then ≤ 45 mm (fronts) / 20 mm (sleeves), then any free spot ≤ 2 x
  that radius scored by distance minus neighbour spacing. Result: 0 dropped on every piece and size (Rev A: 35 on the
  M fronts). Proposed: `qa.place_whole(groups, clip, avoid, tiers)` in the engine.

## Lesson proposals (coordinator merges into LESSONS.md)
- **A14** — Compare sheets drawn from the art regions hid what the machine sews (Rev A: scribbled strokes, hatched glow,
  scribble sparkles looked fine in the region render). Rule: compare sheets and spec-page art are rendered from the DST
  read-back only (every sewn stitch drawn). Check: reviewer re-renders one DST; `compare.py` imports no region renderer.
- **B25** — see note 11 (travel over already-sewn satin). Check: the test in note 11.

## 15. hoodie.Variant has no ORDER (pattern_out.write_dxf / plot_pdf read blk.ORDER)
- **Problem:** `PO.write_dxf(..., blk=hoodie.Variant(welt=...))` -> AttributeError 'Variant' object has no attribute 'ORDER'.
- **Workaround:** `BLK.ORDER = HD.ORDER` in pattern_kc.py. **Fix:** `Variant.ORDER = ORDER` (class attribute) in engine/hoodie.py.
- **Check:** test that write_dxf + plot_pdf run with a Variant.

## 16. A14 tracing at ~1 px/mm: fit each motif to its own silhouette (kctrace.py) — library candidate
- **Problem:** hand-typed motif sizes (bar width 3.4, star 11.6 / 14.0, sparkle span (ext + 1.5) px) failed qa.motif_match on
  86 of 211 badge + field motifs (IoU 0.3-0.6, sparkles 1.4-1.7x too wide, EN stars 20 % small).
- **Fix (project):** `kctrace.comps/snap` segment each colour family on a x4 bicubic upsample (half-max classes = the gate's),
  then `register_glyph(geom, ref_fn, aspect, starts, drop_frag, size_rule)` fits ANY motif geometry (shift / rotation /
  scale / stretch along its own axis, multi-start for 0/45° sparkles, IoU minus a penalty outside the gate's 0.8-1.25 size
  rule) and `apply()` carries the affine into column centrelines, widths (rims keep theirs), stipple runs and satin angles.
  Stars also search their inner-radius ratio and pit; the KR ring is traced (centreline + width per direction, width =
  2 x distance-to-edge) into a closed column with a width table. Font glyphs are registered the same way (IoU only).
- **Proposed fix:** `engine/trace.py` with these functions + tests; `qa.motif_match` callers get the same reference builder.
- **Check:** pre-check (art) and binding (DST) gate tables in gates.json; per-motif fit IoU in scene_meta.json "traced".

## 17. Pixel-centre convention (half-pixel bug, 0.4 mm on a 1 px/mm render)
- `scipy.ndimage.map_coordinates` (all mockup resampling) puts pixel i's centre at i; component centroids computed as
  (start + stop) / 2 or (index + 0.5) are corner-convention — every speck / traced motif sat 0.5 px (0.4 mm) down-right,
  which alone cost ~0.2 IoU on 3-6 mm motifs. Fixed in specks.py + kctrace.py. **Proposed:** one helper `px_centre()` in the
  engine and a test that a single-pixel dot maps back onto itself.

## 18. Gate reference classes vs pale threads / shading (gates.py)
- A pale lemon satin's lit core reaches r - b ~ 70 (the first yellow class cut at 70 split bars into two strips); the
  blue bars passed the first mint class (g - r > 45). Classes now: yellow r - b > 45 (complement of white |r - b| < 45),
  mint needs g >= b - 15. A 0.75 mm closing bridges the render's puff shading lines inside one motif.
- The front map is non-uniform (0.90 x 0.70 mm/px): references built through it squash round stars (h ratio 1.3) — field
  references are patches at the uniform motif scale S about each mapped speck. **Proposed:** `qa.reference(mock, map,
  local_uniform=True)` so every project builds the reference the same way.

## 19. hoodie welt + art: keep-outs from the drafted (graded) welt
- With the engine welt override the welt grades (x with the chest, y with the hem); Rev A's fixed project welt is gone.
  `front.keep_geoms` reads the drafted welt per size; badge 03 clears it on every size (min 6.4).

## Lesson proposals (cont.)
- **A16** — Hand-typed motif sizes are stand-ins too (A14): sizes, widths, angles and star shapes come from a fit to the
  motif's own silhouette; check = qa.motif_match on the shipped DST (gates.json), tables on the compare sheets.
- **A17** — Resample and trace in ONE pixel convention (centre = index); a half-pixel offset is 0.4 mm on a 1 px/mm mockup.

# Rev C (20 Oct 2026)

## 20. dst2.make_pattern hides flat travel under LATER puff stops (foam rule 6 broken on the file)
- **Problem:** the hidden-travel mask counts every later stop's fill, puff included. Flat stops sewn BEFORE the foam
  routed their travel under the puff footprint: after the glow was knocked out under the puff, the Rev C FR M file
  still had 12 flat needle points deeper than 1.25 mm inside the foam (Rev B: 110, mostly the glow itself, which is
  `nok` and was never knocked out).
- **Workaround (project):** `kccore._patch_make_pattern` swaps `cov.later` / `cov.raw` for flat stops to a copy with the
  puff footprint (shrunk 0.5 mm) removed; puff and 'top' stops see the full cover. Glow stipple runs are broken where a
  point lies, or a stitch crosses, 0.6 mm inside the puff edge (`art_size.knock_under_puff`).
- **Proposed fix:** `make_pattern(..., foam_keep=1.0)`: stops flagged `puff` (or keys ending `+foam`) do not count as
  later cover for earlier non-puff stops beyond `foam_keep - 0.5` mm inside their edge (the router raster, 0.2 mm px, and
  its 0.8 mm endpoint forgiveness let travel reach ~0.4 mm past its mask).
- **Check:** `kcstitch.foam_gates` on the written DST (`base_under_puff` = flat-stop needle points inside the puff minus
  keep + 0.25 mm, target 0): red on the Rev B FR M file (110), green on every Rev C file (prod_gates.json).

## 22. Sheer stipple runs drew straight lines across the halo (Rev B: up to 57 mm on FR M)
- **Problem:** two sources, both visible as straight glow-green lines on the stitch view (E01): (a) `kcmotifs.stipple_band`
  bridged every hop of its greedy walk with straight stitches, however long (57.5 mm on the Rev B FR M file); (b) the
  router treated an unsewn stipple run's footprint as hiding travel, so travel crossed the halo in a straight line
  (29.7 mm once the foam mask stopped travel hiding under the puff letters). `dst2.exposed_travel` did not see (a)
  (it is a block, not travel) nor (b) (runs are not cover, but the line was "hidden" under later puff satin in Rev B).
- **Fix (project):** hops > 3 mm start a new run (`max_hop`); sheer run objects never hide travel (kccore `_kc_init`).
  Cost: FR M trims 301 (Rev B file) -> ~500 (reported, fidelity first).
- **Proposed engine check:** a "straight chain" gate on the DST: no run of >= 4 near-collinear stitches longer than
  15 mm in a stop whose codes are all sheer / stipple (scratch check found 13 chains on Rev B FR M, 0 after the fix).

## 21. factory.requests_page drops the multi-hooping list once frames are confirmed
- With `frames_confirmed: true` the page says "Frames on file ... Files are split for these" and no longer lists which
  pieces need > 1 hooping (`test_confirmed_frames_are_not_asked_again` asserts that). Rule 8 wants the list on F1, so the
  project adds a "5b Hoopings on your frames" block. **Proposed:** always list pieces with > 1 hooping (as information,
  not a question), compare each piece with `single_hooping_confirmed_mm`, and update that test.

## 23. F1 page: product-specific sections (Rev D, founder 20 Oct 2026)
- Problem: `factory.requests_page` always prints "4 Quote basis" (and a price ask in the strike-off list); the founder asks
  the factory for prices separately and wants F1 to hold only what applies to the product. Chenille is already switchable
  (`prof chenille=False`), quote basis is not.
- Fix here (project): `pack.f1_pages` drops the quote-basis text elements and the "your price" clause from the SVG, with an
  assert so an engine text change cannot silently bring it back; F2 no longer asks to price puff hoopings.
- Proposed engine fix: `requests_page(..., sections={"quote": False, "chenille": False})` (default all on), and
  renumber the remaining sections. Check: `tests/test_factory.py::test_requests_page_omits_disabled_sections`.

## 24. Puff minimum width per stroke (Rev D)
- Problem: founder asked for puff on every sign part, "thin strokes flat, say which with the measured width". The engine has
  `house.yaml puff.min_w 3.0` but no per-stroke puff/flat decision for font text.
- Fix here: `kcmotifs.text_columns(puff_min=2.5)` splits each glyph's stroke columns by full width; a glyph puffs only if
  >= 50 % of its stroke length qualifies; decisions logged to scene META["puff"] -> G4 table. Strokes 2.5-3.0 are below
  the house minimum and listed for the strike-off (F2).
- Proposed engine fix: a `puff` part extractor step that applies `min_w` per column and reports the flat ones; the
  project's 2.5 vs house 3.0 should be settled by the strike-off (feed back as a LESSONS row with the measured result).

## 25. A failing A14/A15 gate still produced a pack (Rev E, PR #31 round 2)
- Problem: `gates.py` printed `BLOCKING 1` (JP top star, IoU 0.70 on the shipped size-M DST) but exited 0, so
  `build_all.py` built and shipped the pack. The fix comment quoted the scene fit's IoU (0.73, `best_star`), which is
  not the gate: the fit scored white ring + glint parts too, while the gate's mockup mask and stitched mask are the
  yellow family only.
- Fix here: `gates.py` exits 3 in binding mode when `blocking > 0` (prints each failing row); `build_all.py` stops with a
  message and also asserts `gates.json["blocking"] == 0` before building pages. `best_star(..., cols=)` fits a
  multi-colour star on the threads the gate measures. Proven red/green: iou_min forced to 0.95 -> 11 FAIL rows, exit 3;
  real run exit 0.
- Proposed engine fix: `qa.gate_or_die(res)` used by every project's pack build; LESSONS row "quote the gate number
  read from the DST, never the art fit". Check: a test that runs the pack entry point on a fixture with one FAIL row
  and asserts a non-zero exit and no PDF written.

## 26. Ringed / glinted stars need a motif, not scene constants (review PR #31 item 3)
- Problem: the JP top star (dark pit in a thin white ring, white glint streak through the centre) is built in
  `scene.py` with constants measured from this mockup: `_TOP_PIT_R 0.6`, `_TOP_RING_W 0.9`, `_TOP_GOLD_R 1.1`,
  `_TOP_GLINT ((-132°, 4.4 mm, 1.0), (48°, 2.9 mm, 0.8))`; the red star uses `pit_k 0.42` at 0.45 R. (Rev E's facet
  recolour window -158..-125° was wrong - the mockup's glint is a streak into the notch, not an arm facet - and is gone.)
- Proposed engine fix: `motifs.star_facets(..., centre=dict(pit_r, ring_w, ring_col), glints=[(ang, reach, w, col)])`
  with the pit/ring/glint measured by a generic `trace_star_centre(mask)` (dark-blob radius + pale annulus + pale
  streak directions), not typed. Check: a render test that a ringed star's gold-only IoU against a synthetic mask
  stays >= 0.70 and the pit stays unstitched (no stitch within pit_r of the centre).
