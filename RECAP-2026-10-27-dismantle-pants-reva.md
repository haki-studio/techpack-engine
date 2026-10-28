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

## Fix pass (coordinator, 27 Oct, later)
- New M1 page after T1: founder ChatGPT mockup, REFERENCE for look only; departures (a) rounded back pockets, (b) check ~16.8 mm (25 squares across the half waist, scaled as HI 32; dmprint.mockup()), (c) cropped, (d) label/loops match. T2 placeholders replaced by mockup thumbnails + flats-leg note (Konpeito flat-lay tracing; team checks vs real HI fit). "mockups" no longer [MISSING].
- New F1 page: 12 factory yes/no questions (D2/D7/D8/D9/D11/D13/D15) + check-matching QC block; all tolerances [TBD — Haki/factory to set], none invented.
- Text fixes: rivets = outer top corner of each scoop + 2 coin corners = 4, HI lists 5 (T5/T6/T7/F1); T7b weave moved to size label, back label flat woven heat-cut/ultrasonic (D17); D2 CB seam pressed open + trimmed under label, white needle / black bobbin, clear of WB topstitch, min WB height factory to state, scrap-mock photo, sewing order per factory (T6, T7 detail draws the seam); D3 REFERENCE banner on T3; D4 belt-covers-label in Q3; D5 grain [proposed], mill shrinkage + sanforized ask, repeat = finished after wash; D8 pocket size/placement/angle from factory; D10 COO + RN [MISSING]; D19 "factory to quote"; D1 physical-swatch box on P1.
- Q1 now Q1–Q14 (Q11 pockets, Q12 check size, Q13 length, Q14 owed by Haki).
- Flats: back + coin pockets no longer have their own fill, so the body check shows through (matched, no darker aliasing).
- PDF sha256 2ca477f7e8377bd421896c925b21f7d630872bc54dcb867ed57395ec6e100969, 12 pages; overwritten in Desktop/TECH PACKS/Dismantle Pants.
