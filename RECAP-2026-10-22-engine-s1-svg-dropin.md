# RECAP 2026-10-22: ENGINE_PLAN S1 — SVG drop-in (builder-techpack-engine-m2, branch engine-s1-svg-dropin)

Worktree `~/te-s1-svg` (off origin/main 1f03682). NO PR yet. Session handed off at the 8 MB size limit; pick up from "Next".

## Built (committed on the branch)
| piece | file | what |
|---|---|---|
| derived run config | `engine/digitize/extract/svg_auto.py` (new) | `normalize` (art scaled to --width-mm, canvas cropped, every shape numbered `data-s1`, unique group ids, gradients flattened + warned); `derive` (GEOMETRY ONLY, layer names never read): patch detection (rect + inset field) -> patch_border/field, ellipse clusters -> border_motifs, per-shape classes dot/knot/stroke/star/petals/fill (fill angle = long axis, declared); tints = lobe on a shape <= 8x its area; Isacord nearest per fill (CIEDE2000, unique, merge < dE 3, warn > 6); 60wt when a thread only sews lines <= 1 mm (skeleton width); questions with stable ids (patch / role / threads.weight / thread.merge), answers skip the question; `fill_config` mutates a palette-less cfg in place; `fabric_rules` |
| extractor | `extract/svg.py` | calls fill_config (no-config no longer crashes); role `shapes`; fill_map threads; petals(kind=); parts carry meta s1_el / s1_fam; fabric dot floor |
| runner | `svgrun.py` | fill_config at init; `apply_fabric`; `threads.allow_over` (>12 threads = gate fail, not crash); S1 questions first in questions.json; gate_file splits a mixed layer into [lines]/[shapes] families with their own reference (data-s1 filter, exact layer ids in auto mode); auto mode fills only <= 4 mm2 pinholes in the uncovered design mask (ring logos enclose bare fabric) — hand M5 runs unchanged |
| parser | `engine/svgart.py` | arcs (A, packed flags), strokes -> filled outlines (caps/joins/transform), `<style>` class fills, rgb()/CSS names, fill none dropped, `art_read` (whole-file parse vs cairosvg IoU), explicit `unsafe=False` on all 3 cairosvg calls, layer_mask(els=, exact=) |
| rules | `rules/fabrics.yaml` (new), `house.yaml` kind `graphic_fill` | twill/denim = house (no change); jersey/pique/fleece/sherpa PROPOSED deltas, warned on every run |
| CLI | `scripts/svg2dst.py` (new) | svg2dst/1 contract (docs/SVG2DST.md): result.json passes contract.check_result; hard gates engine_real, art_read >= 0.98, fits_hoop (frame-16), threads <= 12, max stitch <= 7.5, has stitches, exposed_none, uncovered_none; soft centreline/motifs/coherence/questions |
| fixtures | `tests/fixtures/svg_s1/` | logo_badge (px units, CSS classes, stroked ring, arcs, no groups), lettering_haki (DejaVu Sans Bold outlines, viewBox only), illustration_wave (gradient, lobed cloud, bands, stroked crests + birds); `make_fixtures.py` regenerates |

## Proof so far (svg2dst, NO run.yaml, width = the art's own width, twill, 300x300)
| element | M5 hand config: st / trims / stops, gates | S1 drop-in: st / trims / stops, gates |
|---|---|---|
| wb waistband | 15,069 / 161 / 10, 7/7 | 15,136 / 161 / 10, 7/7 (ok, 2 questions: patch, 60wt black) |
| coin | 10,525 / 84 / 11, 7/7 | 10,597 / 88 / 11, 7/7 (ok) |
| spill (facing) | 3,609 / 58 / 7, 7/7 | 3,608 / 58 / 7, 7/7 (ok, 0 questions) |
| starP + starY | 281+281 / 1+1 / 2+2, 7/7 each | 562 / 1 / 4 (one file, both stars), 7/7 (4 star-vs-petals questions, default radial) |
| logo (unseen) | - | 4,598 st, 4 trims, all hard gates PASS |
| lettering (unseen) | - | 1,910 st, 32 trims, all gates PASS |
| illustration (unseen) | - | 16,507 st, 20 trims, all hard gates PASS (1 open 60wt question) |
NOTE: these numbers predate the last classifier changes (lobe gap_sd, small-shape -> satin, exact ids): RE-RUN all 7 before quoting.

