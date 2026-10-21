# HANDOFF - fix round 2 for PR #27 (session-size handoff, 20 Oct 2026 ~22:30). READ THIS FIRST.
Reviewer verdict on be032f8: `gh pr view 27 --comments` (6 fixable: A14 rows, A15 gaps, A16 stripes, seams, G1 streaks,
legibility; founder a + b). Founder answers since (coordinator, 20 Oct evening; in inputs/brief.md): (b) ECRU foam +
CHENILLE first (lockstitch padded = alternate; chenille stays a path plan + format question, B33); (a) close-ups in
inputs/closeups/ (sleeves = 2x2 composite, navy blotches = artefacts).

## Done in this round (committed, art + DSTs + QA rebuilt on it)
- `register_closeups.py` (system python3, OpenCV): every close-up / sleeve quadrant registers onto the mockup view as pure
  scale + shift (92-98 % inliers) -> cu_regs.json + out/trace/cureg_*.png. They are super-res crops of the mockup.
- `wavetrace.closeups_labels`: classes from the close-up pixels inside each footprint (art area within 1-5 % of the render's);
  trace_back/front.pkl re-traced; waveart M -> tonematch M -> `gapfill.py M` (new) -> build_size M x5 -> qa_chain.
- `gapfill.py` (A15): every bare gap except keep-out edges filled from the mockup / close-up tones, merged into touching
  stripes / crests, foam fills get curl rows + loops. Unexplained gaps 18 -> **0** on every piece (DST).
- `gates.py` (A14): visible top layer of the DST (hidden travel no longer merges crests), near_mm, drops = cream+shade+grey
  threads compared with ITS OWN motif's stitches (unit attribution) with pull-in modelled; curls now **all pass** on all 5.
  A16: grain from the close-ups (12 ppm, weight mask; render-only tiles masked), per-object groups. ENGINE_NOTES 18-21.
- Ecru: wavecore w1 = #D3CAC1 "Foam ecru" (Isacord 0184 Pearl, the G3 candidate); FOAM_WHITE_ALT = render white.
  Isacord 0151 is "Cloud" #BAAA9E and Polyneon 1801 "Barely Blue" (ENGINE_NOTES 13) -> ask, do not use.
- CORD_TWIST 15 -> 8 deg. views.py: streak fans dropped from the sleeve preview (check G1). pack.py: G9 cut-line cell RED +
  "OPEN" when any remain; F1 section 6 = chenille in ecru first, lockstitch alternate.
- New numbers (size M, DST read-back): BK 302,534 st / 1,212 trims (2 hoopings), FR 120,133 / 533, FL 188,350 / 820,
  SR 224,112 / 756 (2), SL 164,763 / 689 (2); max 7.45; 9 threads.

## Still open (gates_M.json, continuity_M.json, discont_M.json from the shipped files)
1. A14: 53 failing rows (19 "MISSING"), almost all spray drops 4-12 mm2 + 3 stripe masses (BK 153,371; FR -102,412;
   SR 54,140 IoU 0.34). Next: trace each drop's silhouette at close-up resolution (label map UP=4 caps it at ~2.8 px/mm;
   classify the close-up natively inside each drop's bbox) and check SR stripe mass 54,140 (art vs ref picture).
2. A16 stripes 58-76 % (target 85): look at fail_dev tiles on the compare heat-maps vs the close-up grain; foam 18-25 %
   (foam is chenille-first now: say on G8 the lockstitch foam grain is the ALTERNATE and judged on the close-ups).
3. Seams regressed after the re-trace: gapfill runs AFTER tonematch, so fills near seams carry mockup tones, not the
   leader's. Reorder: `rm art_M_pretone.pkl; waveart M; gapfill M; tonematch M` (tonematch backs up its input as pretone),
   then rebuild. G7 now: CF zip 54/46, shoulder L 20/23, armhole back R 0/0 (4 mm of art), sleeve centre R 58/44.
   discont: 86 of 718 edges jump (12 %), many straight cut lines - list them on G9 in red (code started in treatment_page).
4. Pages (review 6): G2-G9 at readable size (>= 2.3 mm text, split tables across pages), G9 thumbnails bigger, G2 art-box
   table not clipped; G8 text: close-ups, visible layer, unit attribution, gap fill; G3: ecru primary + white alternate.
5. Docs: compare.py M, views/covers, build_all, shrink, finish (zip), render EVERY page + look; copy PDF + zip to
   C:/Users/devin/Desktop/wave-RevB; REVIEW_OPEN status table; PR comment; `scripts/dispatch.sh review wave-jacket 27`.
Tasks: `./py.sh` = engine env (no OpenCV); heavy jobs via ../../scripts/heavy.sh. Gate quick-check per piece without the
direction pass: `./py.sh gates.py --nodir` (add `--art` for the art pkl).

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
