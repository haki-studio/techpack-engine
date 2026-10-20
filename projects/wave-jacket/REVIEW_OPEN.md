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
