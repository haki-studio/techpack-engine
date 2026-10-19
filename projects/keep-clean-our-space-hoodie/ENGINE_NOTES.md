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
