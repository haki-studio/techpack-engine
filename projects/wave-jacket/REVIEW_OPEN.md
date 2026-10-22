# Open review findings — Wave, M sampling package Rev A review (→ Rev B, with the seamless wrap redo). Fidelity first (A11/A12/A13).
Hard limits passed (17 M files, max 7.45, 9 colours, PDF/README == readback 804,280 st / 3,705 trims / 12 hoopings, DST == PES counts, splits ≤316×336 incl. crosses, split union 98–99.6 %, crosses agree 0.2 mm, compare sheets from DSTs).
Founder context: the body shape (shoulders, armholes, sleeves) is UNCHANGED, so a Drum Island M placement plot is valid. Only the shell colour, hardware colour and (probably) cuff/hem rib change.
1. BLOCKER No placement. The DST origins are in pattern coords, and G5/G6 refer to DXF layer 13, the welt and the split lines, but there is no DXF or plot in the package. Ship an M-only 1:1 plot PDF + DXF per piece with the art outline, split lines, cross positions, file origins, reference edges (the sleeve y-origin is the underarm line) and the match marks. Label it "art placement only — garment pattern to follow".
2. HIGH No cross-piece match marks (A4/A5). The wrap needs a stripe-end crossing mark (position + tone) on both mating edges at the armhole, side seams and CF zip, printed on the plot and in the spec. Stripe tone and width must be identical on both sides of every seam.
3. HIGH Sleeves have an internal seam at the fold. SR has an ~8 mm bare navy strip mid-sleeve; SL has a hard vertical cut through the stripes/crest at the top left. The source flat-lay is stitched together. Rebuild each sleeve as one continuous trace with no centre-line seam.
4. HIGH Foam (A13): the grey hollows are flat blobs up to ~20 mm → thin ridged grey lines. The curl cords are fragmented → continuous. Also build a chenille/moss variant of the foam file so the strike-off can compare padded tatami vs chenille (F1 already asks).
5. HIGH Stripes: tone-traced tatami with dark dash flecks inside the pale bands → continuous twisted-cord bands with continuous 2–3 mm cream rope lines, each with its own direction. Drop the sub-2 mm tone flecks.
6. MED Foam white #F0EDEA is too cool. The close-up foam averages ~#D3CAC1 warm cream. Add an ecru candidate (Isacord 0151 / Polyneon 1801) and show the render sample next to each hex. Flag that the whole board needs re-checking on the new shell colour.
7. MED Hooping: per-piece section order (S1→S2→S3/S4), which cross re-registers next, how to hoop a cut panel (floating/sticky). Backing: confirm the weight for dense padded fill on 12 oz duck, or specify a double layer under the foam. Say the hoops must not crush the padded foam.
8. MED After the wrap redo, regenerate the stale text ("15 mm short of the armhole", "No seam-true wrap", "armhole is a normal 15 mm keep-out"), the keep-out table and the compare sheets. Keep-outs come from the Drum Island block; re-check the hem/cuff ones when the rib is removed.
9. MED A2: add a render-vs-DST motif count table (curls, drops) per piece.
10. MED Tiny stops: SL stops 8–10 and 15–17 (24–102 st), BK stops 12–13 (143, 98) → merge into an adjacent same-colour stop if fidelity allows.
11. LOW BK S3 hooping is only 17k st. Re-run fold-into-neighbour after the redo.
12. LOW The G2 art-box table overflows the page ("411x360" column clipped). G4 568 vs G5 569 rounding.
13. LOW G1 flat preview shows a dark collar triangle that reads like a hood. The collar is confirmed, so fix the preview.
14. LOW F1 "price the strike-off files" lists the 12 splits, not the 5 full files. Say the full files are reference only.

