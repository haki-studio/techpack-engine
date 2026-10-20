# HANDOFF — /techpack batch (updated 2026-10-19 ~17:30, coordinator session d3fafdf9)

Read `LESSONS.md` first, especially A11–A15. A14/A15 are new today: trace every motif, and mask garment details. The gates are `qa.motif_match` and `qa.uncovered`, tested in `tests/test_fidelity_gates.py`. Then read this file and `RECAP-2026-10-19-techpack-batch-coordinator.md` (the decision log).
Team progress page (private): https://claude.ai/artifact/QzuNQUtk48maLYnWnWt6Aq. Generator: session scratchpad `gen2.py`, regenerate from out/ DSTs.

## Priorities (founder)
1. **Konpeito black jeans: full tech pack DUE TONIGHT 19 Oct.** Silhouette = Hidden Inventory pants (PLM size chart row 9a469aee…, inches, waist sizes 26–40; back rise/thigh/knee/outseam missing → factory pack "tech pack CAMOPANTS1.pdf" in PLM private storage, founder to download). The front-leg embroidery artwork is missing → keep the page with MISSING boxes. New: back-pocket "haki" + konpeito stars (inputs/back_pocket_haki.png), scaled so the stars match the other konpeito. Embroidery files for every embroiderable part.
2. **Wave jacket: embroidery-only sampling package, size M**, for Mandy (factory). Rev A reviewed → NOT ready (REVIEW_OPEN.md: placement plot, match marks, sleeve fold seam, foam/stripe structure). Founder decisions:
   - collar, not hood
   - the wave must be SEAMLESS (true wrap across armhole, side seams, zip, 3 mm short + notches, no armhole topstitch)
   - jacket revision = fabric colour + hardware colour + probably no cuff/hem rib; shoulders, armholes and sleeves unchanged → re-check thread colours once the new fabric colour is known
3. Everything else: normal priority.

## Products
| Product | State | Next |
|---|---|---|
| wave-jacket | M package Rev A reviewed: not ready | Rev B (wrap + REVIEW_OPEN), re-review |
| konpeito-jeans | building tonight | deliver, then quick review |
| castle-falls-jacket | Rev A reviewed (3 blockers); Rev B in progress with founder close-ups + reference.png. Founder: follow the reference composition (IP closed); collar; wrap armhole ok; sleeves full-wrap | re-review |
| grand-line-jacket | Rev E2 in progress. Founder flagged a bare zip-side column + islet shapes (→ A14/A15); solid rays + welt position approved | re-review with gate tables |
| forestball | Rev C in progress. Founder flagged hard-coded parallel rays → trace each ray | re-review |
| moon | Rev C in progress | re-review |
| comet-city-hoodie | Rev B in progress; hood option 1 → pattern unblocked | re-review |
| red-beast-hoodie | Rev B stitch rebuilt; hood option 1 | re-review |
| koi-blossom-hoodie | FISH not koi (inputs/reference_fish.png); A14 gates pass on M; rebuilding all sizes; pattern T1–T8 drafted | review |
| keep-clean-our-space-hoodie | Rev B. NEW: real text from inputs/reference.png: CN 不要世界汚染, KR 우리들 소중한 우주! (confirm 소중함), JP/EN unchanged | review |
| pixel-sky-fleece (new) | intake only (brief). Sparkles embroidered; bird knitted-in if the mill can, else embroidered | waiting: back design, factory answers, fit choice |

## Founder decisions made 19 Oct
- Hood block option 1. PR #2 closed. Engine welt override added.
- Castle: reference composition, collar, wrap armhole.
- Grand Line: solid rays, welt position.
- Wave: collar, seamless wrap.
- Koi: fish.

## Still open for the founder
See the coordinator's 28-question list (in the RECAP). Key ones:
- the new Wave fabric colour
- the Mandy answers: frames/sewing field, chenille, puff, jacquard sherpa + 3rd colour, embroidery on sherpa, thread card
- dye method (Grand Line/Forestball/Moon)
- names: Grand Line, Forestball
- Comet IP
- licence boxes
- fleece back design and fit

