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
