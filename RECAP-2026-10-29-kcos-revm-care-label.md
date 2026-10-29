# RECAP 2026-10-29 — KCOS Rev M care label (finding ed8f0135)

## What / why
- Finding ed8f0135: the standard-labels engine still gave KCOS the Rev J zip-jacket shell ("12 oz cotton duck canvas",
  no fibre % -> care label MISSING). The Rev M pullover pack (`pv_pack.py`, the current KCOS pack) carried **no labels at all**.
- Product lead decision 2026-10-29 (card standard-labels-fibre-pct): KCOS = Rev M pullover, French Terry 350 GSM 100 % cotton,
  rib 95/5 -> care label = the 100 % cotton art.

## Change
- New `projects/keep-clean-our-space-hoodie/pv_bom.py`: the ONE source of the Rev M fabric lines (verbatim from the Hidden
  Inventory BOM). `CARE_SHELL = SELF`; the care label is picked from it by `engine/labels.py` (not hard-coded).
  `FIBRE_CONFIRMED = True` because the wording is the factory's own BOM, not our proposal.
- `pv_pack.py`: K1 fabric rows read `pv_bom`; one new "Labels" row on K1; zip now carries `labels/` (main label + 100 % cotton
  care label .pdf/.ai); README mentions it. Gap after the hoopings table 8 -> 6 mm so Q6 still clears the footer (rendered).
- `kcgtp.py` (Rev J zip-jacket pack) left untouched on purpose: it documents the Rev J garment, whose duck shell has no fibre %.
- Test `tests/test_kcos_revm_labels.py`: red on the Rev J duck shell (4/4 fail), red on fibre unconfirmed (1 fail),
  red on old HEAD (no Rev M label source), green on new.

## State / pending
- Rendered locally only (out/ is gitignored, inputs copied from ~/te-kcos-revm). Nothing sent to the factory; the Desktop
  "Rev M (pullover) - for Mandy.pdf" was NOT replaced.
- Label positions on the pullover (centre back neck, wearer's left side seam) are proposed — factory to confirm.