## Status after the Rev B fix round (20 Oct 2026, branch tp-wave-jacket) — numbers from the rebuilt size-M files
| # | Status | What / evidence |
|---|---|---|
| 1 | DONE | `placement/` 1:1 plot PDF + DXF per piece (+ ALL), "ART PLACEMENT ONLY - garment pattern to follow", art outline, keep-out, split lines, crosses, file origins, CB/CF, sleeve centre line + underarm y-origin, match marks; regenerated on the new files (91 marks on 10 seams). |
| 2 | PARTIAL | Marks on the plot + G7 table (both mating edges, position + tone). NEW `tonematch.py`: follower stripes take the leader's thread across every seam (art, same thread 1-4 mm in: CF zip 33→91 %, side R 35→85 %, underarm R 34→79 %, armhole front L 60→89 %). DST continuity (thread group ±4 mm) still 22-92 % per seam: where the two render views disagree on whether a stripe is there at all, the tone cannot agree. |
| 3 | PARTIAL | No bare strip / cut on the centre line; stripe thread identical across it (art 100 % both sleeves). DST: sleeve centre L meet 75 % / tone 67 %, R 71 % / 45 % — the halves still come from two views; a true one-view re-trace of the sleeves needs a sleeve close-up. |
| 4 | DONE (lockstitch) | Grey hollows = thin ridges + one continuous spiral cord per curl (Rev B); bare pockets left inside the foam filled (20 Oct, ~1,000-1,600 mm² per piece). Chenille/moss: foam SWATCH (padded vs moss look, white vs ecru) + a chenille PATH PLAN per piece; no chenille machine file until the factory names its format (LESSONS B33 - Rev B had shipped _CHENILLE.dst files, removed). |
| 5 | DONE | Twisted-cord rows (along + 15°), continuous rope cords, flecks dropped (Rev B) + 20 Oct: stripe patches < 150 mm² merged into their band (BK 378→145, SR 354→130 WV regions): one continuous cord per stripe. |
| 6 | DONE | G3: render sample beside every hex, ecru candidate #D3CAC1 (Isacord 0184 Pearl ΔE 3.2); "Polyneon 1801" is Barely Blue, not ecru (ENGINE_NOTES 13); whole board flagged for re-check on the new shell. |
| 7 | DONE | G6: section order + which crosses re-register, floating a cut panel, magnetic frame / never hoop over sewn foam, 3.0 oz cutaway + 1.5 oz tearaway under the foam [proposed]. |
| 8 | DONE | Stale texts regenerated (mockmap docstring, FM rule, spec "what changed"), keep-out table + compare sheets from the new DSTs. |
| 9 | DONE | G8: render vs DST motif counts per piece and family (curls, drops, stripes). |
| 10 | PARTIAL | merge_tiny: BK 15→13, FL 19→17, SR 15→11, SL 18→17 stops. Still tiny (30-158 st): BK 12-13, FL 8-10 + 15-17, SL 8-10 + 15-17 - their objects touch art of another colour sewn in between, so moving them would change what lies on top (fidelity first); the factory can merge them on the strike-off. |
| 11 | N/A | Back is 2 hoopings on the confirmed 400 × 450 (no S3). SL S1 is 17k st: merging it into S2 would be 516 mm wide (> frame), so it stays; listed on G5. |
| 12 | DONE | G2 re-laid out (scale 0.118, nothing overlaps); G4 / G5 / spec all read the same files (the spec merged into Rev B was a stale Rev A file - fixed). |
| 13 | DONE | G1 preview: shirt collar lying flat (back stand + two leaves), no hood shape. |
| 14 | DONE | F1: "The full files are REFERENCE only - price + sew the hoopings"; README says the same. |
| new | OPEN | A14 motif gate: 39 failing rows (mostly 4-12 mm² spray drops at IoU 0.6-0.7, a few moved by the wrap) + 18 unexplained bare areas ≥ 25 mm² (G8, compare sheets). A16 direction: stripes 52-71 % OK, foam 15-21 % against a 0.7 px/mm render (indicative only, ENGINE_NOTES 17). |

