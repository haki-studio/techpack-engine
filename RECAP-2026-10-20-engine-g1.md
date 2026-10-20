# RECAP 2026-10-20 — engine G1: labels contract + generic primitives + labels→Parts compiler

Session c2fa35ef (builder), worktree `.claude/worktrees/tp-engine-g1`, branch `engine-g1`. Spec: docs/ENGINE_PLAN.md RE-PLAN (G1).

## Main baseline (recomputed from the DST, this worktree at 8a6a58d = origin/main)
`scripts/identity_check.sh` on main: probe dst 84ff50ea74938675 / pes 1ecd8f657db3f53a, M5 wb 449c14f6e8f693b6, Castle crop DST
**b0fcbbf67618a2d3** (identical to the M4c SCOREBOARD row, so the crop rebuild is reproducible). Crop gates: **2/11** (colours,
stack_parts). direction indep 51.0 % of 194 tiles (coverage 31 % < 50 %), chaos 23.8 %, coherence 81 fails, density 174 flags,
trims 38.0 /100 cm2, satin 1 blob (the B39 join), stack 5 / 12.97 cm2, separation 25 close, travel on sewn fill 5.78 m,
123,820 stitches. BENCH_m4s.md's numbers are pre-#14 (stale) — this row replaces them.

## Built
| piece | where | note |
|---|---|---|
| labels contract | `engine/digitize/labels/schema.py` | parts.labels.json: motifs → parts (primitive, hint polygons/seeds/except, tones, z, direction intent, colour, confidence, question, alternatives, params, rest); validates everything at once |
| vision sheet | `engine/digitize/labels/sheet.py` | the reference crop + garment-mm grid (and an overlay of a labels file) for whoever writes the labels |
| compiler | `engine/digitize/labels/compile.py` | labels → zone-like claims (highest z first, rest last, seeds) → primitive recogniser → Parts; low confidence → review questions (topic `label`) |
| primitives | `engine/digitize/primitives/{band,cord,stroke,lobe,plane,radial,dot,line}.py` | built on fall.cords, trunk.limbs/segments, cloud.lobes, stratum.mass_phase/bands_of, blossom.centres, partition. No subject code |
| directions | schema `label` source (audited from meta label_angle, independent like an answer); construct rule `long_axis` (outline bucket, rebuilt from geometry or the lobe outline `of`) | |
| house kinds | stroke, cord, band, band_grain, lobe, lobe_grain, lobe_shade, plane, plane_grain, radial, bead, line (`dir: label`) | |
| run.py | `labels:` in run.yaml replaces `zones:` | thread planner salience reads the labelled parts |
| B39 fix | dst2.make_pattern `block_roles` + `_over_rows`; compile.regions passes roles; `compile.write(join_guard=True)` | a hop between two blocks of one part never lies on its own sewn top rows → trim. svgrun passes join_guard=False (it moved one wb join to a trim: 15069 → 15076 stitches) so identity_check stays unchanged; opt in with `compile: {join_guard: true}` |

## Decisions
- **Label angles count as INDEPENDENT** (like an answer): the plan's table says "plane: constructed (independent)". To keep it
  judgeable, bench rows report label-angle tiles on their own line. Bands "along" use construct `axis` on each strip (independent,
  a position); lobes "outline" use `long_axis` (outline bucket, not independent); "grain" stays self-derived.
- Claims run highest z first exactly like zones (geometry from pixels inside the hint, A14).
- Sequencer kind sets extended for the generic kinds (bead = knot, radial = floret seam 0.3, line = crack, keep_small list) and a
  per-part `meta seam_mm` (lit lobe pieces knocked out of their lobe).

## Runs
| run | labels | result |
|---|---|---|
| r1 | first labels (session-written) | running |

## Open / next
- prove-the-guard rows for each new gate path (B39 done: red on the synthetic two-block part, green after; default-off proven).
- unsewn_only hidden travel on the crop (travel_on_fill gate).