## Rules learned today
- The coordinator never runs `git commit -a` in the shared tree; use explicit paths or commit_project.sh.
- Project `.gitignore` `*.png` hides `inputs/closeups/` → `git add -f`. Fix candidate: `!inputs/**/*.png`.
- Reviewer prompts must require the A14/A15 gate tables, and must grep each project for hard-coded motif geometry.

## Housekeeping
- Untracked file literally named `*` at the repo root. Ask before deleting.
- Two autostash stashes are still there.

## PAUSED 2026-10-19 ~21:00 (founder: token cost)
Only Konpeito (patches rebuilt from inputs/svg) and Wave (Rev B: wrap, under-collar, smooth warp, new factory frames, chenille) keep running.
PAUSED (work committed; restart with a FRESH builder per product, short brief + the product's REVIEW_OPEN.md + LESSONS A14–A16):
- castle-falls: A16 rework not started. Handoff in inputs/brief.md.
- grand-line: Rev E3, scene good. Next: M gate build, then all sizes.
- forestball: Rev C, rays traced. Next: gates, then pack.
- moon: Rev C nearly done. Next: spec texts.
- comet-city: QA passed. Next: fronts rebuild + pattern/docs.
- red-beast: Rev B3. Next: scene build, gates, T pages.
- keep-clean: Rev B. Next: final build + page check.
- koi: Rev C started (refmask, floratrace).
Factory answered (factory.json): Brother, 750 mm field, frames 300×300 + 400×450, front single hooping, back 2, chenille/puff/sherpa yes.

## ENGINE WORK — state 2026-10-20 (coordinator d3fafdf9 handing off; start a fresh session)
Founder: hold all product work until the shared parts-based digitizing engine is done (docs/ENGINE_PLAN.md,
docs/DIGITIZING_PRINCIPLES.md = founder-approved house rules). Techniques are plugins, toggled per run; the end goal is a PLM
self-serve flow (memory: techpack-end-goal-plm).
- **M0** honest gates + bench: MERGED (PR #3, 73ae3dd). Baseline on the Castle crop: 0/8 gates.
- **M1** skeleton: PR #4 https://github.com/haki-studio/techpack-engine/pull/4 (head 853961b), reviewer APPROVED, MERGED 2026-10-20 (ed278f9). Crop: 89 % direction OK / 7 % chaos, 0 blob satins / fans / random angles, red + gold sewn,
  33 trims per 100 cm², 84k stitches, 3/8 gates. The live view reads as flat paint-by-numbers (stubs), as expected.
- **Fold into M2 first** (from the M1 review):
  - (1) derive random_angles in run.py (it is hard-coded 0 today)
  - (2) a split-satin cord gate read from the DST (width / row length), since satin_runs is blind to cords
  - (3) report direction split by independent tiles (rule angles) vs self-derived ones (field-mean stubs)
  - (4) gates read the written DST: check the labelled segments against readback
  - (5) protect the water blues (falls lost their blue)
  - (6) bench idempotent: replace the row for the same label + sha
  - (7) a LESSONS note on angle_coherence no-visible-stitches
  - LOW: soften the split_row docstring; stub field_angle raises; fence the column.py jitter
- **Next 3 steps:**
  1. After #4 merges, launch a fresh builder for **M2** (organic parts: direction field, guided/contour fill, blends, stratum + cloud splitters) + the follow-ups above. One builder at a time, in a worktree, PR, reviewer, founder merge.
  2. **M5** (SVG parity on Konpeito) can run in parallel after M1 is merged.
  3. Then M3 → M4 (crop passes every gate + the founder signs off the live view) → M6 (puff / chenille / chain) → M7 (Castle) → M8 (Wave).
- **Konpeito:** pack final (21 pp), only the front-leg art is open. The handoff prompt is out/HANDOFF_PROMPT_front-leg-07.md
  (skill /techpack-handoff).
- **Factory (Mandy):** answers are in factory.json. Still to ask her: which frame takes the 340×505 front; whether a sleeve (~500×510) fits one hooping; whether the 580×490 back needs 3–4 hoopings on 400×450; her thread brand + colour book; the sherpa design review.

- Wave paused WIP in projects/wave-jacket/gates.py was saved to projects/wave-jacket/WIP_gates_py_before_M1_merge.patch (it clashed with M1's change to that file); re-apply by hand when Wave resumes.
