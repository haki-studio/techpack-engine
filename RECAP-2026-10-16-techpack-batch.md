# Recap 2026-10-16 — first /techpack batch (Grand Line, Forestball, Moon)

## Products (all Drum Island block, all delivered Rev A)
| Product | Pack | Size M stitches | Machine time M | Open with client |
|---|---|---|---|---|
| grand-line-jacket | `out/HAKI_GRLN_FULL-TECHPACK_RevA.pdf` (26 pp) | 220,855 (front only) | ~4.9 h | retail name (One Piece term), dye method, larger frame?, welt moved 18 mm to CF, solid vs dashed rays |
| forestball | `out/HAKI_FB_Forestball_FULL-TECHPACK_RevA.pdf` (31 pp) | 419,262 | ~9.3 h | placeholder size vs licensor art, dye method, border frame vs 4 hoopings; density lighter than mockup in places → sew-out |
| moon | `out/HAKI_Drum-Island_moon_FULL-TECHPACK_RevA.pdf` (41 pp) | 298,328 | ~6.6 h | wires wrap side seams only (not over sleeves), 2-hooping fronts, placeholder 71×89 mm (M) |

## Decisions
- Licences confirmed by Devin 2026-10-16 for the Moon figure AND the Forestball orb → both are empty, marked placeholder boxes
  (basting outline, no-stitch zone, DXF layer 8). The Forestball client note said "replace with an original"; Devin's licence
  confirmation superseded it.
- Forestball grade A is 90 % (92 % failed the XS side keep-out).

## Engine (commit 6bb49cd)
Merged the small, testable proposals; the rest is ordered in `docs/ROADMAP.md`. LESSONS A8, A9, B14–B19, C8, E5, E6.
- Gotcha: the B17 stitch-rounding change has no unit test — couldn't make a synthetic design produce a 7.45–7.5 mm stitch; the
  per-file `verify()` gate is the check.
- Drum Island (delivered earlier) was NOT re-verified against B16 (split arm) or C8 (shoulder): its `out/` pickles aren't on this
  machine. Its `emb_place.clearances()` already measures on pattern pieces, so C8 should have shown on its T13; B16 needs a
  re-measure of its split files the next time that project is rebuilt.
- System python has no engine deps; `~/.venvs/techpack` → `~/.venvs/techpack-grand-line`, activated by `env.sh`.
