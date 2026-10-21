# Wave jacket — Rev C ART round (founder 'Do A', PR #27) — 21 Oct 2026

## Why
continuity --art showed the traced ART itself failed the wrap seams (front and back mockup views drawn independently),
so four rounds of stitch tuning could not reach the seam targets. Founder: redraw the art in a band at each wrap seam;
shoulders are not wrap seams (W4); ecru = Isacord 0184 Pearl (W3); shell colour (W2) still open.

## What changed
| Item | Change |
|---|---|
| `seamredraw.py` (new) | per wrap seam: unroll both sides by seam length, glide-continue each side across (stripes at their own angle, matched at the stitch edge = pivot; rigid curls/drops moved whole, shift taken at their seam-nearest point), ONE min-mismatch DP cut (never within keep-out + 8 mm; side switches cost; outlines cheap; deleting art and one-sided keep-out corners penalised), foam into bare ends in lobes; locks so later seams don't undo earlier ones; `--grain` carries the close-up grain into the zones |
| `tonematch.py --no-recolour` | structure passes only; whole-region recolour would change stripes far from the seam |
| `redo_rc.sh` / `final_rc.sh` | Rev C art chain / build-QA-docs chain |
| `gates.py` | failing rows + gaps inside a redraw zone are NAMED (`RD_WHY`), still counted open |
| `pack.py` | G7 rewritten: Rev B art / Rev C art / Rev C stitched per seam + founder gate + redraw zones + before/after pages; shoulders n/a (W4); G3 ecru confirmed; G5 tiny-stop reasons; G8 pooled A16 back as headline + redraw breakdown |
| `build_size.py` / `make_current.py` | `tiny_why` per stop (reviewer item 5: merge or print the reason) |
| `test_seamredraw.py` | slope read, glide straightness (m=0 mutation red), DP band, foam lobes |

## Gotchas / dead ends
- First version mapped units by their centre → copies landed off the DP picture (glide shift at the centre ≠ at the seam). Fixed: shift at the seam-nearest point.
- `mapped()` produced invalid MultiPolygons (reflected rings self-touch) → whole pieces vanished after intersection. `clean()` now make_valid + union.
- Without a pivot the glide offsets slanted stripes by 2·m·d between the measured rows (zip: d≈17 mm) → the unchanged metric read them as broken. Pivot at keep-out + 2 mm = stripes meet at the stitch edge.
- Sleeve centre line (not a seam): a 42 mm mirror band read as a butterfly; internal line now 4-20 mm.
- Armhole front R underarm corner: the sleeve's underarm keep-out cannot hold art there; CORNER cost deletes the 4 mm one-sided run instead.
- Killed a build that had started 1 min before an edit (python had loaded the old build_size.py) — check process start times vs edits.

## Numbers
Size M (zip A2 OK, 26-page pack): BK 373,238 / 1,280 trims · FR 144,693 / 524 · FL 234,584 / 839 · SR 292,704 / 759 · SL 236,101 / 763 = **1,281,320 st / 4,165 trims**, max stitch 7.41, 9 threads.
Wrap seams: 9 of 10 graded pass the founder gate (stitched >= 85 and within 5 of art); armhole front R meet 93 vs art 100 = one 1 mm column of 15 mm (FAIL shown, not redefined). Table: REVIEW_OPEN.md (Rev C).
A14: 19 failing rows (4 inside redraw bands, 12 drop-into-crest merges, 3 small misshapen) - all shown as crops (G8, compare/a14_rows.png). A16 pooled 65-75 % (headline restored, under 85). Tiny stops: 25 kept with printed reasons (G5).

## Left open
SR curl definition (review item 3), independent A16 check, element-spec restyle, armhole front R corner column, W2 shell colour, chenille format.
