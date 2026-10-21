# Wave jacket — fix round 3 (PR #27, review of fe0a29f) — 21 Oct 2026

## Root causes found (and fixed)
| Review item | Root cause | Fix |
|---|---|---|
| 1 stale zip | `_small.pdf` was shrunk BY HAND after `finish.py` had zipped the old one | finish.py shrinks the fresh pack itself, refuses an older small file, then re-reads every DST in the zip and checks the zipped PDF + README print those numbers (`zip_check.json`) |
| 2 A14 drops | (a) `dst2.clean_vis` deleted each drop's shade/grey crescents (< 0.7 mm wide) -> bare navy inside the traced drop; (b) the gate's `visible_segments` re-centring under-read satin zigzags (false holes) | (a) `waveart.keep_unit_slivers`: slivers go to the same motif's touching region; (b) drop gate = z-buffer raster of all stitches (red-then-green proven on the round-2 files) |
| 3 A16 drops | turning satin across drops; close-up grain runs along them | one declared angle per drop = long axis, fixed-angle satin (`waveart.drop_angles`, `wavecore` declared branch) |
| 3 A16 stripes | geometric field + twist 79-84 % | `grainfield.py`: stripe cells follow the close-up's thread grain where clear (weight >= 0.6, coherence >= 0.3) |
| 4 seams | armhole back R = 3 mm of art (one drop at the underarm corner), back render bare along the armhole: not a mapping bug; shoulder L one-sided (back render bare) | `seamedge.py`: one-sided runs end in foam lobes, not a straight cut |
| should-fix | swatch: w1 became ecru on 20 Oct, so the "white" tiles sewed ecru twice; spec p2/p6 crops showed bare fabric (fixed offsets), SL map ran off the page | swatch A/B ecru, C/D white alt; crops centred on the art they name; p2 re-laid |

## Pipeline order (size M)
`redo_r3.sh` (waveart -> gapfill -> tonematch) then `final_r3.sh` (seamedge -> grainfield -> build_size x5 + swatch -> qa_chain -> views/covers/compare -> build_all -> finish incl. zip A2).

## Engine proposals
ENGINE_NOTES 22-26.
