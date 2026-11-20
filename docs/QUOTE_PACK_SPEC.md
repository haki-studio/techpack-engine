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
| cover | ✓ | ✓ | style **quote ref** (see §2), category, size range, colourway as Pantone/TCX, ladder. No product name, no collection/drop name, no mockup render. |
| quote_sheet (new; Pixel Sky Q1 generalised) | ✓ | – | ladder (default 300/500/1,000; project may override), blanks for unit price per qty, currency, Incoterm, sample price + days, production days, MOQ per colour. **We never print a number in a price field** (skill `request-a-supplier-quote` rule 1). |
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

**Copy code**: 6 chars Crockford base32, random, unique across the register (`K7Q3MZ`).

| Mark | Where | Survives |
|---|---|---|
| Visible footer, every page: `Prepared for <factory legal name> · copy K7Q3MZ · confidential, for quotation only` + Chinese line `仅供 <中文名称> 报价使用，不得转发、展示或用于其他客户` | PDF text layer | print, screenshot, re-type |
| Quote ref on cover + filenames: `HK-FL-PIXSKY-K7Q3MZ` (not the internal style code alone) | text + filename | catalogue / Alibaba listing that reuses our ref |
| PDF metadata: Title/Subject/Keywords + XMP `dc:identifier` = copy code; `/Author` = "Haki Studios" (`strip_creator`) | file | forward of the original file |
| **Unique harmless variation** — one pick per copy, recorded: (a) which of 4 equivalent wordings of the QC/how-to-measure note is used, (b) the ordering of the optional questions on factory_questions, (c) a 1–3 digit offset in the placeholder-box label numbering (E1 vs E01 vs E-1). Never a measurement, colour, fabric, tolerance or anything that changes the garment. | text | re-typed / re-drawn copies that strip the footer |
| Award only: copy code on the **care label lot line** (`LOT K7Q3MZ`), proposed amber for the founder at first award | physical garment | overruns / factory resale of our product (the documented leak, brief §2c) |

Variations (a)–(c) give 4 × 24 × 3 = 288 combinations per style — with the code that's a unique fingerprint per
factory even if the footer is cut off.

**Register** (`projects/<style>/out/marks/register.jsonl` now; PLM table in fq-rfq-in-plm, Dec): one row per copy —
`style, rev, tier, copy_code, factory_id, factory_legal_name, variation{a,b,c}, files[{name, sha256}], built_at,
agreement_ref (award), sent_at (null until Scribe records the send)`.
**Trace**: `python3 -m engine.trace_mark <file | text | image-ocr-text>` → copy code / variation match → factory.

## 3. Gates (all must pass on the SHIPPED file, after any shrink — E15)

`build_quote_pack()` / `build_award_pack()` fail the build (exit ≠ 0, no zip written) on any of:

| # | Gate | quote | award | Red-then-green proof (the gate must catch its own canary first) |
|---|---|---|---|---|
| G1 | **File-type allowlist**: quote zip may contain only `*.pdf` + `README.txt`. Refused by extension *and* magic bytes: stitch `.dst .pes .exp .jef .vp3 .hus .emb .xxx`, chart `.bmp` + any raster outside the PDF, pattern `.dxf .plt .hpgl .rul .aama .mrk`, art `.svg .ai .eps .psd .png .jpg .tif .pdf-other-than-the-pack` | ✓ | – | build a canary zip with one file of each refused type renamed to `.txt` → every one refused |
| G2 | **Art fingerprint**: no art path data in any quote page. Fingerprint = rounded (0.5 mm) point runs of every `art/*.svg` path + sha256 of every art/stitch-preview raster; scan quote page SVGs + PDF content streams + embedded image hashes | ✓ | – | the same scan on the award flats must find ≥1 hit (else blind) |
| G3 | **Embedded rasters**: every image in a quote PDF must be on the build's allowlist (placeholder hatch, Haki wordmark, how-to-measure diagram) by sha256 | ✓ | – | an injected art PNG on a test page → refused |
| G4 | **Prices**: currency + number (`\$ ?\d`, `USD ?\d`, `US\$`, `RMB ?\d`, `CNY ?\d`, `¥ ?\d`, `€ ?\d`, `\d+(\.\d+)? ?(USD|RMB|CNY|元)`), `FOB ?\$?\d`, `EXW ?\$?\d`, `target price`, `unit cost`, `landed`, `margin`, `retail` | ✓ | ✓ | canary list (`$18.99`, `USD 9`, `¥120`, `RMB 120`, `FOB 9.00`, `target price 12`) must all hit; a blank quote-sheet field (`Unit price (USD): ______`) must NOT hit |
| G5 | **Other factories**: every name in the supplier register (legal + contact + Chinese name) except the recipient's; `factory.json` answer strings | ✓ | ✓ | the internal copy (which names Mandy's answers) must hit |
| G6 | **Mark present**: every page's text has the recipient's legal name + copy code; metadata carries the code; code exists in the register with matching file sha256 | ✓ | ✓ | an unmarked copy of the same pack → refused |
| G7 | **Agreement**: award build needs `--factory <id>` + an agreement record for that id (`inputs/agreements.json` now: `{factory_id, legal_name, signed_on, version, doc_ref}`; PLM supplier documents later, brief §6 row 8) | – | ✓ | award build for a factory with no record → refused |
| G8 | existing `leak_gate` BASE_PATTERNS + `rev_pattern` + `summary_gate` (now tier-aware: required kinds per tier from §1a) | ✓ | ✓ | unchanged (internal copy must hit) |

