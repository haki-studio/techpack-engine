# RECAP 2026-10-22 — factory summary + leak gate (engine), Konpeito factory copy

Mission konpeito-soot-sprites (lead-eng-konpeito-soot-sprites), task TASK-builder-summary.md. Branch `konpeito-factory-summary`.

## Why
Nick + Steph: the 26-page Konpeito pack is too much for the manufacturer. Founder: the factory summary is "whatever the
factory needs to nail the product the first time", not a fixed page count. Pixel Sky Rev G had a supplier/internal split
for one project only (rfq_text_gate, LESSONS E14 on its branch).

## What
- `engine/factory_copy.py`: page `KINDS` a factory needs (ordered), `Page(id, kind, title, factory|internal, svg)`,
  `summary_gate`, `factory_pages`, `scrub_svg` + `BASE_SCRUB`, `leak_gate` (red-then-green built in: blind = fail),
  `BASE_PATTERNS`, `rev_pattern`. `tests/test_factory_copy.py` (8 tests).
- `projects/konpeito-jeans/kjfactory.py`: tags every kjpages page, builds factory pages (FACTORY flag), scrubs them,
  factory cover (contents = factory pages + ORDER block), renders the SUMMARY, the full pack as INTERNAL, reference zip
  (stitch files, previews, labels, factory README, factory element pages), leak gate on the PDFs + zip text.
- `kjpages.py`: 6-line hook only (`FACTORY` flag skips the D stitch-check / E fidelity panels on element pages).
- LESSONS E15 (E14 is Pixel Sky's, still on its branch), README "Factory copy" opt-in note.

## Decisions
- Summary = T1-T8, T7b, G1-G7, G6b, F1 (18 pages). C1-C7 compare sheets + Q1 decisions = INTERNAL. Compare sheets are
  internal BY KIND because their gate tables are images: the text gate cannot read them.
- "Full reference" for the factory = the reference zip (stitch files, 1:1 previews, thread charts, labels), not a second
  long PDF; everything internal sits in the INTERNAL pdf.
- Scrub happens on rendered SVG `<text>`; the leak gate on the rendered PDF text is the proof (not the scrub rules).
- Built on B7 art (soot B8 is the other builder's branch); re-run `python3 kjfactory.py` after it merges for the B8 file.

## Gotchas
- kjpages G7 / Q1 wording will change in B8: new internal words there will FAIL the leak gate (by design) → add a
  KJ_SCRUB rule, don't loosen a pattern.
- out/ is git-ignored; this worktree's out/ was copied from ~/te-standard-labels (B7 @ f2c55c0).

## Round 2 — review CHANGES on f7d46bb (fresh builder)
Review: https://github.com/haki-studio/techpack-engine/pull/57#issuecomment-6349297371. Each must-fix has a test that is
red on f7d46bb's `factory_copy.py` (5 new tests: 5 red on the old module, 13/13 green now).

| # | Finding | Fix |
|---|---|---|
| 1 | T8 Note "move CONFIRMED" / "kept as the mockup" | `scrub_text` tidies after every rewrite and checks drop rules on the raw AND the rewritten text |
| 2 | G3 orphan "(confirmed)" | tail of a wrapped "Generated, not traced" note: kjpages skips those notes when `FACTORY`; BASE_SCRUB drops a lone status word |
| 3 | G4 layer ids + before→after widths | kjpages `FACTORY` branch prints "name ちひろ 0.85 mm (40wt)" (WB_FAC names); BASE_PATTERNS flag `a_b 0.9 ->` and `N [mm] -> M` |
| 4 | gate ok on empty factory text | `leak_gate(..., min_chars=40, image_only=())`: any factory page/file under 40 chars = `empty` = not ok |
| 5 | gate ran pre-shrink | kjfactory shrinks SUMMARY + INTERNAL first, then gates the shipped files |
| should | G7 provenance, G2 cream, T2 client, T6 pixels, F1 size-24, G2 "art → needle" | KJ_SCRUB rewrites + EXTRA patterns (`per px`, `median of the`, `client`, `mockup pixels`, `reads cream`, `dropped`) |
| should | zip gate only read .txt/.svg | `FC.file_text` reads PDF/.ai text + info + XMP human fields + `%%` header; `FC.strip_creator` blanks `%%For:` / /Author / dc:creator in place (same byte length) |

Gotchas found on the way
- `sheet.esc` writes `>` as `›` and `<` as `‹` in SVG text: scrub rules must match `-[>›]`.
- The wider zip gate found a real leak the old one could not see: the 1:1 preview PDFs said "Drawn from the DST
  read-back" → now "Drawn from the DST stitch file" (kjpages, also in the internal pack).
- Whole-XMP scanning is noise (Adobe instance uuids hit the PLM-uuid pattern, base64 thumbnails hit `C[1-7]`): read only
  dc:/pdf:/photoshop: fields + CreatorTool.

Result (B7 art): summary 16 pages, 0 hits, min 1390 chars/page; internal 340 hits; zip 55 files (text + metadata), 0
hits, 0 empty; re-extracted zip checked separately; unstripped source .ai = red on `\bDevin\b`. Every page read at
110 dpi, nothing clipped. Still to do on the B8 re-run (after #58): re-check G7 wording (EXTRA patterns will flag new
provenance words).
