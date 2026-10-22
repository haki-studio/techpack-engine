# RECAP 2026-10-22: engine G3, per-petal label windows + motif reference image

Session dc908122 (builder-techpack-engine-g3, lead lead-eng-techpack-engine-m2). Worktree `~/te-g3`, branch `engine-g3`
off origin/engine-g2 (PR #49, approved, unmerged). Engine proof only: product packs paused, Koi pack NOT rebuilt.
Python: `~/.venvs/techpack/bin/python`. Check `~/.claude/company/bin/heavy-jobs` = 0 before suite/render.

## Done (commit 73053ef, pushed)
1. **`hint.each`** (labels contract, `engine/digitize/labels/{schema,compile}.py`, `primitives/__init__.py`, `run.py` `_claims`):
   each window of a part is its own piece/claim, zone `<pid>#<n>`, z + 0.001·(n-1) in listed (back→front) order.
   So the front piece claims an overlap first and the back piece sews first. Meta `label` stays the part id (one review
   question, one answer applies to every piece); meta `label_piece` = n. Schema: bool only, >= 2 windows.
   Why it's needed: a soft mockup area has no pixel edge between petals, so one window gave flat slabs (G2 runs 3-4).
2. **`reference: {image, box}`** on a motif or a part (`labels/schema.py`, new `labels/refgrade.py`, `run.py`
   `Run.motif_reference` → gates.json `motif_reference`, reported but not a verdict line). The default unit reference =
   the MOCKUP (bench registration evidence pixels in the unit's windows ∩ its tones, bare excluded). With `reference`,
   the unit is graded on that picture instead: RGBA alpha > 127 (else pixels away from the corner colour), stretched into
   `box` garment mm; the path is relative to the labels file. A part with its own reference becomes its own unit. A missing
   image raises FileNotFoundError (never falls back to the mockup silently). Grading only: extraction ignores it (test).
3. **Rule-3 separation float fix** (`direction.py` `ANGLE_EPS = 1e-6` in `separate` clash/ok and `separation_report`):
   DirSpec rounds to 0.01°, so a turn to exactly 15° read back as 14.999999999999986 and FAILED the separation gate
   (found on the G3 Koi run: petals.031 vs leaves lobes.061), and a second pass "turned -0.0 deg".
4. Tests: `tests/test_digitize_g3.py`, 18 pass. Red first: 13 of 16 initial tests failed before the code (the 3 that
   passed are guards on unchanged behaviour: no-`each` = one slab, `except` on the parent, reference ignored by
   extraction). Separation test red (`close == 1`) before the fix. Note: one test failed at first on a bad fixture
   (a smaller reference passes under near_mm); I fixed the fixture, not the engine.
5. Koi labels (`bench/labels_FR_src.py` → `labels_FR.json`): the upper lily = `petals` lobe with `each`, 5 windows
   (top, upper right, left, lower left, lower right) + `heart` lobe (round window, `layers: lit`, `min_layer_mm2: 15`,
   tone dominant → cobalt heart, white/lav cups at the heart's angle). The lower flower gets `except` += `flower_upper.petals`.
   Dead ends: separate `heart` dark + `cups` parts (chaos 5.5 %); radial heart (radius 9.2 mm > 4 mm floret exemption, chaos 5.9 %);
   heart window with a flat top edge (cut a hard line across the top petal).

## Gate table (bench/g3_compare.py → bench/g3_table.md, g3_gates.json; crop x -220..-50, y 30..300, mockup refs)
| gate | Rev B delivered | G2 run 3 (one lily window) | G3 (one window per petal) |
|---|---|---|---|
| fish vs founder tetra @0.82 (A14) | 4/5, IoU 0.71 | 3/5, IoU 0.68 | 3/5, IoU 0.68 |
| fish vs mockup fish (A14) | 0/5, IoU 0.54 | 5/5, IoU 0.86 | 5/5, IoU 0.86 |
| flora motif_match (A14) | 12/34, IoU 0.59 | 23/34, IoU 0.66 | 22/34, IoU 0.67 |
| labelled motifs vs their reference (G3 refgrade) | mockup 3/9 IoU 0.66 | mockup 8/9 IoU 0.88 | mockup 8/9 IoU 0.88 |
| upper lily vs mockup (refgrade unit) | IoU 0.86 ok | IoU 0.88 ok | IoU 0.89 ok |
| upper lily: 15° angle bins >= 8 % / top bin | 5 / 14.4 % | 3 / 37.9 % | 4 / 29.0 % |
| uncovered >= 25 mm2 (A15) | 9 gaps, 741 mm2 | 12, 467 | 11, 445 |
| sewn off the reference | 1934 mm2 | 793 | 749 |
| orphan fragments | 26 | 0 | 0 |
| direction OK / chaos | 21.8 % / 20.4 % | 69.4 / 4.0 | 75.5 / 5.1 |
| density flags (p95) | 19 (7.43) | 5 (6.39) | 5 (6.78) |
| trims /100 cm2 | 107.8 (148) | 39.8 (49) | 43.4 (53) |
| stitches in crop | 21,937 | 16,764 | 18,257 |
| bench verdict | 1/8 (colours) | 2/8 (chaos, colours) | 1/8 (colours) |
Honest read: G3 loses the chaos gate by ~1 tile (13/253, max 5 %). 4 of the 13 tiles sit where the petals meet the
heart: each petal now sews along its own axis, which is the point of the change. G2's one slab had no such junction.
Looked at bench/g3_side_by_side.png + g3_zoom_lily.png myself: the lily now reads as 5 petals round a dark heart
(G2: two flat slabs). Gaps: the top/lower-right petals pick lavender (tone "lit") where the mockup is near-white; fills are
flat tatami without the mockup's soft shading; the heart is a bit boxy.
G2 run 3 baseline = te-g2 out (labels sha db80930968d88a92 = commit 1c12c05), copied to out/g2run3 (git-ignored).

## Done by the next builder (session 49a881a8, same branch)
1. **Tetra wiring (D2, Koi side):** `bench/make_tetra_refs.py` writes `bench/refs/tetra_fish{1..5}.png` (RGBA, alpha = the
   refmask.fish_ref mask cropped to its bbox, 5 px/mm) + `refs/tetra_refs.json` (box = pixel edges in garment mm). Six poses on
   FR; pose 5 (y 403, below the crop) overlaps no fish window and is skipped. `labels_FR_src.py --fish-ref tetra` →
   `labels_FR_tetra.json` (reference on the 5 fish motifs). `labels_FR.json` is byte-identical (stays on the mockup until
   founder card techpack-koi-fish-reference). `g3_compare.py --labels bench/labels_FR_tetra.json` → `g3_table_tetra.md` /
   `g3_gates_tetra.json` (suffixed, so the mockup table is never overwritten): G3 fish vs tetra image 3/5 IoU 0.69 (old tetra
   column 0.68), G2 3/5 0.69, Rev B 4/5 0.71.
   **DST proof:** `bench/run_fr_labels_tetra.yaml` (labels = tetra, out_dir `..._tetra`) and a fresh `run_fr_labels.yaml` run
   both give DST sha256 `54643085e60aa153...`, the same as the earlier G3 run. A labels reference changes the grade, not the sewing.
2. **Mutation proofs** (tests/test_digitize_g3.py, 18): drop `each` expansion → 3 red; drop `piece > 1` in questions() → 1 red;
   grade ignores `ref` → 2 red; no ANGLE_EPS in separation_report → 1 red; no ANGLE_EPS in separate() clash → 1 red. All restored.
   Subject-word grep `git diff origin/engine-g2 -- engine | grep -iE "koi|fish|tetra|lily|petal|flower"` = 0 (one comment in
   labels/schema.py said "per petal / panel", now "per piece").
3. **Full suite** 404 passed. **identity_check:** probe 84ff50ea/1ecd8f65 and wb 449c14f6 unchanged; **Castle crop moved on
   purpose** 91197899 → e5b64b20 (126,219 → 126,230 stitches, same 154 trims, same verdict lines, same separation 25 close).
   Cause proven: with ANGLE_EPS = 0 the crop is back to 91197899. Diff of parts.json: one part, foliage.306 (lit side of
   clump foliage.229) — the exact 15.00 deg candidate from foliage.305 read back as 14.99999 and was rejected, so it turned
   +10.3 deg; now it takes the nearest legal turn, +5.3 deg. scripts/identity_check.sh expected hash updated.
4. LESSONS A38 (numbered A34 before merging main + S1 lettering), docs/ENGINE_PLAN.md G3 status, HANDOFF.md G3 line.

## HANDOFF (superseded: steps 1-4 done above)
State: branch engine-g3 @ 73053ef pushed. Rev B + G2 run 3 DSTs are in projects/koi-blossom-hoodie/out/{revB,g2run3}
(git-ignored; copy from ~/te-g2/projects/koi-blossom-hoodie/out if missing). Re-run:
`cd ~/te-g3 && PYTHONPATH=engine:projects/koi-blossom-hoodie scripts/heavy.sh ~/.venvs/techpack/bin/python -m digitize.run projects/koi-blossom-hoodie/bench/run_fr_labels.yaml --stages extract,review,plan,compile,gates,panel --no-api`
then `... projects/koi-blossom-hoodie/bench/g3_compare.py [--labels bench/labels_FR_tetra.json]`.
1. **Tetra wiring (D2, Koi side):** write `bench/make_tetra_refs.py`: for each pose in `refmask.fish_ref("FR")` (project code,
   5 px/mm on BB["FR"] = (-300,-60,0,520)), crop the mask to its bbox, save RGBA `bench/refs/tetra_<fishN>.png` (alpha =
   mask) + box in garment mm (bbox px / 5 + BB origin). Assign each pose to the fish motif whose windows it overlaps most.
   Add `--fish-ref tetra` to labels_FR_src.py → `labels_FR_tetra.json` with `"reference": {"image": "refs/tetra_fishN.png", "box": [...]}` on each
   fish motif. Default labels_FR.json STAYS on the mockup (founder card techpack-koi-fish-reference pending).
   Proof: `g3_compare.py --labels bench/labels_FR_tetra.json` → fish units show reference = refs/... with IoU ≈ the
   old tetra column (0.68). Also run digitize with a copy of run_fr_labels.yaml whose labels = labels_FR_tetra.json and
   out_dir another dir: the DST sha must equal the mockup-labels DST (a labels edit changes the grade, not the sewing).
2. Mutation proofs (record red counts): drop the `each` expansion in compile.resolve; drop `piece > 1` in questions();
   make grade ignore `ref` (always mockup); drop ANGLE_EPS in separation_report; drop it in separate() clash.
   Then the subject-word grep (`git diff origin/engine-g2 -- engine | grep -iE "koi|fish|tetra|lily|petal|flower"` must
   show 0 code hits; test_primitives_and_labels_carry_no_subject_code covers labels/refgrade.py too).
3. heavy-jobs = 0 → full suite (`~/.venvs/techpack/bin/python -m pytest -q tests`, ~404 + 18) + `bash scripts/identity_check.sh`
   (expect probe 84ff50ea/1ecd8f65, wb 449c14f6, crop 91197899. Castle is a zones run, so `each`/refgrade can't touch it.
   ANGLE_EPS could only move it if a Castle pair sits at exactly 15.00°; if the hash moves, explain it).
4. LESSONS row (G3: soft areas need per-piece windows; a gate tolerance must match the stored precision), ENGINE_PLAN
   G3 status line, HANDOFF.md line, this RECAP; PR base engine-g2 (retarget to main after #49 merges), body = the
   gate table + side-by-side paths; reviewer subagent → REVIEW: APPROVE <sha>; check remote head = sha; DONE to the lead.