The gate result is written next to the zip (`out/marks/<copy_code>_gate.json`) and its sha256 goes in the register
row. No gate json = not sendable.

## 4. API (build phase target)

```python
from quote_pack import build_quote_pack, build_award_pack
build_quote_pack(pages, factory=REG["shengnan"], ladder=[300, 500, 1000], decorations=ELEMENTS)
build_award_pack(pages, factory=REG["shengnan"], refzip_tree="out/pkg")      # G7 first
```
- `engine/quote_pack.py` (new): tiers, placeholder_box, marks, register, gates G1–G7, calls `factory_copy` for G8.
- `engine/factory_copy.py`: tier-aware tags + `KINDS` gains `quote_sheet`, `decoration_spec`; `leak_gate` gains
  `price_patterns()` and `others_patterns(register, recipient)`.
- `engine/trace_mark.py` (new).
- Supplier names for G5 + the footer: extend the existing `factory.json` `"suppliers"` map (already read by
  `engine/supplier_gate.py`) with `legal_name`, `legal_name_zh`, `contacts[]` per key — no second supplier file, no prices.
  Seeded from PLM `manufacturers` / `supplier_profiles` (read-only export; no PLM write in this mission).
- First adopter: Pixel Sky (`finish.py` → quote zip + award zip), then Konpeito (`kjfactory.py` already does the award side).

## 5. Definition of done (charter)
`tests/test_quote_pack.py` builds a test quote pack from a fixture style for a fixture factory and asserts:
1. zip members ⊆ {pack PDF, README.txt}; no stitch / art / chart / pattern file by extension or magic bytes;
2. G2/G3: 0 art fingerprints, 0 non-allowlisted rasters — and the award copy of the same fixture has > 0 (blind check);
3. G4/G5: 0 prices, 0 other-factory names — canaries hit;
4. every page names the fixture factory + copy code; register row written with matching sha256;
5. award build without an agreement record exits non-zero.
Then reviewer (spawned session) APPROVE on the PR.

## 6. Decisions taken by the lead ($0, no founder item)
| Decision | ★ Pick | Rejected |
|---|---|---|
| Grading in quote pack | base size only | full chart: grade rules are pattern work and not needed to price |
| Stitch count precision | nearest 500 | exact: an exact count + box size helps redigitising nothing, but nearest 500 is enough to price and leaks less |
| Allowlist vs blocklist for quote zip | allowlist (pdf + txt) | blocklist: one new extension slips through |
| Mark | visible bilingual footer + code + 3-way variation + metadata | invisible-only: a visible line also deters; paid watermark service (brief: rejected) |
| Incumbents (Mandy, Emmie) | same rule for **new** styles; live styles they already hold are not re-sent | exempt incumbents: their copy is the documented leak route |
| Register home | jsonl in project `out/` now, PLM in Dec (fq-rfq-in-plm) | PLM now: needs a migration + anon probe, outside this mission's $0 design window |

## 7. Not in this mission
PLM request entity / landed-cost sheet (fq-rfq-in-plm), who to send to (fq-bench-plan), agreement template + trademark
(fq-protection-card), any factory contact (founder approves each). Scribe's authority file is unchanged: quote sends
stay ALWAYS UP.
