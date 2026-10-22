# RECAP 2026-10-22 — Koi blossom hooded jacket, Rev D "RFQ / sample edition"

Session e63ef499 (builder-koi-blossom-hoodie-techpack), lead = lead-eng-koi-blossom-hoodie-techpack.
Brief: ~/.claude/company/missions/koi-blossom-hoodie-techpack/BRIEF-builder-RevD-rfq.md.
Branch `tp-koi-blossom-rfq` (worktree ~/te-koi-rfq), stacked on `standard-labels-rollout` (PR #54, T6b labels).

## Decisions
- **Factory-summary shape**: Konpeito's engine `engine/factory_copy.py` did not exist yet (its builder had not started).
  Lead TASK (19:3xZ): option (a), build it at project level as a THIN layer. It maps the Konpeito page kinds (same names
  and order) to the existing Koi page builders, and each page is tagged factory/internal. Swapping to the engine later
  means deleting rfq.py's table, not rewriting pages. Do NOT create engine/factory_copy.py.
- **Rebuild was required**: no Rev C build output (out/, DSTs) existed anywhere on disk. Every out/ is gitignored, and
  te-g2/g3/g4 hold only engine digitize experiments. The Desktop DST is the PR #52 tetra draft, not Rev C. So "DST
  sha-equal" can't be checked against an old file. Instead the rebuilt DSTs get a sha manifest and are rebuilt a second
  time to show the build is deterministic.
- Upstream steps that run_all.sh does NOT run (needed on a clean checkout): floratrace.py → fishtrace.py → scene.py.

## Progress
- [x] Rev C art rebuilt (traces + run_all): 158 DST/PES, sha manifest projects/koi-blossom-hoodie/bench/dst_sha_RevD.json; size M rebuilt a 2nd time = 22/22 identical (deterministic).
- [x] kbcore: REV = Rev D for the whole pack (REV_EMB = REV_GAR = REV), DATE 22 Oct 2026, ART_REV = Rev C, REV_LOG Rev D line.
  MODE ("internal" | "factory") + fx() + scrub() (SCRUB regex list for block / engine pages this project doesn't own:
  "(founder 22 Oct 2026)" on T6b, "Drum Island" on T2/T3, factory.json, LESSONS ids).
- [x] rfqgate.py = Pixel Sky rfq_text_gate (regex over the RENDERED PDF text) + check() (red-then-green built in).
  tests/test_koi_rfq_gate.py: 15 pass; with BANNED emptied 14 fail (proved red).
- [x] rfq.py: KINDS (Konpeito names + order) → page table → 3 PDFs + TBD md/png + sha manifest + factory zip.
  run_spec.py --factory builds *_SPEC_RevD_FACTORY.pdf (neutral reference/changes text). finish.py now writes
  HAKI_KOIB_INTERNAL_RevD.pdf + *_INTERNAL_files.zip (its README has founder/provenance lines → internal only).
- Gap found (TBD, decide with factory): T2 note 4 says welts/pocket bags/facings/lining are "as the jacket block".
  A new factory has no seam spec for that, so it's asked in Q2 item 7.

## Lead TASKs folded in (all 22 Oct)
- Shape = Konpeito's factory_copy (PR #57). fc_shim.py = byte-identical mirror @ 598ea82 (re-synced twice: f2b6245 draft → f7d46bb → 598ea82).
  Page(id, kind, title, audience, svg), 11 kinds. leak_gate on the SHIPPED PDFs via file_text (text + info + XMP), min_chars 40 per page,
  image_only = none. strip_creator run; Author/Creator blank.
- Summary trimmed to 12 pp (lead: one page per kind): C1 · T2 · T3 · T4 · T6 · T5 · T6b · G2 · E0 (threads + files + hooping) ·
  E01 / E02 (one page per element: view, placement, stitches + hoopings per size, threads with ΔE, open questions, "full spec: TECHPACK p. X–Y")
  · QF (quote first, then tell-us, strike-off, open points, packing). TECHPACK keeps everything (26 pp). INTERNAL = finish.py merge + TBD (27 pp).

## Gaps the gate / page review caught (fixed)
- 16 first-run leaks (reference_fish.png in the thread column, "DST read-back", my own "fidelity").
- F1 (engine factory.requests_page) printed the profile on file as if it were the new factory's: "Frames on file 300x300, 400x450",
  "max 12 colours (confirmed)", "You can sew chenille". Factory mode now passes a neutral profile → asked, not stated. ENGINE_NOTES ask.
- 598ea82's history pattern hit F1's "art W x H mm → 2 hoopings today": narrow Koi scrub rule + ENGINE_NOTES ask (engine is not mine).
- Element-spec mockup shows the old koi; factory change notes now say the files' tetras replace the mockup's fish.
- Royal blue + Slate share Polyneon 1943: E pages print ΔE and an automatic "pick the nearer of two from your card" note.
- rfq.py re-runs used to append TBD to INTERNAL again: fixed (drops an earlier TBD page).

## Tests
tests/test_koi_rfq_gate.py 24 pass (red proven: Koi rules/extras emptied → 8 fail). Full suite 564 pass, 2 fail =
test_konpeito_gates (needs Konpeito's gitignored out/front_stars.json; no Konpeito file touched).

## Next
- Lead: reviewer + td pass on the PR head, then copy out/HAKI_KOIB_FACTORY-SUMMARY_RevD.pdf, _TECHPACK_RevD.pdf, factory-files zip,
  TBD_RevD.md/png to Desktop/TECH PACKS/4 (builder does not write there).
- When PR #57 merges: `import factory_copy as FC` in rfq.py / rfqgate.py, delete fc_shim.py.
- Founder card koi-blossom-rfq-questions: all ★ defaults shown amber; change Q2/QF/E01/E02 text if he answers differently.
- Session size: transcript ~19 MB at the end; next Koi work should start a fresh builder from this RECAP.

---
# Rev E (session 14252606, builder; brief BRIEF-builder-RevE-fixes.md) — fix round on PR #59

## What changed and why
- **Founder rule**: the factory summary must hold everything the sample room needs. The TD said Rev D could not
  produce a correct first sample (no seam spec, no bag-out order, welt/zip/wash undefined). Rev E adds pages, one per topic.
- New `construction.py` (project level; the zip-hoodie block itself is NOT edited, other jackets use it):
  - **CS** seam table: 22 seams, SA read from the pattern edges, stitch/SPI/topstitch/thread/finish amber; wash + shrinkage block (M5 ★ no garment wash).
  - **CI** inside view drawn from the real pattern pieces (F01/K01/L01, B01/K02/L02 + CB pleat from L02.internal) + 13-step bag-out order.
  - **CD** welt detail (P01 fold/length, bag P02 numbers, welt-to-facing 9.3 cm, welt low corner 7.7 cm above hem), zip/hood/neck junction,
    zip garage P03, hanger loop P04, zip ordering lengths (pattern → rounded, N2), CF keep-out reference (S10).
  - `install(ZB)` overrides T2 (notes 9-10 + callouts), T3 (D+/H+ rows from the band cut lengths, every callout drawn, hood measuring
    conditions), T4 (S02 drawn, not-to-scale note, "removed from the jacket" line gone), T5 (centre-panel label off the table).
- rfq.py: QF split into **QF** (quote + S14 items, sample plan = ONE order, pattern/file rules, strike-off with split files only + panel
  before/after measurement) and **QF2** (feasibility (a)-(m) closed YES/NO + numbers, open points, labels, colour standards, packing).
  E0 rewritten (heading gap, split-file stitches/trims column, run-time basis, METHOD = oversized block + re-cut, frame line, crosses).
  E01 L/XL note (N8), E02 sleeve sign convention from the pattern (S9). Cover contents no longer truncated (review MUST).
- pack.f1_pages: one frame (400 × 450) everywhere, split files only in the factory copy, thread-card grammar, ΔE per brand, S4 wording.
- rfqgate.EXTRA: `\.(png|jpe?g|py|json|pkl)\b` (review SHOULD 2) + test (red: 5 fail without it; green 29 pass).
- REV = Rev E (kbcore + rfqgate), REV_LOG line.

## ★ defaults built (lead asks the founder; all amber + in TBD)
- S2 hem gather: kept for the M sample; re-derive grading before bulk. Pattern numbers unchanged.
- S8 near-empty hoopings (FL S1 234 st / 7 trims, SL S1 396 / 5): kept; cost = 2 of 7 hoopings.
- S13 FR at L/XL: **kept + flagged, not re-fitted** — a re-fit needs a new placement rule + new L/XL DSTs, not an existing re-fit.
- M5: no garment wash.

## Dead ends / caveats
- Drew the pocket bag on CI/CD at first: the pattern bag (20 deep) perpendicular to the welt crosses CF, hanging down it crosses the hem.
  The real orientation isn't in the pattern, so the drawing was removed and CD asks the factory to lay it on the pattern (TBD item).
- PR #57 head moved (640ea23) but engine/factory_copy.py is unchanged since 598ea82: no shim re-sync.
- No DST rebuild: stitch files are Rev D's; rfq.py now compares bench/dst_sha_RevE.json with RevD.
