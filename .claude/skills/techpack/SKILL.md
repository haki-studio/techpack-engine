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
     the boxy zip hoodie (hood, zip, self-fabric elastic hem/cuffs — e.g. the koi hoodie) → `zip-hoodie`
     (`engine/hoodie.py`, pattern ready; reference build `projects/zip-hoodie-block/`; its blank fit sample is pending — say so);
     anything else → `unknown — needs a fit chart` (art + stitch files still go ahead on a proposed block; the
     pattern waits for the chart).
   - **process**: embroidery (thread texture, satin sheen, raised fills), **knit jacquard / printed fleece**
     (pixel-grid scenes on fleece or sherpa — not embroidery; build the artwork + colour count, flag the process),
     print, patch.
   - **elements**: every decorated area with its pattern piece.
   - **IP flags**: anything that looks like an existing character, logo or franchise creature (e.g. a known
     game/anime creature) → flag it; that element gets an original replacement, never a lookalike. Public-domain
     art (e.g. Hokusai's Great Wave) is fine to reference.
   - **detail views inside a mockup image** (a close-up panel beside the jacket): crop each one with `"as": "closeup_<what>.png"` —
     intake puts it in `inputs/closeups/`, where builders trace from it (LESSONS A12). Say in the brief that it exists.
   - low-resolution source (the usual case: AI renders ~1–1.5k px for the whole garment) → there are no originals.
     Write `projects/<slug>/inputs/closeup_request.md` (one prompt per decorated panel, template in
     `techpack-pipeline` §0b) and, in step 4, ask Devin to run those prompts in the same image tool and drop the results
     into `inbox/<slug>/closeups/` (`closeup_<element>.png`). Builders start without them and trace from them when they land.
4. Write `inbox/_plan.json` (format in `scripts/intake.py`) and run `python3 scripts/intake.py apply inbox/_plan.json`.
   Post ONE message: a table of products (slug, garment, block, process, elements, flags) + every question that
   blocks a product (usually: fit charts for non-Drum-Island garments, fabric). Then continue — don't wait.

## 2. Build (parallel, detached — LESSONS E10)
For every product run `scripts/dispatch.sh build <slug>` (one line each). Each builder is its OWN background Claude
session (`claude --bg`) in its own worktree `.claude/worktrees/tp-<slug>` on branch `tp-<slug>` — never an in-process
`Agent` subagent, because those die with this session and force it to stay open. dispatch.sh runs at most
TECHPACK_MAX_WORKERS (default 2) at once and respects the company session/RAM cap; the rest are queued and start
by themselves as workers finish. Heavy commands still share CPU through `scripts/heavy.sh`.

**Then end this session.** Nothing waits on it: each builder pushes, opens its PR and launches its own reviewer
(`dispatch.sh review`); the reviewer approves, sends a fix round back (`dispatch.sh fix`) while each round clearly improves, or marks the product
blocked for the founder. Closing a coordinator is always safe; never keep one open to babysit workers.

Tell Devin how to watch: `claude agents` (attach / logs / stop any worker), `python3 scripts/status.py --watch`, or
`status.html` — the board (`~/.techpack/board/`) shows every product's stage and which worker has it.

## 3. Next session: collect results (`/techpack-status`)
A later, fresh session reads the board + `gh pr list` and does only what needs a person or a merge:
- Relay each product in one line (stage, PR link, open questions). `reviewed` PRs go to Devin to merge.
- Engine changes: builders don't edit `engine/`; they write proposals to `projects/<slug>/ENGINE_NOTES.md`. Apply them
  in a separate engine PR (tests passing), with LESSONS rows + tests.
- **Independent review (every product, no exceptions)** is launched by the builder itself (`dispatch.sh review`).
  Reviewer: **fidelity first** — stitch preview vs mockup side by side, zoomed, every mockup detail that is missing or
  simplified (cost findings are informational, never a reason to simplify); then every page rendered and looked at,
  every number vs the generated files, factory clarity, LESSONS gates, cost (trims / stitches). `scripts/review_next.py` decides the
  next step: fix rounds continue while each review finds fewer fixable items than the last (max 3, a cost safety net);
  no improvement, or only founder decisions left → `blocked` for the founder. Only a `reviewed` pack goes to the factory.
- A worker that died mid-way (laptop restart: background sessions do not survive a daemon restart) leaves its work on
  its branch/worktree; re-run `scripts/dispatch.sh build <slug> "resume from the branch"`.
- **Factory loop:** every pack carries the F1 page (`engine/factory.py`): strike-off files (size M), frame + needle
  question, thread card / lab dip for weak matches, quote basis. Frames, needles, speed and thread brands come from
  `factory.json` — when the factory answers, update it and rebuild the splits. Strike-off photos/notes go into
  `projects/<slug>/inputs/strikeoff/`; feed them back per `techpack-pipeline` §6 and add LESSONS rows.
- Sync: every worker has its own worktree + branch + PR, so there is no shared-tree sync step any more; `main` changes
  only by merged PRs.
- Finish with a summary table: product, stage (delivered / reviewed), stitches + trims (M), machine hours, files,
  what's blocked and why, and what the factory has been asked (F1).
