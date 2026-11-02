# techpack-engine

Haki Studios' tech pack generator: garment mockups + a fit chart in, factory pack out.

What it produces for a garment:
- **Embroidery**: stitchable region art (SVG with digitizing attributes), production-intent **DST + PES** stitch
  files (hidden travel, turning satin, underlay, pull compensation, density blends, merged colour stops, ≤ 12
  threads), graded art sizes, per-size files where art wraps across a seam, **360 × 360 hoop splits** with basting
  registration crosses, thread charts (Madeira Polyneon / Isacord, ΔE2000 matched).
- **Pattern**: every piece XS–3XL drafted from the POM chart — seam allowances, notches, grain, drill holes,
  fusing, lining, embroidery placement — as **AAMA-layer DXF** (per size + all sizes) and a **1:1 plot PDF**, with a
  measurement check against the chart and seam walks.
- **Tech pack PDF**: flats, construction details, size chart + grading, BOM (consumption from the pattern),
  seams/assembly, labels/packaging/QC, colourway, pattern pages, inside view, operations, revision log, open
  questions, then the embroidery section (placement, threads, stitch summary, production files, element specs).
- **Factory copy** (`engine/factory_copy.py`, LESSONS E15): from the same build, a lean **FACTORY SUMMARY** PDF
  (only what the factory needs to make it right the first time) + a factory-safe reference zip, and the full pack as
  the **INTERNAL** copy (compare sheets, QA tables, decisions). A project opts in by tagging every page it builds
  `Page(id, kind, title, factory|internal, svg)` with a kind from `factory_copy.KINDS` (compare / check / qa /
  decisions are internal-only), scrubbing factory pages with `scrub_svg(svg, BASE_SCRUB + its own rules)`, and failing
  the build unless `summary_gate(pages) == []` and `leak_gate(pdf_texts(factory), pdf_texts(internal), extra,
  current_rev)["ok"]` (0 hits in the factory copy, > 0 in the internal copy). Example: `projects/konpeito-jeans/kjfactory.py`.

Start with `CLAUDE.md` (how to run, conventions) and `LESSONS.md` (rules + checks). `docs/ROADMAP.md` covers the
path to batch runs. Projects: `projects/drum-island-plum-pine` (embroidered work jacket),
`projects/konpeito-jeans` (patches + direct embroidery, see `.claude/skills/embroidery-tech-pack`).

## Daily use
1. Drop mockup images (single products, close-ups or whole boards) into `inbox/`
   (Windows: `\\wsl$\Ubuntu\home\<you>\techpack-engine\inbox`).
2. In Claude Code: `/techpack` (optionally with notes: `/techpack all on 12 oz duck`).
3. Watch: open `status.html` (refreshes itself, shows each product's latest render) or run `python3 scripts/status.py --watch`;
   `/techpack-status` lists open questions.

## Setup
```bash
scripts/setup_wsl.sh            # WSL 2 / Ubuntu: system libs + venv + deps + tests (once)  (macOS: scripts/setup_mac.sh)
scripts/new_project.sh <slug>     # scaffold a new product on its own branch
source scripts/env.sh projects/drum-island-plum-pine
python3 pattern_out.py qa
```

## Windows (WSL 2)
- Install Claude Code inside the WSL terminal: `curl -fsSL https://claude.ai/install.sh | bash`, then `claude` (log in once).
- Clone into the Linux home (`cd ~ && git clone https://github.com/haki-studio/techpack-engine`), not `/mnt/c/...`.
- Open outputs from Windows (Hatch, Acrobat) at `\\wsl$\Ubuntu\home\<you>\techpack-engine\projects\<style>\out\`.
- Give WSL most of your cores for the stitch builds: `%UserProfile%\.wslconfig` → `[wsl2]` `processors=<n>` `memory=<n>GB`, then `wsl --shutdown`.