## Pass 2 (builder replacement, 22 Oct night): crescent fixed, tests, parity
| what | where | why |
|---|---|---|
| per-shape centreline gate | `svgrun.gate_file` (auto only), `qa.centreline_match(profile=True)` | the pooled [lines] row passed the one-width crescent; per shape + thick end (ratio90) on TAPERED refs only (w90-w50 >= 0.4 mm; on even lettering p90 is junction noise) |
| window excludes other shapes' art | gate_file `full & ~ref` | crossing ring + same-thread fill beside the bar leaked into its window |
| columns per source element | `_shapes` strokes keyed (fill, element) | ring + bar crossed and were one polygon |
| width = length-weighted median (S1 only) | `stroke_width(weighted=)` | coin ぺ: 3 ticks out-voted the main stroke -> 0.85 mm, ratio 0.57 |
| taper profile | `extract/svg.py::_taper` | only: one open stroke, length >= 3x belly, belly >= 2 mm, < half samples near belly, narrow ends + central belly. First cut profiled 70 wb glyph strokes (2 exposed) and the i stems (LESSONS A35) |
| >12 colours | `factory.check_threads(raise_over=)` | the S1 "gate fail not crash" claim was false: compile raised; the new test caught it |
| tests | `tests/test_svg_s1.py` (21), worker tests autouse REAL_CLI off + real round trip | red: no-config on origin/main (ValueError empty palette, not KeyError); per-shape rows at d0ae3ca (1 pooled row) |
| parity | `projects/konpeito-jeans/bench/PARITY_S1.md` + `bench/s1/*.png` | all 7 hard 8/8; lettering 8/11 per-shape soft (open finding) |

Dead ends: width-scaled skeleton spur pruning (the bar miss was the neighbour fill, not spurs) - reverted.

## Known defect found by LOOKING (FIXED in pass 2)
Logo crescent (tapered white shape) is sewn as ONE-width column (column role = one needle width per layer, the M5
lettering rule), so it reads thinner than the art; the [lines] centreline row pooled it with the navy ring (w_ref 3.55)
and passed. Fix: (1) centreline rows per thread within a family; (2) tapered strokes (skeleton width max/median > ~1.6):
use column_points' `prof` width profile (techniques/column_satin.py) or sew as fill when T >= 4 mm. Red-then-green test.

## Next
1. Fix the crescent defect above; re-run 4 Konpeito + 3 unseen; check panels by eye (out: $job tmp/s1/*/panel.png — regenerate under projects/... or docs/s1/ for committing previews).
2. Tests `tests/test_svg_s1.py`: no-config extract red on main (KeyError 'palette') -> green; layer ids renamed -> same parts; classifier synthetic shapes; fill long-axis angle; Isacord dE + unique; question/answer round trip (answered disappears, bad option -> exit 2); >12 colours = gate fail not crash; normalize px -> mm; arcs/strokes/CSS parse vs cairosvg (art_read >= 0.98); fabric twill = identity; svg2dst result passes check_result. Update `tests/test_svg2dst_worker.py`: the http fixture + test_http_auth_and_errors must monkeypatch REAL_CLI to nonexistent (the real CLI now exists and wins), add a real-engine round trip.
3. Full suite (`~/.venvs/techpack/bin/python -m pytest -q tests`, check free RAM / heavy-jobs first); `scripts/identity_check.sh` (M5 wb 449c14f6e8f693b6 must be unchanged: hand runs untouched); orphan gate on new files.
4. Parity table file `projects/konpeito-jeans/bench/PARITY_S1.md` + previews (commit PNGs); docs: SVG2DST.md status (S1 real), services/svg2dst/README (stub only until merge, then delete SVG2DST_ALLOW_STUB), ENGINE_PLAN S1 done, LESSONS rows (A?? S1 geometry-only roles; prefix-id masks; ring-hole uncovered).
5. PR --base main, independent reviewer posts REVIEW: APPROVE <sha>, DONE to lead-eng-techpack-engine-m2 with PR link + sha + gate table.

## Pass 2 verification
- Full suite: 401 passed (`~/.venvs/techpack/bin/python -m pytest -q tests`).
- identity_check: probe 84ff50ea74938675 / 1ecd8f657db3f53a, M5 wb 449c14f6e8f693b6, crop 911978994b664110 (all unchanged).
- Open finding: lettering fixture 8/11 per-shape centreline (both i's 0.80-0.82, a bowl ratio90 0.73), soft; see PARITY_S1.md.

## Pass 3 (lead TASK: lettering follow-up, branch engine-s1-lettering off 9711ed5)
- i's 0.80-0.82 = gate artefact (zig-zag edge spurs survive a 0.6 mm prune) -> per-shape prune at 0.6 x shape width (`qa.centreline_match(profile=True)`).
- a bowl ratio90 0.73 = real (one width per glyph) -> per-stroke width in S1 (`extract/svg.py` column()); now 0.80, on the limit.
- Reviewer note: cut-out moved to `svgrun.cut_other_shapes`; `test_cut_other_shapes_is_load_bearing` switches it off -> bar row ratio 1.4, fails.
- Lettering 11/11; Konpeito 4 unchanged; fixtures gate_i_ref/dst.png (real read-back masks), gate_bar_beside_fill.svg.
