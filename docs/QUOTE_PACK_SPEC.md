# Quote pack vs award pack — spec (mission fq-quote-pack, 2026-11-20)

Status: **SPEC** (design phase, due Tue 24 Nov). Build 2–18 Dec. Source brief:
`HakiCode/missions/factory-quote-network/BRIEF.md` §3 rows 2–4, §6 rows 1–3. Builds on LESSONS E14/E15
(`engine/factory_copy.py`: FACTORY summary vs INTERNAL copy, red-then-green `leak_gate`). Unrelated to
`engine/supplier_gate.py` (colour-count feasibility), whose `factory.json` supplier map this spec reuses.

## 0. Problem in one line
Every quote request today ships the full production files (Pixel Sky Rev G zip, `projects/pixel-sky-fleece/finish.py`:
DST/PES stitch files, art SVG, jacquard BMP/PNG per size, DXF pattern for every size). A factory only needs garment
spec + decoration *method and size* to price. Construction files are the only thing a factory can leak before launch.

## 1. Three tiers (one build, three outputs)

| Tier | Who gets it | When | Contents |
|---|---|---|---|
| `quote` | 3–5 bench factories per style, each its own marked copy | founder approved the factory **and** the style's send list | placeholder-art quote pack PDF + README.txt. Nothing else. |
| `award` | the one awarded factory (or 2–3 finalists for a paid sample) | founder awarded + **agreement record exists for that factory** | today's FACTORY summary + reference zip (stitch, art, chart, pattern, labels), marked per factory |
| `internal` | us | always | the full pack, unchanged |

`factory_copy.FACTORY` becomes two audiences: a page is tagged with the **lowest tier allowed to see it**
(`quote` ⊂ `award` ⊂ `internal`). Existing projects tagged `factory` read as `award` (no behaviour change until a
project opts into `quote`).

### 1a. Page kinds per tier (extends `factory_copy.KINDS`)

| Kind | quote | award | Quote-tier rule |
|---|---|---|---|
| cover | ✓ | ✓ | opaque **quote ref** (see §2), category, size range, colourway as Pantone/TCX, ladder, **ship-to** (country + port/warehouse; default Ohio warehouse) and the **Incoterm place** we want quoted (default FOB <port of loading>, plus DDP <ship-to> as a second column), required **ex-factory window** and **sample deadline**. No product name, no collection/drop name, no character/series name, no internal style code, no mockup render (all enforced by G9). |
| quote_sheet (new; Pixel Sky Q1 generalised) | ✓ | – | ladder (default 300/500/1,000; project may override) with **qty per colourway + size ratio** (from the project, or "to be agreed"); blanks for unit price per qty, currency, Incoterm, **surcharge for sizes above base (yes/no + per size)**, sample price + days, production days, MOQ per colour, **testing cost**, **fabric/yarn consumption per piece** (asked, for jacquard / knit-to-shape: they cost the yarn, we never send the cell map), **quote validity (days)**. Stated terms (no numbers of ours): **sample request** (count, size, colourway, fit vs pre-production), **payment terms we accept** = deposit to start, balance on completion + shipping (memory po-payment-terms-standard), **packing method** (polybag, fold, hangtag, carton count + carton marks), **compliance / testing** (fibre-content labelling; CPSIA / AZO or "none required", per project). **We never print a number in a price field** (skill `request-a-supplier-quote` rule 1). |
| flats | ✓ placeholder | ✓ full | front/back garment outline with callouts; every decoration area replaced by a dashed box (§1b). No mockup, no render, no art path. |
| measurements | ✓ base size only | ✓ all sizes | base size (M) POMs + tolerance + how to measure; size range named. Grade rules = pattern work → award. |
| pattern | – | ✓ | award only (DXF, 1:1 plot, cut list). Quote pack states piece count + "pattern supplied at award". |
| bom | ✓ | ✓ | fabric composition/GSM/construction, trims, hardware, thread *count* not thread chart. **No supplier names, no prices, no other factory's material sources.** |
| construction | ✓ | ✓ | seam types, stitch types, wash. Assembly order may be summarised. |
| labels_packing | ✓ dims only | ✓ | label type + size + method ("woven main label 65×20 mm, 2 colours"); no label artwork file. |
| decoration_spec (new) | ✓ | ✓ | per element: id, method (embroidery / chenille / puff / jacquard / print), box size mm, placement on garment, **stitch count (rounded to nearest 500)**, colour count, frames/hoopings. Jacquard: panel, colours, cell size, rough % coverage — never the cell map. |
| artwork_placement / artwork_summary / artwork_element | – | ✓ | award only (they show the art). |
| factory_questions | ✓ | ✓ | questions **to this factory**. Never another factory's answers (E14): `factory.json` and any `factory_answers_*` text is internal for a quote pack to anyone but the factory it came from. |
| compare / check / qa / decisions / internal | – | – | internal only (unchanged) |

