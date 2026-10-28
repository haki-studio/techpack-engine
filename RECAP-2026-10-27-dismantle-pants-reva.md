# RECAP 2026-10-27 — Dismantle Pants Rev A (INTERNAL tech pack)

## What was built
- `projects/dismantle-pants/`: 10-page INTERNAL sampling-draft pack modelled on Konpeito (HI block): T1, T2 flats + mockup
  placeholders, P1 print spec (new page kind), T3 HI chart, T4 pattern + check-matching rules, T5 BOM (fabric open, two
  options), T6 construction + finish, T7 placement, T7b label art, Q1 open questions.
- Delivered: `Desktop/TECH PACKS/Dismantle Pants/Dismantle Pants - Rev A - INTERNAL.pdf` + `.zip` (labels/: standard main
  label + HAKI_DM size labels 26–40). `plm.json` links the PLM product for the tech-pack sync.

## Decisions + why
- Print repeat estimated from photos (dmprint.py, FFT pitch 14.4 px, ~45 squares across the half hip); garment scale
  unknown (elastic ref waist) → 3 assumed half-hip anchors → 12.2–13.8 mm; proposed 12.7 mm = 1/2 in mill repeat. The
  ChatGPT prompt's "1.5–2 cm" disagrees with the photos → Q5.
- Back label = standard main label OUTSIDE at CB (founder said "back label on the waist band"); HI CB belt loop replaced by
  two loops 15 mm clear of the label (also what the mockup prompt asks). Inside CB = size label only.
- Care label = [MISSING]: fibre not chosen (LESSONS D7, never pick the nearest).
- Sizes = HI published evens 26–40 (Konpeito's 29/31/33 not added; Q6).
- No HI stone/enzyme wash for a check (greys the black, fuzzes the lines) — proposed rinse + soften.
- Flats + size-label code COPIED from Konpeito (not imported) so a Konpeito change cannot move this pack.

## Gotchas
- `git fetch origin` failed: "Your account is suspended" from GitHub → branch made from local `main` (27c0c70, 65 commits
  ahead of origin/main); push likely impossible.
- `scripts/env.sh` symlinks `inputs/*` into the project dir (`reference` link) — delete before committing.
- The 110 dpi preview makes the check alias into dark pockets; at 400 dpi pockets match the body — check zooms, not thumbnails.

## Next
- Founder answers Q1–Q11; drop in the ChatGPT mockups on T2; pick fibre → care label; Rev B; then a factory summary copy
  (LESSONS E15) before any factory send.
