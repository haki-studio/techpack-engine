# RECAP 2026-10-22: engine G4, the founder's tetra governs the Koi fish

Session d2f588bb (builder-techpack-engine-g4, lead lead-eng-techpack-engine-m2). Worktree `~/te-g4`, branch `engine-tetra-ref`
(off engine-g3, then main merged in after #51 landed; PR base = main per the lead). Engine proof only: product packs paused,
Koi pack NOT rebuilt. Python: `~/.venvs/techpack/bin/python`; check `~/.claude/company/bin/heavy-jobs` = 0 before suite/render.

## Why
Founder ruling 2026-10-22T15:00Z on card techpack-koi-fish-reference, verbatim: "we want the tetra". G3's `reference` field only
changed the GRADE, and only by shape: the koi-coloured fish still passed 3/5 against the tetra, and nothing made the sewing follow it.

## PR 1 (this branch)
**Engine (generic, no subject code):**
1. `labels/schema.py`: `reference.governs` = subset of ["silhouette", "colour"], default [] (= G3 grading only). `LS.governs(ref)`.
2. `labels/refsource.py` (new): `composite(ref, labels, dir, palette, bare)` puts a governing picture into the EXTRACTION source
   (`Run.ref()`): colour = the picture's RGB inside its pixels; silhouette = the motif's windows outside its pixels read as the first
   bare tone; close-up weight 0 there. The gate reference (bench registration) is never composited. Silhouette with no bare tone = error.
3. `labels/refgrade.py`: `place()` (picture + its RGB on any grid); `tone_groups()` (palette tones joined within COLOUR_DE 12
   CIEDE2000, transitively); `colour_grade()` per colour group: colour_match >= 0.70 AND every group holding >= 3 % of the picture
   recalled >= 0.50 within 1.5 mm. A colour-governed unit's row: shape_ok, colour_ok, groups, ok = both. `grade(..., stops, palette)`.
4. `run.py`: motif_reference passes the stop masks + thread hex per stop (plan stops via compile.regions; raises if the DST has more
   stops than the plan); plan meta `reference_governs` lists what was recoloured/bared.

**What the tetra governs (stated):** outline + colours of each fish. The mockup keeps position, heading and count (the labeller
places each picture's box at the mockup fish pose); size = 0.82 x the mockup fish length (founder decision 19 Oct, unchanged).

**Koi side (project code):** `refmask.fish_ref(sample=True)` adds the photo colours + template coordinate t; `bench/make_tetra_refs.py`
writes coloured RGBA `refs/tetra_fish{1..5}.png` (boxes unchanged) + per-fish tetra anatomy windows (whole fish, body t < 0.80,
tail t >= 0.80 where the red stripe ends, root seed, eye = darkest head blob). `labels_FR_src.py`: default = tetra fish (tail radial,
silver body lobe, blue shade lobe, red band, cyan band, eye dot; reference governs both); `--fish-ref mockup` = the G3 koi labels,
now `labels_FR_mockup.json` (byte-identical to the old labels_FR.json). Removed `labels_FR_tetra.json` + `run_fr_labels_tetra.yaml`
(G3 grading-only variant, superseded). `bench/g4_compare.py` grades Rev B / G3 / G4 with the thread per stop from each PES.

Dead end: colour rule per palette TONE (not group): the photo's shading spreads over ~9 tones, so the right answer failed (0/5).
Dead end: fish body tones = light only: the photo's blue belly shade went to the leaf part; fixed with a `shade` part per fish
(chaos 7.1 % → 5.3 %). Edge erosion in the colour grade: no effect on real data or tests → removed.

## Tests
`tests/test_digitize_g4.py` 14 pass. Red on the G3 engine (230f218, new labels/refs copied in): 11 fail, 3 pass (schema-rejection
cases G3 also refused). Mutations (each red): no group-recall rule 2, ok ignores colour 2, composite skips colour 3, skips bare 2,
no tone groups (COLOUR_DE 0) 1. Key real-data test: on the committed tetra pictures, koi-coloured fish (silver + red in the mockup koi
stripe windows, no cyan) fail 5/5 with shape ok (cyan recall 0); the tetra sewn in its nearest threads passes 5/5.

## Bench (bench/g4_table.md, crop x -220..-50, y 30..300)
See the table in the PR body / g4_table.md (Rev B | G3 koi | G4 tetra).

## Open / next (PR 2 per the lead's brief)
- trims rose 53 → 93 in the crop (each fish now sews 5-6 colours: body, shade, red, cyan, eye, tail); chaos 5.3 % (> 5 %).
- belly shade sews bluer (cornflower) than the photo's lavender-blue: the photo quantises to corn; consider a lav/ice choice.
- PR 2: (a) chaos < 5 % (Castle no worse), (b) fewer trims/100 cm2 with orphans 0, (c) shading via the tone trace.

## HANDOFF (session d2f588bb hit the 8 MB session limit)
State: branch `engine-tetra-ref` pushed (main eab31190 merged in, no rebase). Koi FR G4 run in
`projects/koi-blossom-hoodie/out/digitize/KOI_FR_M_labels` (git-ignored; DST sha256 32533f4f292d8170 on the pre-#51-merge head;
re-run if needed), G3 baseline in `out/digitize/KOI_FR_M_labels_g3`, Rev B + g2run3 in `out/` (copied from ~/te-g3; copy again if missing).
Next builder, in order:
1. heavy-jobs = 0 → `~/.venvs/techpack/bin/python -m pytest -q tests` (full suite) + `bash scripts/identity_check.sh`
   (Castle crop / probe / wb must be unchanged: the Castle run has no labels, so refsource can't touch it; if a hash moves, explain it).
2. `gh pr create --repo haki-studio/techpack-engine --base main --head engine-tetra-ref`, body = what/why (founder quote), what the
   tetra governs, the g4_table.md table, red/green + mutation counts, side-by-side paths, risk (engine: labels contract additive,
   default [] = unchanged). No "merge #51 first" line (#51 merged).
3. Spawn an independent `reviewer` subagent → it must comment `REVIEW: APPROVE <full head sha>`; push fixes, re-review; then
   `git ls-remote origin engine-tetra-ref` = the approved sha = `gh pr view --json headRefOid`. SendMessage
   lead-eng-techpack-engine-m2: `DONE techpack-engine-g4 — PR 1 ...` with link + sha + bench numbers.
4. Then PR 2 per the lead's brief (chaos < 5 %, fewer trims with orphans 0, shading), `--base main`, "Merge PR <n> first" if PR 1 is open.

## Session g4b (continues d2f588bb)
- Full suite on afee22a: 528 pass, 1 fail = G1 subject-word guard flagged `refsource._window_mask` ("window"). Renamed `_hint_mask` (cb06c25); g1+g4 tests 53 pass.
- identity_check on cb06c25: probe + wb unchanged; Castle crop run KILLED by system low memory (not a failure). Re-run the crop only when RAM allows. cb06c25 pushed.
- PR 1 = https://github.com/haki-studio/techpack-engine/pull/52 (head cb06c25). Lead TASK: crop identity PENDING in body; re-run crop when avail >= 4 GB + heavy-jobs 0, edit body, THEN reviewer → verify heads → DONE. Then PR 2.

## Session g4c
- identity_check on cb06c25: probe 84ff50ea/1ecd8f65, wb 449c14f6, Castle crop e5b64b20d56db7e8 (126,230 st / 154 trims): ALL unchanged vs main.
- Full suite on cb06c25: 529 passed. PR #52 body updated (no PENDING left).
- Lead TASK (re-prioritised): finish PR #52 to DONE, then STOP — do not start PR 2 until a new TASK. Heavy commands `nice -n 19` + heavy-jobs 0 only.