### 1b. Placeholder decoration box
Drawn by a new `engine/quote_pack.placeholder_box(el)` from data the project already has (placement bbox from the
G1 / decoration placement step, stitch count from the DST read-back, colours from the thread list):

```
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
  E1 · EMBROIDERY · 120 × 80 mm
  ~14,000 stitches · 6 colours
  left chest, 70 mm below HPS
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```
Grey hatch, no art. This is the only image of a decoration a quote copy contains.

## 2. Per-factory mark + one harmless unique variation

Every quote **and** award copy is built once per factory (never one copy forwarded to several).
The award marking claim is per file: PDFs + stitch/SVG/DXF headers where the format has a field (§2 table); a format with no
field is listed unmarked in the award README.

**Copy code**: 6 chars Crockford base32, random, unique across the register (`K7Q3MZ`).

| Mark | Where | Survives |
|---|---|---|
| Visible footer, every page: `Prepared for <factory legal name> · copy K7Q3MZ · confidential, for quotation only` + Chinese line `仅供 <中文名称> 报价使用，不得转发、展示或用于其他客户` | PDF text layer | print, screenshot, re-type |
| Quote ref on cover + filenames: opaque `HK-Q-K7Q3MZ` (never a product, collection, series or internal style code; the internal style ↔ ref map lives only in the register) | text + filename | catalogue / Alibaba listing that reuses our ref |
| PDF metadata: Title/Subject/Keywords + XMP `dc:identifier` = copy code; `/Author` = "Haki Studios" (`strip_creator`) | file | forward of the original file |
| **Unique harmless variation** — one pick per copy, recorded: (a) which of 4 wordings of the QC/how-to-measure note is used (the 4 wordings are written once per family and **checked equivalent by a person**, recorded in the family file; a changed tolerance or method is a garment change, not a variation), (b) the ordering of the optional questions on factory_questions (needs ≥ 4 optional questions; a style with fewer uses fewer orderings and the count below shrinks), (c) a 1–3 digit offset in the placeholder-box label numbering (E1 vs E01 vs E-1). Never a measurement, colour, fabric, tolerance or anything that changes the garment. | text | re-typed / re-drawn copies that strip the footer |
| Award only: copy code in each reference-zip production file — DST header `LA:` label, PES/EXP description where the format has one, SVG `<metadata>`, DXF `999` comment, PDF metadata — read back after writing; plus the **care label lot line** (`LOT K7Q3MZ`), proposed amber for the founder at first award. Stitch formats without a header field (JEF/HUS/XXX) are **not marked**: say so in the award README; the register sha256 still identifies the file. | file headers + physical garment | overruns / factory resale of our product (the documented leak, brief §2c); a forwarded stitch file |

Variations (a)–(c) give 4 × 24 × 3 = 288 combinations per style when (b) has ≥ 4 optional questions. The build
refuses a triple already in the register for that style (uniqueness enforced, not assumed) — with the code that's a
unique fingerprint per factory even if the footer is cut off.

**Register** (`projects/<style>/out/marks/register.jsonl` now; PLM table in fq-rfq-in-plm, Dec): one row per copy —
`style, rev, tier, copy_code, factory_id, factory_legal_name, variation{a,b,c}, files[{name, sha256}], built_at,
agreement_ref (award), gate_sha256, sent_at (null until Scribe records the send)`. Order: build → shrink →
`strip_creator` → marks/metadata final → **then** sha256 + gates on those exact bytes → register row. Nothing rewrites the file after.
**Trace**: `python3 -m engine.trace_mark <file | text | image-ocr-text>` → copy code / variation match → factory. Works
with no footer (variation triple + quote ref alone) and on re-typed text (whitespace/case-insensitive).

## 3. Gates (all must pass on the SHIPPED file, after any shrink — E15)

`build_quote_pack()` / `build_award_pack()` fail the build (exit ≠ 0, no zip written) on any of:

| # | Gate | quote | award | Red-then-green proof (the gate must catch its own canary first) |
|---|---|---|---|---|
| G1 | **Zip allowlist + content check**: quote zip members are exactly `<ref>.pdf` + `README.txt`. Names are not trusted: `.pdf` must start `%PDF`, parse, and pass G3/G10; `README.txt` must be UTF-8, ≤ 8 KB, no NUL bytes, no zip/PDF/image/DXF/SVG signature (`PK`, `%PDF`, PNG/JPEG/BMP/GIF/TIFF magic, `0\nSECTION`, `<svg`, `<?xml`, `IN;`/`PU`/`PD` HPGL), and its text runs through G4/G5/G8/G9. Formats with no reliable magic (DST/EXP/JEF/HUS/XXX) are caught because only these two members can exist and each must be what its name says. | ✓ | – | canaries all named `README.txt` (a DST, a PES, a DXF, an SVG, a BMP, a zip) and one `<ref>.pdf` that is really a DXF/SVG/zip → every one refused; plus a third member with any name → refused; green: the clean fixture zip passes |
| G2 | **Vector art fingerprint**: no art geometry in any quote page. Each `art/*.svg` path is flattened to a polyline, normalised (translate to centroid, scale to unit bbox, rotate to principal axis) and reduced to a shape signature; quote page SVGs and PDF content-stream paths (CTM applied, then the same normalisation) are compared at signature level. Raster hashes move to G3. | ✓ | – | red: the art SVG injected into a quote page at 0.33× and rotated 90° → refused; blind check: award flats of the same fixture → ≥ 1 hit; green: clean fixture with placeholder boxes → 0 hits |
| G3 | **Embedded rasters**: every image in a quote PDF must be on the build's allowlist (placeholder hatch, Haki wordmark, how-to-measure diagram), matched on the **decoded pixels** (perceptual hash, distance ≤ threshold), not the file bytes, so `shrink.py` recompression cannot false-red | ✓ | – | red: an injected art PNG → refused; green: the clean fixture **after** shrink passes |
| G4 | **Prices**: symbol/code before or after a number, either decimal mark (`\$ ?\d`, `US\$`, `(USD|EUR|RMB|CNY|HKD) ?\d`, `[¥€£] ?\d`, `\d+([.,]\d+)? ?(USD|EUR|RMB|CNY|元|€|¥|dollars?|euros?)`), per-unit forms (`\d+([.,]\d+)? ?/ ?(pc|pcs|piece|unit)`, `per (piece|pc|unit) \d`), `FOB ?\$?\d`, `EXW ?\$?\d`, and words `target price`, `unit cost`, `landed cost`, `our margin`, `retail price`, `RRP`, `MSRP`. Scans page text, README.txt and PDF metadata/XMP (`file_text`). | ✓ | ✓ | red canaries: `$18.99`, `USD 9`, `¥120`, `RMB 120`, `120 RMB`, `9.50 dollars`, `9,50 €`, `EUR 9`, `8.5/pc`, `per piece 8`, `FOB 9.00`, `target price 12`, `retail price 79` — all hit; green: a realistic clean page (ladder 300/500/1,000, `Unit price (USD): ______`, `retail-ready polybag`, `seam margin 1 cm`, `300 pcs`) → 0 hits |
| G5 | **Other factories**: for every supplier in `factory.json` `suppliers` except the recipient: legal name EN + 中文, registry key (`shengnan`), contact names + nicknames, plus every `factory.json` answer string | ✓ | ✓ | red: a quote pack for factory A containing factory B's legal name, Chinese name, a contact first name, the key, and one answer string → each refused separately; green: the recipient's own names (mandatory footer) → 0 hits |
| G6 | **Mark present + unique**: every page's text has the recipient's legal name + copy code; PDF metadata carries the code; code is in the register for **this** factory_id with matching sha256; variation triple unique for the style | ✓ | ✓ | red: unmarked copy; mark naming the wrong factory; code not in the register; one page missing the footer; metadata code missing; sha mismatch (one byte changed after registering); a duplicate variation triple → each refused; green: the clean fixture |
| G7 | **Agreement**: award build needs `--factory <id>` + an agreement record for that id (`inputs/agreements.json` now: `{factory_id, legal_name, signed_on, version, doc_ref, recorded_by}`; PLM supplier documents later, brief §6 row 8). Records are written by Scribe/COO from the signed document, never by the builder session (`recorded_by` must be one of them; the PLM move makes this a real permission). | – | ✓ | red: no record; record for another factory_id; empty or future `signed_on`; `legal_name` ≠ register; empty `doc_ref`; `recorded_by` = builder → each refused; green: a complete fixture record |
| G8 | `leak_gate` BASE_PATTERNS + `rev_pattern` + `summary_gate`, now **tier-aware** (required + allowed kinds per tier from §1a) | ✓ | ✓ | red: internal copy hits (existing); quote pack with a `pattern` or any `artwork_*` page → fails; quote pack missing `quote_sheet` or `decoration_spec` → fails; green: legacy `factory`-tagged project still builds as `award` unchanged (existing tests stay green) |
| G9 (new) | **Product-name denylist**: per project `inputs/quote_denylist.txt` (product name, collection/drop name, character/series names, internal style code + aliases), seeded by the build from the project's own names, scanned in page text, README.txt, every member filename and PDF metadata/XMP | ✓ | – | red: canary pack with the product name once in a page, once in a filename, once in `/Title` → three hits; green: clean fixture → 0; blind check: the internal copy → > 0 |
| G10 (new) | **PDF structure**: exactly one revision (one `%%EOF`, no incremental update), no `/EmbeddedFile`, no `/FileAttachment` annots, no `/JavaScript` or `/JS`, no `/OCProperties` (hidden layers), no `/AA` / `/OpenAction` actions; the build writes a fresh file (never pads in place after the gates) | ✓ | ✓ | red: one canary per feature (incremental save holding the art, embedded file, attachment annot, JS, OCG layer, OpenAction) → each refused; green: clean fixture |