## Status after fix round 2 (PR #27 review on be032f8; 20 Oct 2026 late) — numbers from the rebuilt size-M files
| Review item | Status | Evidence (gates_M.json, continuity_M.json, discont_M.json, dst_current.json) |
|---|---|---|
| 1 A14 motif rows | PARTIAL | 53 -> 44 failing rows. Curls 0 failing on all 5 pieces (FL big curl was hidden travel merging crests; the gate now reads the VISIBLE DST layer). Drops 39 + stripe masses 5 open: drops re-traced at close-up resolution and graded at 12 ppm with only their own stitches; remaining rows IoU 0.5-0.7 on 4-25 mm2 drops. |
| 2 A15 bare areas | DONE | 18 -> 0 unexplained on every piece: gapfill.py fills every gap from the mockup / close-up tones (merged into the touching stripe / crest), 'moved by the wrap' is no longer an explanation; only keep-out edges stay bare (BK 6, FR 1, FL 1, SR 1, SL 3). |
| 3 A16 direction | PARTIAL | Stripes 52-71 -> 79-84 % on the CLOSE-UP grain (flowdir.py: rows along a stripe flow field, no across-satin; twist 8 deg). Target 85 not reached. Foam = lockstitch ALTERNATE (chenille ecru is primary, founder 20 Oct): 19-25 %, said plainly on G8 (2/2). |
| 4 Seams | OPEN (red) | Gap fills now run before the tone handover. DST meet / tone: CF zip 57/51, side L 58/44, shoulder L 20/23, sleeve centre L 53/46, R 58/39, armhole back R 0/0 (3 mm of art), armhole front R 59/47; armhole back/front L 93/85, 93/64. G9: 32 parallel straight cut lines + 62 across, 97/722 edges jump - all listed in red on G9 (1/2), none shown green. |
| 5 G1 streaks | DONE | views.py drops ill-conditioned sleeve-fold pieces from the preview; the render's welt-pocket lips (traced as stripes, A15) and close-up wash creases are masked in wavetrace (DETAILS_PX, crease rule). |
| 6 Legibility | DONE | G2-G9 re-laid out at 2.2-3.0 mm text with wrapping and continuation pages (20-page pack); G2 art-box table fits; G9 crops full page. Element spec pages (01 p1-6) not re-laid out. |
| a close-ups | DONE (used) | register_closeups.py: all 7 close-up crops register as pure scale + shift (92-98 % inliers); trace classes, drop outlines and the A16 grain come from them inside their footprints. Sleeves still come from two half views (each close-up quadrant is a half view): no one-view re-trace exists. |
| b ecru + chenille | DONE (docs) | w1 = Foam ecru #D3CAC1 -> Isacord 0184 Pearl (ΔE 3.2); 0151 = Cloud, 1801 = Barely Blue (asked). F1 / G4 / G5 / spec: chenille ecru first (path plan + format question, B33), lockstitch files = alternate. Foam swatch file not rebuilt this round. |

