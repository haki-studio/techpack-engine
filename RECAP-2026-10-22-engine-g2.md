# RECAP 2026-10-22 — engine G2: session vision labels on the unseen Koi FR (zero subject code)

Session f5e7f669 (builder-techpack-engine-g2, lead lead-eng-techpack-engine-m2), worktree `~/te-g2`, branch `engine-g2` off
origin/main 1f03682. Spec: docs/ENGINE_PLAN.md RE-PLAN G2. Engine proof only: product packs paused, Koi pack NOT rebuilt.

## Plan
1. Restore the Koi FR bench (crop x -220..-50, y 30..300, mockup-only gate reference) from 9735857^ (removed with the trial's
   subject code; bench data is project data, not subject code).
2. Vision sheet (digitize.labels.sheet) -> the session looks once and writes `projects/koi-blossom-hoodie/bench/labels_FR.json`:
   fish = lobe (body) + band (cyan/red stripes) + radial (fins/tail) + dot (eye); flora = lobe/stroke/cord/radial.
3. run_fr_labels.yaml -> digitize.run --no-api; gate table (A14/A15 motif_match + uncovered, orphan gate) vs Rev B; side by side.
4. Any primitive fix in engine/ with red-then-green tests; grep proof of no koi/fish code; identity_check unchanged.

## Log
- 08:0xZ worktree made; read ENGINE_PLAN G2, PR #37 body, LESSONS A14-A16/E rows, G1 recap. Restored bench files.
- Engine fix (generic, red->green, tests/test_digitize_g2.py): radial `params.shape: "traced"` = a FAN (the root seed's whole
  traced cell, rays from the root: tails, fins, rays) — the lobed floret mode capped r at the distance to the cell edge, so a
  root seed on a shape's narrow end made no fan. dst2.radial_satin `_fan_order`: a fan's rays start after the empty sector
  (the sweep wrapped across the fan = 17 mm stitch), stubs < 1 mm behind the root dropped, long hops along the side cut <= 6 mm.
  Florets (no empty sector > 30 deg) return their rays untouched (identity).
- Restored Koi bench from 9735857^ (bench.json, registration*.json); new run_fr_labels.yaml, labels_FR.json (session-written,
  5 fish = radial tail + lobe body + band stripe + dot eye; flora lobes + cord), g2_compare.py (from trial_compare.py +
  fish graded vs the mockup silhouettes too + orphan gate). Rev B FR M copied from the Rev B zip to out/revB (git-ignored).
- Run 1: G2 fish vs tetra ref 3/5 (Rev B 4/5), vs mockup fish 5/5 (Rev B 0/5), flora 23/34 (12/34), uncovered 470 mm2 (741).

## Run 1 gate table (crop x -220..-50, y 30..300, mockup-only references; bench/g2_gates.json)
| gate | Rev B delivered | G2 labels (run 1) |
|---|---|---|
| fish motif_match vs founder tetra @0.82 (A14) | 4/5, IoU 0.71 | 3/5, IoU 0.68 |
| fish motif_match vs mockup fish silhouettes (A14) | 0/5, IoU 0.54 | 5/5, IoU 0.86 |
| flora motif_match (A14) | 12/34, IoU 0.59 | 23/34, IoU 0.66 |
| uncovered >= 25 mm2 (A15) | 9 gaps, 741 mm2 | 12 gaps, 470 mm2 |
| sewn off the reference | 1934 mm2 | 790 mm2 |
| orphan fragments (target 0) | 26 | 5 (stops 14/15/17: royal + cornflower slivers by the lower flower/leaves) |
| direction OK / chaos | 21.8 % / 20.4 % | 77.9 % / 7.9 % |
| density flags (p95) | 19 (7.43) | 10 (6.81) |
| trims /100 cm2 | 107.8 | 95.4 |
| satin blobs | 90 | 8 |
| stack max / flags | 3 / 0 | 4 / 5 |
| stitches in crop | 21,937 | 19,438 |
| bench verdict | 1/8 (colours) | 1/8 (colours); engine own 2/11 |
Looked at the side by side (bench/g2_side_by_side.png): fish read as fish (fan tails, red stripe, body); bodies come out
partly grey (tone "lit" picked lavender); the upper lily is a cross-hatched mess (lobe grain + shade layer at +20 deg).

## HANDOFF (session hit the 8 MB size limit after run 1) — next builder, exact next steps
State: branch engine-g2 pushed (commit below). Worktree ~/te-g2. Rev B FR M copied to out/revB from the desktop checkout's
out/HAKI_KOIB_RevB_files.zip (git-ignored; re-extract if missing). Machine: check `~/.claude/company/bin/heavy-jobs` first.
Run: `cd ~/te-g2 && PYTHONPATH=engine:projects/koi-blossom-hoodie ~/.venvs/techpack/bin/python -m digitize.run projects/koi-blossom-hoodie/bench/run_fr_labels.yaml --stages extract,review,plan,compile,gates,panel --no-api`
then `PYTHONPATH=engine ~/.venvs/techpack/bin/python projects/koi-blossom-hoodie/bench/g2_compare.py` (~1 min each).
1. Run 2 labels (edit bench/labels_FR_src.py, regenerate labels_FR.json): fish bodies `colour: kb_white`; upper lily lobe
   intent outline + layers "lit" (no shade cross-hatch), lobe_sep_mm ~10, min_lobe_mm2 ~60; lower flower layers none
   (stack 4). Re-run both commands; look at g2_side_by_side.png once.
2. Orphans 5 -> 0: hits are royal/cornflower slivers in the lower-left foliage (flower_lower / leaves_petals) sewn in a
   different stop than the block they touch; try one motif for that area or raise min sizes; if it needs an engine fix,
   red-then-green in tests/test_digitize_g2.py.
3. Full suite (`~/.venvs/techpack/bin/python -m pytest -q tests`, ~400 expected pass) + `scripts/identity_check.sh` (must be
   unchanged: florets keep their ray order, _fan_order returns them untouched; if a hash moves, explain it). Mutation proofs:
   delete `fan = P["shape"] == "traced"` branch -> test_radial_traced_fan red; `_fan_order` return segs always -> 2 red.
   LESSONS row A?? (G2), HANDOFF.md/ENGINE_PLAN G2 status line, PR (never merge) with the gate table + side-by-side,
   reviewer subagent REVIEW: APPROVE <sha>, confirm remote head, DONE to lead-eng-techpack-engine-m2.
Founder question to carry in the PR: the fish gate reference is the founder's TETRA at 0.82 x (Rev B's), but the mockup
governs (founder 2026-10-20) and G2 traces the mockup fish. G2 wins on mockup fish 5/5 vs 0/5, loses on tetra 3/5 vs 4/5.
If the founder wants tetras, that needs a generic "motif reference image" in the labels contract (G3 scope).
No koi/fish/tetra/lily word added under engine/ (grep of the engine diff: 0 hits).
