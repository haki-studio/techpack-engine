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