## Status after fix round 3 (PR #27 review of fe0a29f; 21 Oct 2026) — numbers from the rebuilt size-M files (zip_check.json, gates_M.json, continuity_M.json, discont_M.json)
| Review item | Status | Evidence |
|---|---|---|
| 1 stale zip | DONE | Cause: `_small.pdf` was shrunk by hand AFTER finish.py zipped the old one. finish.py now shrinks the fresh pack, refuses an older small file, unzips the package and re-reads every zipped DST: the zipped 20-page pack + README print BK 318,135 · FR 124,535 · FL 190,153 · SR 239,064 · SL 173,177 = 1,045,064 st / 4,134 trims (`ZIP A2 OK`). |
| 2 A14 motif rows | PARTIAL: 44 → 15 failing | Causes found: (a) `dst2.clean_vis` deleted each drop's shade/grey crescents and the stripe under it grew back over the hole → `keep_unit_slivers` (same motif, same thread family); (b) a drop's grey parts sat under the crests (SL drop knocked out whole) → all drop parts sew with the drop; (c) satin pull comp as an all-round buffer made small drops 20-30 % too big → pull at the stitch ends only; (d) the drop gate's re-centred visible segments left false holes in satin → z-buffer of every stitch (red-then-green: drops that really lost parts stayed red). Wave masses compared per motif (A21 near 1.5 mm): SR 0.34 / FR 0.67 rows now pass. Open: 11 drops of 4-8 mm2 (IoU 0.58-0.79 or one side 1.1-1.65; 9 of them touch a crest), 1 SR curl fragment of 4 mm2, BK stripe mass width 0.79, 2 stripe masses at the keep-out edge. |
| 3 A16 direction | DONE for stripes + drops (mostly) | Stripes 79-84 → **91-95 %** (cells follow the close-up's thread grain where it is clear, `grainfield.py`, else the stripe field). Drops 10-15 → **64-90 %** (one declared angle per drop: close-up grain on the drop, else its long axis; fixed-angle satin). BK 81, FR 64, FL 69 % still under 85. Foam 20-26 % = lockstitch ALTERNATE (chenille ecru primary), stated on G8. |
| 4 seams | OPEN (shown red) | armhole back R: 3 mm of art on 281 mm = one drop at the underarm corner, the back render is bare along that armhole (not a mapping bug) → not graded (< 10 mm). One-sided runs (shoulder L 28 mm, armhole back L 8 mm): foam ends in lobes (`seamedge.py`) instead of a straight cut; founder question: carry the wave over the shoulder onto the back or not. Meet / tone unchanged elsewhere (CF zip 56/48, side L 56/37, sleeve centre R 56/38, underarm R 65/54). G9: 32 parallel + 91 across straight cut lines: 18 on a keep-out edge (allowed), 17 at another seam, 88 inside panels (clusters, not hoop splits: back split is at x = 6 mm) - listed red. |
| should-fix spec pages | DONE | 01 p2 / p6 detail crops centred on the art they name (the fixed offsets showed bare fabric), SL map back inside the margin. |
| should-fix foam swatch | DONE | Rebuilt: w1 had become ecru on 20 Oct, so the old "white" tiles sewed ecru twice. Now A/B ecru (primary), C/D white (alternate): 111,245 st / 744 trims, 1 hooping. |

## Status after fix round 4 (PR #27 review of b448e33; 21 Oct 2026) — numbers from the rebuilt size-M files (zip_check.json, gates_M.json, discont_M.json, continuity_M.json)
| Review item | Status | Evidence |
|---|---|---|
| 1 A14 motif rows | PARTIAL: 15 → 14 failing; **all shape errors the review named first are fixed** | SL wave mass (h 0.38) and BK wave mass (w 0.79) now pass, and so does BK stripe 10. Cause of the SL one: the "keep-out edge" excuse covered mockup art INSIDE the art limit (the reference is already clipped to it). A rigid crest moved 10-15 mm off the sleeve edge. Now only a < 2 mm sliver is excused, and gapfill fills the rest. Cause of the BK one: a 1-2 mm spray tail off the crest was under the 25 mm² A15 size. Fix: gapfill TAILS (>= 6 mm², >= 1 mm wide, within 2.5 mm of the art, reaching >= 2 mm beyond it): 164 tails from mockup pixels. Still open: 13 drops of 4-11 mm² (11 touch a crest; IoU 0.41-0.87, or one side 1.1-1.6) + 1 SR curl fragment of 4 mm². 6 of the SR drops are graded on the x4 render (no close-up), at x 9-44 mm by the sleeve centre. |
| 2 A16 direction | PARTIAL: all visible **BK 86.5 · SR 86.0 · SL 87.3** pass; FR 81.7, FL 79.7 still under 85 | Foam 20-26 → **75-79 %**. The padded foam and its shade / hollow / inner-blue details sew in 4 mm cells along the close-up's 4 mm grain (`flowdir.fm_grain_parts`). The loop texture is now cords along that grain (`foamcord.py`, 2,353 cords) instead of scalloped rings (rings stay where no grain is readable). The headline is now judged per object, like the family rows; the pooled figure (71.5-80.3 %) is printed beside it. Stripes 92-95 %, drops BK 81 / FR 65 / FL 70 / SR 90 / SL 87. The foam angles are read from the graded close-up (self-derived, A24), and G8 says so. |
| 3 seams | PARTIAL: in-panel straight cut lines 123 → **19** (15 across + 4 parallel) | discont.py had flagged every straight stripe edge: a stripe that crosses a seam square has constant-position edges by design (armhole back L A: 26 such "cuts"). `discont.flow_check` now separates them. Coherent tone edges beside the line that run within 20° of it count as a stripe edge (97), not a cut. Tested red-then-green in `test_discont_flow.py`. The 19 remaining are listed red on G9. Meet / tone is unchanged: CF zip 57/48, side L 53/34, shoulder L 21/9 (founder question), sleeve centre R 58/36, armhole front R 59/47; armhole back R 0/0 = 3 mm of art (not graded). |
| 4 should-fix: paths | DONE | G7 / G8 / G9 / G6 point to zip paths (compare/…, compare/seams/…, placement/…); gates_M.json, discont_M.json and continuity_M.json are now in the zip. |
| 4 should-fix: counts | DONE | G8 says per piece + family how many reference motifs were sewn merged with a neighbour and how many DST blobs touch no reference motif (gates.py `ref_merged`, `dst_extra`). |
| 4 should-fix: date | DONE | wavecore.DATE = the build date (never typed). |

## Rev C — ART round (founder 21 Oct 2026, 'Do A' + W3 + W4) — numbers from continuity_M_art.json (art), continuity_M.json (shipped DSTs), gates_M.json
Founder: stop tuning stitches; redraw the ART in a band at every wrap seam (seamredraw.py); shoulders are not wrap seams
(W4); ecru = Isacord 0184 Pearl (W3, confirmed); shell / hardware / rib colour (W2) still open -> other threads PROPOSED.

| Wrap seam | Rev B art meet/tone | Rev C art | Rev C STITCHED | Gate (>= 85 and within 5 of art) |
|---|---|---|---|---|
| CF zip | 63 / 54 | 100 / 100 | 100 / 100 | PASS |
| side L | 54 / 42 | 95 / 95 | 97 / 97 | PASS |
| side R | 67 / 53 | 100 / 100 | 99 / 100 | PASS |
| armhole front L | 95 / 69 | 99 / 99 | 99 / 98 | PASS |
| armhole back L | 95 / 91 | 99 / 100 | 99 / 100 | PASS |
| armhole front R | 59 / 47 | 100 / 86 | 93 / 87 | meet 7 points under the art = ONE 1 mm column of 15 mm (underarm corner) - shown as FAIL on G7, not redefined |
| underarm L | 52 / 40 | 97 / 94 | 96 / 95 | PASS |
| underarm R | 69 / 44 | 100 / 100 | 100 / 100 | PASS |
| sleeve centre L | 54 / 44 | 98 / 100 | 98 / 99 | PASS |
| sleeve centre R | 57 / 36 | 100 / 100 | 99 / 100 | PASS |
| armhole back R | 4 mm of art | — | — | not graded (< 10 mm) |
| shoulder L / R | — | — | — | not a wrap seam (W4) |

| Review round 4 item | Status |
|---|---|
| 1 seams | DONE by redraw (table above); G7 shows art vs stitches per seam + BEFORE / AFTER art per seam; the cut-line detector is unchanged (G9 still lists its count) |
| 2 A14 rows | 19 failing (14 before): 4 inside a redrawn band (named, still counted), 12 'drop merged into a crest', 3 misshapen 4-7 mm² drops/fragment. Every row shown as a crop (reference vs DST): G8 + compare/a14_rows.png |
| 3 SR curl definition | not addressed this round (art round scope) |
| 4 A16 | pooled figure restored as the G8 headline (BK 74.7, FR 69.9, FL 65.1, SR 72.9, SL 72.0 % - all under 85); per object beside it; independent check still OPEN |
| 5 tiny stops | 25 kept, each with its reason printed on G5 (moving it changes what lies on top: the stops touching it sewn between) |
| 6 element-spec style | not addressed |
