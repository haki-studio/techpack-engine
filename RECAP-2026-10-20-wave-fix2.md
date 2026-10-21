# Wave jacket — fix round 2 (PR #27 review) — 20 Oct 2026

Worker session 0bf098b0, branch `tp-wave-jacket`. Handed off at a clean point (session size); the full brief, numbers and
next steps are at the top of `projects/wave-jacket/REVIEW_OPEN.md`.

## Decisions + why
- Close-ups are pixel-aligned super-res crops of the mockup (SIFT fit = pure scale + shift), so they replace the render's
  pixels inside their footprints for tracing and gating; the mockup still decides placement (founder rule).
- A15 "moved by the wrap" was hiding real bare navy; gaps are now filled from the mockup's own tones (0 unexplained).
- The motif gate reads the visible DST layer (A17) and each drop's own stitches (A21); hidden travel had failed a correct crest.
- Ecru #D3CAC1 = Isacord 0184 Pearl; the founder's 0151 / 1801 candidates are Cloud / Barely Blue in our thread book (asked).

## Open
A14 drop rows, A16 stripes < 85 %, seam tone regression (gapfill after tonematch: reorder), page legibility, docs + review.

## Round finished (same session, ~23:10) — the fresh-session handoff was cancelled
The queued fix job was 4th in a full queue, so this session finished the round itself. Final state + per-item status:
`projects/wave-jacket/REVIEW_OPEN.md` (bottom table). Totals M: 1,053,146 st, 4,145 trims, 8 hoopings, max 7.46.
Extra fixes found on the way: the render's welt-pocket lips and the close-ups' wash creases were being traced as stripes
(masked: wavetrace DETAILS_PX + crease rule); gapfill now runs before tonematch (redo_r2.sh). Stripes sew along a flow field
(flowdir.py). Pack G2-G9 re-laid out (20 pages). Copied to Desktop/wave-RevB.
Open: drops (39 rows), stripe direction 79-84 %, seams (red on G7/G9), foam swatch not rebuilt in ecru.
