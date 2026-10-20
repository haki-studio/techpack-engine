---
name: techpack-handoff
description: Write a self-contained, model-agnostic handoff prompt so ANY new session (any AI model or a human digitiser) can finish or change a delivered tech pack. It gets the pack PDF plus the new design file; the prompt explains the pack, the current design, exactly what to change, how, and the house branding. Use when the founder says "/techpack-handoff <slug> <what is missing or changing>".
---

# /techpack-handoff <project-slug> "<the change>"

You write ONE file, `projects/<slug>/out/HANDOFF_PROMPT_<change-slug>.md`, and show its path. The founder pastes it into
a new session, together with the tech pack PDF and the new design file(s). That session may be ANY model with or without
tools, or a human digitiser. So the prompt:

- assumes **no repo, no engine, no Claude tools, and no memory of this conversation**. Everything it needs is either in
  the prompt or in the files the founder attaches. Say exactly which attachments it will receive.
- is **specific about outputs and checks**, and neutral about method ("produce a DST + PES …", never "run build.py").
- is written in plain imperative English, with every number taken from the pack's files (read the PDF / readback json /
  STATUS.json; never estimate).

## Gather first (read, don't guess)
1. **The pack:** `projects/<slug>/out/*TECHPACK*.pdf`. Run `pdftotext -layout` on every page and record page codes, titles,
   which pages carry MISSING / PROPOSED / FACTORY TO SUPPLY, and the cover contents list.
2. **The page(s) to change:** their full current text, plus every page that cross-references the element (cover contents
   flags, flats, placement overview, embroidery summary + per-garment totals, compare pages, factory requests).
3. **Branding** from `engine/sheet.py` and the project's page builders:
   - page size, font, colour tokens, header layout (title / subtitle / rule / page code)
   - footer string
   - legend conventions (amber `[proposed — confirm]`, `[MISSING — …]`, blue FACTORY TO SUPPLY)
   - table style, file naming
4. **Embroidery house spec:**
   - the thread chart (name, hex, weight, catalogue codes) from the summary page
   - stitch limits (≤ factory needles per file from `factory.json`, max stitch < 7.5 mm, minimum satin/feature sizes)
   - densities and underlay rules from `docs/DIGITIZING_PRINCIPLES.md` and LESSONS A3/A11–A16
   - keep-outs from the placement page
   - motif conventions already used on the garment (e.g. "10 mm konpeito star")
5. **Founder decisions** (brief.md "Founder decisions", STATUS.json), and any constraint that must carry over: licensed
   look-alikes declined (A7), no invented numbers, and so on.
6. **Factory profile** (`factory.json`): machine, frames, needles, speed, which techniques they can do.

## The prompt's sections (in this order)
1. **Role + goal** (2–3 lines): "You are completing a factory tech pack for <style>. Deliver <X> so the pack can go to
   the factory."
2. **What you are given:** each attachment, by file name, with what it is.
3. **The product in one paragraph:** style, code, revision, garment, sizes, fabric and colour, factory.
4. **How the pack is organised:** the page list (code, title, purpose) and the legend conventions.
5. **The current state of the element:** a verbatim summary of the page to change (placement area, PROPOSED content,
   coordinates, current files) and why it is incomplete.
6. **The change:** what the new design is, and the exact rules for turning it into embroidery. Spell out:
   - motif sizes
   - colours mapped to the thread chart (never new threads unless unavoidable; if one is needed, add it to the thread
     chart and keep ≤ N per file)
   - stitch types and directions per part (from DIGITIZING_PRINCIPLES)
   - underlay, density, pull compensation
   - keep-outs and placement reference points
   - grading rule
   - hooping (factory frames)
   - what to do if the design is ambiguous (ask, or mark PROPOSED)
7. **Pages to edit and pages to add:** list each affected page and the exact edit, including totals, flags and the
   contents. "Every other page stays byte-identical."
8. **Branding spec:** enough to reproduce a page that is indistinguishable from the originals:
   - A4 landscape 297 × 210 mm
   - fonts and sizes
   - colour hex values
   - header and footer text
   - margins and table style
   - legend colours
   - number format
   - the language of notes
   Tell them to copy the layout of a named existing page (e.g. "G6 for a stitch-file page, G1 for the summary").
9. **Deliverables:**
   - stitch files (DST + PES), named per the convention
   - thread chart txt
   - preview PNG
   - updated pages as PDF (and the merged pack)
   - a short change log
10. **Acceptance checks** (each must be stated as passed, with numbers read from the written files):
    - colours ≤ limit
    - max stitch
    - min feature sizes
    - keep-outs
    - satin aspect and width limits
    - no random or automatic angles (stitch direction per part, as specified)
    - stitch / trim / time counts read back from the DST and copied into the pages
    - totals recomputed
    - the visual check: the stitch preview beside the design at the same scale
11. **Questions to ask before starting:** the open items the founder might still need to decide. Default for each.
12. **Do not:**
    - change anything outside the listed pages
    - invent measurements
    - draw licensed characters
    - remove PROPOSED tags without a founder decision
    - change the branding

## After writing
Render nothing. Check the prompt yourself against the pack: every number in it must appear in the pack or its files.
Give the founder:
- the file path
- a two-line description
- the attachments list to send with it
