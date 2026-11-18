# RECAP 2026-11-03 — KCOS Rev N (labels page) + tee family standard labels

Builder `kcos-labels`, for lifetime-product-lead. Founder go via Chief 2026-11-03 (standing 22 Oct label rule, $0).

## Job 1: KCOS pullover Rev N = Rev M + labels page
- Branch `kcos-labels-revn` (worktree ~/tpe-kcos-labels). Build inputs (`out/pv/M`, art_M.pkl, fonts) copied from ~/te-kcos-revm, so
  the 9 DST/PES are **byte-identical** to the Rev M zip Mandy already has (md5 checked).
- New page **K7 LABELS = PDF page 7 of 12** (K1-K7, then Rev J reference E01-E04, R1). Model = Rev J T6b (`labelsheet.hoodie_page`),
  rebuilt in `pv_pack.k7()` because hoodie_page hard-codes zip-jacket lining text (flannel/taffeta/sherpa) that the pullover does not have.
  Placement rows live in `pv_bom.PLACEMENT`: main label inside back neck, CB, flat, 4 sides (standard, black); height 1.5 cm below the
  neck seam, size label under it, care label left side seam 10 cm above the hem rib = amber [proposed — confirm].
- Care label = 100 % cotton white (self fabric, factory BOM wording -> green). Rib 95/5 is NOT on the label: question 7 on K7 asks Mandy.
- Fabric weight: SELF now 425 GSM (Mandy 30-31 Oct, per product-lead brief; I could not read the WhatsApp thread myself, the auto-mode
  classifier blocked the production read). Hidden Inventory BOM line kept as `SELF_HI_BOM` (350). K1 and K7 print the change in amber.
- K1 subtitle + footer say Rev N / 3 Nov 2026; Labels row points to K7. Zip carries labels/ (main + 100-cotton care .pdf/.ai).
- Test: `tests/test_kcos_revm_labels.py` (425 vs 350, K7 rows, rib question) red on Rev M pv_bom, green on Rev N.
- NOT sent to Mandy (founder sends).
- Independent reviewer: **REVIEW: APPROVE c3721c2** (0 must-fix). Should-fix 1 applied after the review: K1's Labels row now names question 7
  (rib) on K7. Date 3 Nov is UTC-correct. Rev J reference pages keep their Rev J footers, carried over from Rev M as designed.
- Delivered: TECH PACKS/2 Keep Clean Our Space hoodie/ "... - Rev N (pullover) - for Mandy.pdf" (12 pp, labels = page 7) + "... stitch files size M.zip";
  Rev M moved to older versions. READ ME - meeting list item 2 rewritten for Rev N.

## Job 2: tee family standard labels
- Branch `family-tee-standard-labels` @ d042f94, PR #62. family.yaml labels: main 6.5x2 cm (assets/labels/main-label-6.5x2cm-white.pdf),
  care = 100 % cotton white (by blank.fabric), separate size label (proposed); the old hem and neck labels are removed. Main + size placement stay
  {proposed} (previous hem spot) + a TODO: **Nick decides back neck vs hem**. Size label moved to 10.5 cm so it does not cover the main label on T6.
- LESSONS D8 + test_tee_family_uses_the_standard_label_files (red on the old yaml). Full suite 722 pass / 2 known konpeito fails.

## Source confirmed (product lead, 3 Nov)
- 425 GSM = Mandy WhatsApp 2026-10-31 05:17Z: "the fabric is 425gsm of hidden inventory hoodie. not 365gsm". She said 365, not 350.
  The pack's "350" is our Hidden Inventory BOM figure (SELF_HI_BOM), so the note is accurate as worded. Founder send card filed by the product lead.

## HANDOFF (3 Nov, builder kcos-labels stopping; work accepted by product-lead-lifetime)
- Branch kcos-labels-revn @ this commit (worktree ~/tpe-kcos-labels), PR https://github.com/haki-studio/techpack-engine/pull/61, reviewed APPROVE c3721c2.
- Branch family-tee-standard-labels @ d042f94 (worktree ~/tpe-tee-labels), PR https://github.com/haki-studio/techpack-engine/pull/62.
- Both PRs wait on the release lead. Full suite: 722 pass / 2 known konpeito fails (test_soot_sprites_traced_and_gated,
  test_soot_art_gates_red_on_b7_green_on_b8: need konpeito build outputs that a fresh worktree lacks; baseline, not labels).
- Nothing in flight. Open: Nick decides tee main-label placement (back neck vs hem); founder sends Rev N to Mandy (card filed by product lead).
- Leftover: an untracked symlink named `*` in ~/tpe-kcos-labels (from env.sh), harmless; safety check blocked its removal.
