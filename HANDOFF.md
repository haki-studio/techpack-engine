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
