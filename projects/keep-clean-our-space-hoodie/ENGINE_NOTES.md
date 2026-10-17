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
