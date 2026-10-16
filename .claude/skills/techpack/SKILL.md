---
description: Turn every mockup in inbox/ into a product and build all their tech packs in parallel (embroidery art, DST/PES, splits, pattern, tech pack PDF). Run after dropping images into inbox/.
argument-hint: "[optional: extra notes for this batch, e.g. 'all on the Drum Island block, 12 oz duck']"
disable-model-invocation: true
---

# /techpack — inbox to tech packs

Batch notes from Devin (may be empty): $ARGUMENTS

You are the coordinator. Read `LESSONS.md` first. Do not stop to ask questions until step 4 — Devin wants to drop
images and watch.

## 1. Intake (you)
1. `python3 scripts/intake.py sheet` — lists every image in `inbox/` and writes grid overlays `inbox/_grid_*.png`.
   Look at every overlay. Images may be single products, close-ups, or **boards with many products** (crop those).
   **A subfolder of `inbox/` is one product: use the folder name as the slug** (all images in it belong together),
   and read any `.md`/`.txt` notes in it as the client's brief for that product.
2. Group images into products: one product = one garment design (front, back and close-ups together). Skip a
   design that already has a project folder under `projects/` (say so). Give each a short slug
   (`wave-jacket`, `koi-lily-hooded-jacket`).
3. For each product decide, from the images and the batch notes:
   - **garment + fit block**: if it's the collared work jacket (corduroy collar, rib hem/cuffs) use `drum-island`;
     anything else → `unknown — needs a fit chart` (art + stitch files still go ahead on a proposed block; the
     pattern waits for the chart).
   - **process**: embroidery (thread texture, satin sheen, raised fills), **knit jacquard / printed fleece**
     (pixel-grid scenes on fleece or sherpa — not embroidery; build the artwork + colour count, flag the process),
     print, patch.
   - **elements**: every decorated area with its pattern piece.
   - **IP flags**: anything that looks like an existing character, logo or franchise creature (e.g. a known
     game/anime creature) → flag it; that element gets an original replacement, never a lookalike. Public-domain
     art (e.g. Hokusai's Great Wave) is fine to reference.
   - low-resolution source → note it (ask for originals in step 4 but don't wait for them).
4. Write `inbox/_plan.json` (format in `scripts/intake.py`) and run `python3 scripts/intake.py apply inbox/_plan.json`.
   Post ONE message: a table of products (slug, garment, block, process, elements, flags) + every question that
   blocks a product (usually: fit charts for non-Drum-Island garments, fabric). Then continue — don't wait.

## 2. Build (parallel)
For every product, launch one **`techpack-builder`** subagent in the background with the prompt
`Build the tech pack for projects/<slug>. Brief: projects/<slug>/inputs/brief.md.` — all at once (they share CPU
through `scripts/heavy.sh`, so it's safe to start them together).

Tell Devin how to watch: `python3 scripts/status.py --watch` in a second terminal, or open `status.html`
(Windows: `\\wsl$\Ubuntu\home\<you>\techpack-engine\status.html`) — it refreshes itself and shows each
product's latest preview.

## 3. As builders finish
- Relay each builder's result in one line (deliverable paths under `projects/<slug>/out/`, open questions).
- Engine changes: builders don't edit `engine/`; they write proposals to `projects/<slug>/ENGINE_NOTES.md`. When
  all builders are done, apply the proposals yourself (one at a time, tests passing), add LESSONS rows + tests,
  commit and push to `main`.
- Finish with a summary table: product, stage, stitches (back M), files, what's blocked and why.