The gate result is written next to the zip (`out/marks/<copy_code>_gate.json`) and its sha256 goes in the register
row. **What this mission enforces:** a failing gate means the build exits non-zero and writes no zip. **Send side** (Scribe
refuses to send a file whose sha256 has no passing gate json in the register) is **not** enforced here: it is scoped to
fq-rfq-in-plm (lead-eng, Dec), see §7.

## 4. API (build phase target)

```python
from quote_pack import build_quote_pack, build_award_pack
build_quote_pack(pages, factory=REG["shengnan"], ladder=[300, 500, 1000], decorations=ELEMENTS)
build_award_pack(pages, factory=REG["shengnan"], refzip_tree="out/pkg")      # G7 first
```
- `engine/quote_pack.py` (new): tiers, placeholder_box, marks, register, gates G1–G7 + G9–G10, calls `factory_copy` for G8.
- `engine/factory_copy.py`: tier-aware tags + `KINDS` gains `quote_sheet`, `decoration_spec`; `leak_gate` gains
  `price_patterns()` and `others_patterns(register, recipient)`.
- `engine/trace_mark.py` (new).
- Supplier names for G5 + the footer: extend the existing `factory.json` `"suppliers"` map (already read by
  `engine/supplier_gate.py`) with `legal_name`, `legal_name_zh`, `contacts[]` per key — no second supplier file, no prices.
  Seeded from PLM `manufacturers` / `supplier_profiles` (read-only export; no PLM write in this mission).
- First adopter: Pixel Sky (`finish.py` → quote zip + award zip), then Konpeito (`kjfactory.py` already does the award side).

## 5. Definition of done (charter)
`tests/test_quote_pack.py` builds a test quote pack from a fixture style (≥ 4 optional questions) for a fixture factory
and asserts:
1. every gate G1–G10 goes **red on each canary listed in §3 and green on the clean fixture** (one parametrised test per
   gate; a gate with no red test or no green test fails the suite);
2. zip members = {`<ref>.pdf`, `README.txt`}; the ref and every filename are opaque (G9 clean);
3. G2/G3 blind checks: the award copy of the same fixture has > 0 art hits;
4. every page names the fixture factory + copy code; register row written with sha256 of the final bytes;
5. variation uniqueness: building a second copy with a forced duplicate triple fails;
6. `trace_mark` round-trip: (a) the shipped PDF → its copy code → the fixture factory; (b) the page text with the
   footer stripped and re-typed (whitespace/case changed) → same factory by quote ref + variation triple; (c) a text
   from another copy of the same style → the *other* factory, never the first;
7. award build without a valid agreement record exits non-zero (all G7 reds); award stitch/SVG/DXF headers read back
   the copy code.
Then reviewer (spawned session) APPROVE on the PR.

## 6. Decisions taken by the lead ($0, no founder item)
| Decision | ★ Pick | Rejected |
|---|---|---|
| Grading in quote pack | base size only | full chart: grade rules are pattern work and not needed to price |
| Stitch count precision | nearest 500 | exact: nearest 500 is enough to price, and gives anyone re-digitising the design less to check their copy against |
| Allowlist vs blocklist for quote zip | allowlist (pdf + txt) | blocklist: one new extension slips through |
| Mark | visible bilingual footer + code + 3-way variation + metadata | invisible-only: a visible line also deters; paid watermark service (brief: rejected) |
| Incumbents (Mandy, Emmie) | same rule for **new** styles; live styles they already hold are not re-sent | exempt incumbents: their copy is the documented leak route |
| Quote ref | opaque `HK-Q-<code>` | readable ref (`HK-FL-PIXSKY`): names the product to a factory before launch (review r1) |
| Register home | jsonl in project `out/` now, PLM in Dec (fq-rfq-in-plm) | PLM now: needs a migration + anon probe, outside this mission's $0 design window |

## 7. Not in this mission
PLM request entity / landed-cost sheet (fq-rfq-in-plm), who to send to (fq-bench-plan), agreement template + trademark
(fq-protection-card), any factory contact (founder approves each). Scribe's authority file is unchanged: quote sends
stay ALWAYS UP.
**Send-side check** (Scribe refuses a file whose sha256 has no passing gate json): owner fq-rfq-in-plm (lead-eng, Dec);
until it ships, the build refusing to write the zip is the only enforcement, and the charter says so.
