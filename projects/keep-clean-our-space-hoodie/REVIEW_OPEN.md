# Open review findings — Keep Clean Our Space, Rev A review (→ Rev B). Fidelity first (A11/A12/A13). No close-ups yet (mockup ~1 px/mm) — trace from a ×4 upscale.
Hard limits passed (112 files, max 7.35, ≤7 colours, M FR 23,604/172 FL 21,459/114 SR 2,619/118 SL 2,274/104 == readback, G5 splits ok, sections ≤339×340, G2 keep-outs pass, PDFs newer than DSTs).
1. HIGH compare_01..05 + compare_front_M are rendered from art regions (compare.py SR.render(allv)), not DSTs — regenerate from DST readback; DST preview shows scribbled CN/JP strokes (crossing rows, noisy fans) — fix what shows.
2. HIGH Glow: hatched serpentine stripes → soft dense teal halo following letter/dot silhouettes (~3 mm offset). JP/EN: no rectangle bands with row gaps. CN: no spiky zigzag ladder past the ring dots.
3. HIGH Puff objects (text, spark bars, hearts, stars, ring dots): domed look — lighter rim ring + darker core, each its own direction. CN ring dots: no radial starburst/centre line. EN/JP big stars: faceted with lighter facets.
4. MED JP text on straight −30.1° baseline → curved (≈−45° at 宇, ≈−20° at に); re-space spark bars and glow along the arc.
5. MED JP red bottom star: solid red with small dark inner star pit (not outline); check top gold star centre.
6. MED CN stroke junctions: 要 top-bar notch, 污 stroke gaps, fans on 球/地 — strokes meet cleanly (ENGINE_NOTES 9 fallback).
7. MED KR oval: keep the non-garble ornaments (i-arrow mark, accent dots); E04 "decorative marks dropped" → restore or list as founder decision.
8. MED E05 star counts don't reconcile (190 detected vs 155 placed + 61 dropped) — add front-only dropped column, nudge don't drop on fronts; state any under hood/neck keep-out.
9. MED Sparkles: thin 45° plus scribbles → concave 4-point stars with soft glow, span distribution matched to mockup (more 5–8 mm ones).
10. LOW EN badge: Nunito stroke ~10–15 % thinner than mockup; line pitch 27 mm looser; star border lighter top facet.
11. LOW Sleeve files identical across sizes (SL +16 at L+) — confirm intended (constant-mm stars) and say so on spec. Add a badge close-up request to inputs/closeup_request.md.
