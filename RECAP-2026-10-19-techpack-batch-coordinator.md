# Recap 2026-10-19 — techpack batch, coordinator session d3fafdf9

Continued from HANDOFF.md (previous coordinator 98f15cbf). All earlier builder WIP was already committed on main.

## Launched (all background, shared main tree, commits via scripts/commit_project.sh, 4 heavy slots on 8 cores)
| Product | Agent job | Target |
|---|---|---|
| grand-line-jacket | builder | finish Rev E per REVIEW_OPEN.md |
| forestball | builder | finish Rev C per REVIEW_OPEN.md |
| moon | builder | finish Rev C per REVIEW_OPEN.md |
| comet-city-hoodie | builder | finish Rev B per REVIEW_OPEN.md |
| castle-falls-jacket | builder | finish + deliver Rev A |
| wave-jacket | builder | finish QA + documents, deliver |
| red-beast / koi-blossom / keep-clean hoodies | reviewer each | first review of embroidery Rev A |

Loop: builder reports → reviewer (private render dir) → findings into REVIEW_OPEN.md → builder → until "reviewed".

## Founder decisions still pending (unchanged from HANDOFF.md)
Hood block (engine/hoodie.py vs PR #2), per-design welt angle, Keep Clean CN/KR text, IP resemblance (Comet/Castle),
plain hooded backs/hoods, factory frames/puff/chenille/thread board.

## Log
- Keep Clean + Red Beast first reviews: not reviewed. Common finding on BOTH: project compare.py renders from art pickles,
  not DST readback (A12 check violated) — candidate engine fix: one shared DST-based compare helper + a test that fails
  if a compare sheet isn't built from a .dst. Findings → REVIEW_OPEN.md; Rev B builders launched.
- Koi first review: not reviewed (close-up unused, lily petals/centres wrong, compare from pkl). Rev B builder launched.
- ~09:00 all 9 builders stopped when the coordinator session closed (little progress; uncommitted edits left in castle, grand-line, wave, moon, keep-clean, comet). 12:46 founder back.
- Team progress page published (private): https://claude.ai/artifact/QzuNQUtk48maLYnWnWt6Aq — overview per garment + one card per
  embroidered piece (39), previews/numbers from the M (or grade B) DSTs via readback. Stages renamed "Pack built"/"Signed off"
  (founder asked whether "delivered" meant done — it doesn't; nothing is signed off yet).
- ~13:00 all 9 builders resumed from their transcripts. Stray untracked file literally named `*` at repo root — left alone, ask founder.
- ~14:00 FOUNDER: Wave jacket is now the main project — embroidery-only sampling package ASAP (size M strike-off + splits, specs, F1); pattern/garment pages on hold (jacket being revised). Wave builder told + allowed to bypass heavy.sh queue. Others keep running.
- Castle Falls Rev A delivered (38 pp, M jacket 1,986,289 st / 4,632 trims, 16 hoopings, 15 threads sewn; known gap: village/pagoda/gate tower have no close-up). First review launched.
- Castle Rev A review: not reviewed (3 blockers: castle/pagoda/gate structure). Rev B started at normal priority (Wave first).
- ~14:35 FOUNDER inputs: Castle Falls got 4 close-ups (front, back L/R, sleeves 4 views incl. sleeve BACKS) + inputs/reference.png (the anime still)
  as "true source" for detail → builder told to trace close-ups, use reference for structure, build sleeves full-wrap. IP (Wano) still open.
  Koi Blossom: fish are NOT koi → tetra-like fish per inputs/reference_fish.png; builder told to replace all koi.
- Gotcha: projects/castle-falls-jacket/.gitignore has `*.png` + `!inputs/*.png`, so inputs/closeups/*.png are silently ignored
  (needed `git add -f`). Other projects may have the same trap → engine/intake fix candidate (`!inputs/**/*.png`).
- ~14:40 FOUNDER DECISION: Castle Falls follows the reference composition (IP question closed by founder). Builder told to drop the 'original castle/opened tree' deviations.
- Pixel Sky fleece (new, first fleece): intake brief + mockup committed. Founder: sparkles embroidered; bird knitted-in (jacquard 3rd colour) if mill can, else embroidered. Awaiting back design, factory answers, fit choice.
- Slip: coordinator ran 'git commit -a' in the shared tree and swept 27 files of builder WIP into a fleece commit; caught at once, soft-reset before push (was ahead 1), recommitted only the brief. Rule: coordinator never uses commit -a here.
- Wave M sampling package delivered (13 pp, 804,280 st / 3,705 trims, 12 hoopings, 24.4 h; QA found + fixed 26 % bare stripes,
  satin wedge gaps, bare sleeve centre band; sleeve-grading bug fixed). FOUNDER: collar (not hood); wave must be SEAMLESS → true
  seam-true wrap redo requested. Garment revision = fabric colour + hardware colour + probably no cuff/hem rib; shoulders/armholes/
  sleeves unchanged. Reviewer launched on the M package in parallel.
- FOUNDER: hood block option 1 (engine/hoodie.py). PR #2 closed. Engine: per-design welt override (pattern.draft/hoodie.draft welt=,
  hoodie.Variant) + test, 56 tests pass, pushed. 4 hoodie builders told.
- Founder sent Mandy the frame/machine/chenille questions (not yet: puff, jacquard sherpa, thread card).
- Wave M review: not ready (no placement plot, no match marks, sleeve fold seam, foam/stripe structure). REVIEW_OPEN.md written; builder to do Rev B incl. wrap.
- FOUNDER caught Grand Line bare zip column + islet shape mismatch. Root cause: islets were detected (position/width) but drawn as stand-ins with height capped at 0.30 w; zip shadow traced as dark sea. Added LESSONS A14/A15 + qa.motif_match/qa.uncovered + tests/test_fidelity_gates.py (red-then-green), 58 tests pass, pushed; all 9 builders told; future reviewer prompts must require the tables.
- FOUNDER caught Forestball rays: one hard-coded direction (56°, parallel, typed starts) vs mockup's steeper fanning sheer rays that fade at the bank — A14 again. Builder told to trace each ray + motif_match. Next reviewer prompts: grep each project for hard-coded motif geometry (angles/sizes as literals) and check each against the mockup.
- ~17:00 FOUNDER: Konpeito black jeans full tech pack DUE TONIGHT, same silhouette as Hidden Inventory pants (cargo; factory has pattern), front-leg embroidery file missing → page kept with MISSING boxes. No HI measurements found locally (only photos/PSD/tags in HakiStop/Designs/JJK/Pants/Hidden Inventory Pants); analyst searching Shopify/PLM. Builder launched.
