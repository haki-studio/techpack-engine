# RECAP 2026-10-28 — engine hat styles (techpack-engine-m2, builder)

Founder ask 2026-10-28: make the tech-pack engine hat-style aware; a hat design submitted for tech packing must pick
its hat style. Inventory: `HakiCode/missions/techpack-engine-m2/hat-styles-facts.md` (not redone).
Branch `engine-hat-styles` off 3bb01868, worktree `~/te-hat-styles`. GitHub suspended: local commits only.

## Progress
- [x] families/cap/family.yaml + styles.yaml (9 styles) — `capstyle.py check` → 9 valid, 296 proposed values across them
- [x] engine/capstyle.py (load, strict validate, style_for_product, CLI list|show|check|check-project|product)
- [x] engine/cap_pages.py (H1 style sheet, H2 POM, H3 flats / K1 knit, H4 embroidery, H5 construction+BOM, F1) — renders
- [x] intake plan/apply style gate + dispatch build gate + /techpack doc (session 3)
- [x] tests red-then-green (test_cap_drawing.py 30, test_cap_styles.py 59)
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

## Session 2 (builder #2, 2026-10-28) — drawing fixes done; HANDOFF again (session-size limit)
Done + committed (see git log on engine-hat-styles):
- **Brim drawn at E/F** (lead fix a): `CapGeom.brim_poly` rebuilt — width = F end to end, centre depth = E (crown seam at
  CF to the tip), seam edge curves back by a new drawing-only constant `block.brim_inner_depth_cm` {proposed: 3} (on F1).
  TOP view draws the same brim carried under the crown (convex hull with the oval front, `brim_drawn(g, "top")`) so no
  gap shows. Was 0.84 deep/wide on asce-dad vs chart 0.39; now 0.39 on both views for all 7 cap styles.
- **Labels clear of outlines** (fix b): SIDE G beside the tip, D lifted off the button; TOP head length/width outside,
  A label under the oval; UNDER-BRIM F right of the brim, E below it, rows label above; INSIDE labels outside with leaders.
- **BACK C** (fix c / old step 1): dimension base → button, outside the crown, label "C … along the back seam".
- **H4** (old step 2): three views in a row under the text, one scale; back frame box above the strap opening.
- **H2 tolerance** (old step 3): `pom_tolerance_cm` {proposed: 0.5} in family.yaml; H2 rows without `tol` use it; F1
  lists it under Measurements.
- `tests/test_cap_drawing.py` (29 tests): brim ratio within 10% on TOP + UNDER-BRIM measured from the drawn SVG paths,
  not-square guard, H3 label-vs-outline check (+ a probe test proving the check catches an overlap), C stops at button.
  **Red then green:** against the old cap_pages.py 28 failed / 1 passed (ratio 0.84 vs 0.39, the exact overlaps the lead
  saw, C top at -120 vs button -99); against the new one 29 passed.
- Looked at: asce-dad H3 + H4 (fine). NOT yet looked at after these changes: asce-dad H1/H2/F1, beanie-cuff K1/H1, a
  bucket H3, other cap styles' H3 (tests pass for all 7 caps).

### HANDOFF — next builder, in order
1. Re-render asce-dad + beanie-cuff + bucket (`~/.venvs/techpack/bin/python engine/cap_pages.py <key> --out
   out/hat-samples/<key>`) and LOOK at every page (H2 tolerance row, F1 new items, K1, bucket H3).
2. Old steps 5-9 above are still open: intake.py style gate + STATUS/brief + TECHPACK_ROOT; dispatch.sh build gate;
   SKILL.md / FAMILIES.md / LESSONS.md / CLAUDE.md; tests/test_cap_styles.py (catalogue, refusals, product → style,
   every style renders, proposed on F1) + intake/dispatch tests, red then green.
3. heavy-jobs = 0 → full suite; commit; independent reviewer subagent on the exact sha; append reviews.log; SendMessage
   lead-eng-techpack-engine-m2 DONE with sha, test counts, PNG paths.

