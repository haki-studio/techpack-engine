# RECAP 2026-10-28 — engine hat styles (techpack-engine-m2, builder)

Founder ask 2026-10-28: make the tech-pack engine hat-style aware; a hat design submitted for tech packing must pick
its hat style. Inventory: `HakiCode/missions/techpack-engine-m2/hat-styles-facts.md` (not redone).
Branch `engine-hat-styles` off 3bb01868, worktree `~/te-hat-styles`. GitHub suspended: local commits only.

## Progress
- [x] families/cap/family.yaml + styles.yaml (9 styles) — `capstyle.py check` → 9 valid, 296 proposed values across them
- [x] engine/capstyle.py (load, strict validate, style_for_product, CLI list|show|check|check-project|product)
- [x] engine/cap_pages.py (H1 style sheet, H2 POM, H3 flats / K1 knit, H4 embroidery, H5 construction+BOM, F1) — renders
- [ ] intake plan/apply style gate + dispatch build gate + /techpack doc
- [ ] tests red-then-green
- [ ] independent review, reviews.log, DONE to lead

## Decisions
- A facts-file cell with no source tag is treated as unsourced → `{proposed}` (amber + F1), never a plain value.
- Conflicts stay `{proposed}` + a style `factory_questions` entry: ASCE 5 vs 6 panels, trucker back height 12.5 vs
  16.2–16.8, ripstop 6 panels; Radical Ed → asce-dad is a proposed product mapping.
- Drawing-only constants (head_ratio 1.22, strap opening 7x5, 8 brim topstitch rows) live in `family.yaml block:`, all
  proposed, and print on F1 under "Sketch constants (drawing only)". The POM chart governs; the flats are a sketch.
- Cap-frame limits per position are all proposed (none recorded); H4 turns a style's art red if it exceeds the frame.
- **No CJK on pages**: this machine has no CJK font (fc-match → DejaVu), so 顶刀模/舌刀模 printed as boxes. The Chinese
  terms stay in a yaml comment; pages print "crown die" / "brim die".
- Product → style: longest `match` substring of the product name; non-hats (Hat Box, Mystery Hat, tees) → None.

## HANDOFF (session-size limit hit, 2026-10-28)
WIP commit `ee57afe74cfb019104f1a463e4e424128af7d5e1` on `engine-hat-styles` (worktree ~/te-hat-styles, not pushed).
Sample renders (gitignored): `~/te-hat-styles/out/hat-samples/asce-dad/pages/*.png`, `.../beanie-cuff/pages/*.png`.
Run: `cd ~/te-hat-styles && ~/.venvs/techpack/bin/python engine/cap_pages.py <key> --out out/hat-samples/<key>`.

Looked at asce-dad H1–H4 + F1. Still to fix on the pages:
1. H3 BACK: the C dim is drawn vertically (12.5 cm) and overshoots the 10.5 cm crown — C is measured ALONG the back
   seam; draw it base→button and label "C 12.5 cm * along the back seam". (`view_back`)
2. H4: the side view runs off the right edge and the back box sits on the side view's edge. Re-lay out as three views
   in a row under the text (y≈120–195): front x≈60, side x≈150, back x≈240, one shared scale; back box centred above the
   strap opening on the back view. (`p_embroidery`)
3. H2 tolerance: add `pom_tolerance_cm: {proposed: 0.5, note: ...}` to family.yaml and use it for rows without `tol`,
   so the amber tolerance also lands on F1 (today it is amber on H2 but not listed on F1 — breaks the rule).
4. Re-check the under-brim topstitch rows render (fixed offset sign + `buffer(0)` in `brim_rows`, not yet looked at),
   TOP view label overlaps, and LOOK at beanie-cuff K1/H1 + one bucket H3.

Then the remaining build (see the founder ask in the lead's TASK):
5. `scripts/intake.py plan PLAN.json` (validate + print, refuse a hat garment {cap,hat,trucker,bucket,beanie,snapback}
   with no/unknown style naming `capstyle.load().valid_keys_text()`, use `capstyle.check_choice`); `apply` runs the same
   check before writing; write `style` + `garment` into STATUS.json (status_set.py keeps extra keys) and
   "- Hat style: <key> — <name> (crown die X, brim die Y)" into brief.md (capstyle.project_info reads that line).
   Add a `TECHPACK_ROOT` env override for the data root in intake.py + status_set.py so tests use tmp dirs.
6. `scripts/dispatch.sh` launch, role `build` (also --dry-run): run
   `python3 "$R/engine/capstyle.py" check-project "$slug" --root "${TECHPACK_ROOT:-$MAIN}"`; nonzero → print, return 2.
7. Docs: `.claude/skills/techpack/SKILL.md` step 1.3/4 (hat → ask the operator to pick from `capstyle.py list`; plan
   field `style`), docs/FAMILIES.md cap section, LESSONS.md row (problem → rule → check), CLAUDE.md layout line.
8. Tests (`tests/test_cap_styles.py` + intake/dispatch): 9 keys validate; unknown style refused naming valid keys;
   validator errors (POM without source, plain value, missing/unknown field, unknown POM code, knit with cap POMs);
   conflicts proposed; live PLM hat names → style (list in the session transcript: ECEG/Fire Fist/Rain Dinners/
   Superrrr/Big News/Greed Island/Guardian Deity/Valentine/Dead or Alive/Tiger → asce-dad; Will of D → sweet; You Wish
   → someday; Rabbit Escape/Shibuya → ripstop-6p; Haki "Block" → haki-cord-5p; Pink "Hearts" Beanie → beanie-cuff;
   Hat Box/Mystery/Tee → None); every style renders (knit has K1 not H3); proposed amber + on F1. Show red first.
9. heavy-jobs = 0 → full suite; commit; reviewer subagent on the exact sha; append reviews.log; SendMessage lead DONE.
