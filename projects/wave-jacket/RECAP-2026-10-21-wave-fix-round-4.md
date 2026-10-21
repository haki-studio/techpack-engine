# Wave jacket — fix round 4 (PR #27, review of b448e33) — 21 Oct 2026

## What changed and why
| Item | Root cause | Fix |
|---|---|---|
| A16 foam 20-26 % | loop texture = scalloped rings (chaotic in 4 mm tiles); padded rows at the curl tangent, off the close-up grain | foam + details in 4 mm grain cells (`flowdir.fm_grain_parts`), loop texture = grain streamlines (`foamcord.py`) → 75-79 % |
| A16 headline | pooled every object in a tile (crest/stripe borders = chaos by construction) | per object (groups), pooled printed beside it |
| A14 SL mass h 0.38 | "keep-out edge" excused real art inside the limit | excuse only < 2 mm slivers; gapfill fills the rest |
| A14 BK mass w 0.79 | 1-2 mm spray tail below the A15 gap size | gapfill tails |
| G9 cut lines | detector flagged stripes that cross the seam square | `discont.flow_check` + `test_discont_flow.py` |
| docs | zip paths, count mismatch, typed date | fixed |

## Gotchas hit (ENGINE_NOTES 32)
- tonematch restarts from an existing `art_M_pretone.pkl`: a partial chain re-run silently dropped the new fills (one wasted rebuild). `redo_r4b.sh` deletes it.
- importing gapfill restored `art_M_pregap.pkl` at import time: now only under `__main__`.

## Pipeline order (size M)
`redo_r4.sh` (full art chain) or `redo_r4b.sh` (from gapfill), then `final_r4.sh`.

## Left open
13 small drops + 1 curl fragment (A14); FR/FL direction 82/80 %; 19 cut lines; seam meet/tone. Founder questions unchanged.