## Session 3 (builder #3, 2026-10-28) — gates, tests, docs done
- **intake.py**: new `plan PLAN.json` (check + print, exit 1 on refusal); `apply` runs the same check first and refuses
  the WHOLE plan before writing anything. A hat garment (cap/hat/trucker/bucket/beanie/snapback) needs `"style": "<key>"`
  from the catalogue; missing / unknown / wrong-kind → `REFUSED <slug>: ...` naming every valid key. The style lands in
  STATUS.json (`garment`, `style` via new `status_set.py --field k=v`, mirrored to the board) and brief.md
  (`- Hat style: asce-dad — ASCE dad cap (crown die SN508, brim die 202)`). `TECHPACK_ROOT` overrides the data root in
  intake.py, status_set.py and dispatch.sh (tests use tmp dirs).
- **dispatch.sh build**: runs `capstyle.py check-project <slug> --root ${TECHPACK_ROOT:-$MAIN}` before anything else;
  refusal → message on stderr, return 2, no session. Projects with no garment recorded pass (no existing hat projects
  in main, checked).
- **tests/test_cap_styles.py** (59): catalogue (9 keys validate; refusals name every key; wrong-kind; non-hats need
  none; 8 validator errors; broken yaml won't load; conflicts proposed; 19 live product names → style; every style
  renders, knit K1 vs H3, F1 lists every proposed value) + intake gate (plan/apply refuse and write nothing; unknown
  style; STATUS + brief + project_info round trip) + dispatch gate. **Red:** 9 failed before the gates (7 gate tests +
  2 test-side needle mistakes fixed); **mutation red:** 29 failed with check_choice / leaf validation / product match
  disabled; green 59.
- **Docs**: SKILL.md step 3 (hat style required, `capstyle.py list` / `product`, ASK the operator "Which hat style is X?
  Pick one: ...") + step 4 (`intake.py plan` first, table gets a hat-style column); docs/FAMILIES.md "Hats" section;
  LESSONS H1 (new section H); CLAUDE.md layout line.
- **Looked at** (4 PNGs): beanie-cuff K1 fine; bucket H3 — E label sat on the brim's bottom edge in all 3 side views
  (dim drawn right→left puts the label above the line) → fixed (tip→crown), and the H3 label test now covers the bucket
  (red 1 → green); asce-dad H1 + F1 fine. Note for the lead: F1 quotes the current physical seam tape
  'HAKISTOP · WRITE YOUR OWN STORY' (asking to replace it) — factual, left as is.
- Gotcha: the red run of the intake tests (before TECHPACK_ROOT existed) wrote `projects/probe-cap/` into the worktree;
  deleted, and the green run leaves the tree + ~/.techpack/board clean.
- **Full suite** (heavy-jobs 0): 705 passed, 2 failed — both `test_konpeito_gates.py` soot tests, FileNotFoundError
  `out/stitch/HAKI_KJ_07a_front-leg-trail-upper.json` (gitignored Konpeito build output absent in this fresh worktree;
  branch touches no konpeito/digitize file). Hat tests: test_cap_styles 59 + test_cap_drawing 30 green.
- **Review 1 (9cb02f84): REQUEST_CHANGES** (logged in reviews.log). Fixed:
  1. plurals / hyphens slipped past (`caps`, `Beanies`, `hats`, `snapbacks`, `snap-back`) → `capstyle.garment_words`
     folds plurals + "snap back"; `visor` added (no style fits it yet → refused with "add one to styles.yaml first").
  2. shell injection: intake's `os.system(... --field garment="...")` ran `$(...)` → `subprocess.run` argv list.
  3. `check-project` passed any project with no garment line → now judges by the product name (brief/README title or
     slug): a hat word or a known hat product (e.g. "Fire Fist") needs a style; the 14 main projects all still pass.
  + `status_set.py --field` only takes garment/style.
  Tests: red 9 (6 spellings, injection, field allowlist, no-garment) → green; mutation (plural fold + fallback off) red 6.
