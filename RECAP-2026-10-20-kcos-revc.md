# RECAP 2026-10-20 — Keep Clean Our Space hoodie, Rev C (branch kcos-revc)

## Why Rev C
- Founder 2026-10-20: KCOS is top priority; finish Rev B's "final build + page check" as a deliverable Rev C.
- Rev B (19 Oct 20:41) was built from DSTs written at 20:13, but the art changed again at 20:55 (sparkle
  traced-silhouette fallback); the last rebuild was killed by the token-cost pause. Rev B therefore shipped one failing
  A14 row (FR field star, IoU 0.70) and DSTs that did not match the committed art. Rev C rebuilds everything.
- Factory answered 19 Oct (factory.json): frames 300 × 300 + 400 × 450, 12 colours, puff yes. Rev B splits were for the
  assumed 360 × 360.

## What changed (source)
- `kccore.py`: Rev C / 20 Oct; `CUT_KEEP_MM = 1.0` (house rule 6); make_pattern patch: flat stops cannot hide travel
  under the later puff stops (foam mask 0.5 mm inside the puff edge).
- `art_size.py`: `knock_under_puff` cuts flat work sewn before the foam (the glow stipple, `nok`) out of the puff
  footprint, keeping the 1 mm edge band (runs end 0.6 mm inside it).
- `kcstitch.py`: `foam_gates` on every written DST (puff stops only puff, nothing flat after them, base_under_puff = 0).
  Red on the Rev B FR M file (110 flat needle points inside the foam), green on Rev C.
- `prod_gates.py` (new, run by build_all): every file, every size: max stitch, ≤ 12 colours (PES), section fits the
  400 × 450 frame, foam gates, keep-outs. Exits 1 on any failure.
- Docs: G4 rewritten (7 founder questions amber), F1 "5b hoopings on your frames" + "6 puff" (puff confirmed), S1 foam
  check lines, G5 foam note, cover + README wording, T9 Rev C row, T8 pointer to G4; Rev B WIP patch applied (sleeve flat
  front half, CJK outlines, thread estimates flagged, same-card-code warning).
- Founder ruling (20 Oct): the garment mockup governs; reference.png only for the text wording. Checked: no close-ups
  exist and nothing traces or grades from reference.png (only shown on compare sheets / E pages).

## Decisions
- Fronts do NOT fit 400 × 450 in one hooping (M 267 × 512): 2 hoopings each; full single-hooping files ship too and F1
  asks which frame takes a whole front (factory confirmed 340 × 505 without naming the frame).
- Sleeves (M 435 × 558) need 2 × 2 on 400 × 450 (width 435 > 384 usable).

## Open
- 7 founder questions (STATUS.json) — built as proposed, printed amber on G4.
- ENGINE_NOTES 20 (foam travel mask → engine make_pattern), 21 (F1 multi-hooping list when frames are confirmed).
- Independent review of Rev C.
