# RECAP 2026-10-22 — standard labels rollout (builder-standard-labels, session 689b969f)

Lead: lead-eng-standard-labels. Mission charter: Obsidian `Claude/Missions/2026-10-22-standard-labels.md`. Base: PR #53 (`standard-labels`).

## What / why
Founder 22 Oct: one standard main label (6.5 × 2 cm white) for every product; care label picked by fibre. Konpeito was done in #53; this rolls the labels out to every other pack builder, and rebuilds KCOS + Pixel Sky.

## Built
- `engine/labelsheet.py` — one shared helper so no builder hand-draws labels: `main_bom()`, `care_bom(shell)`, `care_desc`, `panel(x, y, w, shell, main_where, care_where)` (main label 1:1 + care label front/back 1:1, or an amber MISSING box), `export(dir, shell)` (zip labels/, emptied first so a stale care label can't survive). `tests/test_labelsheet.py`: red on a "duck/cotton → 100-cotton" nearest-label mutation (4 fail), green on the real rule.
- 6 jacket `gtp.py` copies (castle, drum-island-plum-pine, forestball, grand-line, moon, wave): BOM main + care rows from labelsheet; T8 = standard panel at the right; main label "flat, sewn down on all 4 sides" (D7), placement unchanged; old draft care text replaced (the standard care label carries its own fibre/care text); `SHELL_MAT` = the BOM shell string (100 % cotton duck) so care label = 100-cotton; `gtp.build` exports out/labels, `finish*.py` copies it into the zip.
- Pixel Sky (branch `labels-pixel-sky` → push to `tp-pixel-sky-fleece` on top of Rev G 5f734e3): T6 main label art + care label MISSING, both PDFs; rfq_text_gate 0.
- KCOS (branch `labels-kcos` off `tp-keep-clean-our-space-hoodie` Rev I): Rev J = labels only; new page T6b; BOM rows; note 8; rev log; zip labels/.

## Decisions
- Pixel Sky Rev G was uncommitted in its owner's worktree → BLOCKED to the lead; lead got Rev G pushed (5f734e3), then I added the labels on top (no rebase, no force).
- Panel title has no "founder" (Pixel Sky's RFQ gate bans the word).
- Jackets: care label = 100 % cotton because their BOM states "100% cotton duck canvas" (not marked proposed) — BUT the BOM footnote says "fibres ... proposed". Flagged to the lead.
- Pixel Sky neck tape NT1 is 1.5 cm, the main label is 2 cm tall → printed as [proposed — confirm] "centre it on the tape".

## Open / gotchas
- Standard care label prints "DRY CLEAN" and "MADE IN CHINA" — the old jacket draft said "do not dry clean"; flagged.
- Comet City + Red Beast + zip-hoodie-block (Koi uses it) also write a "Labels" BOM row — see later updates.
