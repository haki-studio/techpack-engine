# Open review findings — Koi Blossom (tetra fish), Rev B review (→ Rev C). Fidelity first (A11–A15).
Hard limits passed (75 DST/PES, max 7.47, ≤11 colours, all 7×4 doc numbers == readback, M keep-outs CF 15.7 / armhole 15.2 / hem 10.2 / welt 12.8+ / cuff 19.0, zip == docs, welt override drawn on T2/T4/T7). Gates reproduce, but they are partly circular (item 1).
1. HIGH The A14/A15 gates are circular:
   - Fish reference = the art's own fish regions.
   - FR lily reference = rasterised art (PROTECT) ORed into the mask.
   - Flora silhouettes are filled from the same traced mask they are compared to.
   - Stems are removed from both sides; the DST mask is closed + hole-filled.
   Rebuild every reference mask from INPUT PIXELS ONLY (mockup / close-up / reference_fish.png), never from art or scene data. Report texture primitives too (A13), not only silhouette. The stricter run shows a 40 mm² gap at FR (-190, 189).
2. HIGH The hem and cuff lilies are template copies, not traced:
   - FR hem = cu_lily1 mirrored +15°
   - FL hem big lily = cu_lily0 mirrored
   - FL dark flower = cu_lily1 darker, -20°
   - SR cuff = cu_lily1 mirrored +10°
   Trace each from the mockup (its own petal fan; the dark flower is a distinct shape). Until then, list all four on G1 as "generated, not traced".
3. HIGH Tone and structure:
   - FR big lily petals stitch pale ice/white; they should be mid-blue with ice highlights only.
   - Petal edges are radial streak fans; they should be long stitch rows.
   - Lily 2 fragments.
   - FR hem leaves have random white interior blobs; they should be solid mid-blue.
   - The FL hem lily, dark flower and SR cuff cluster read near-white; the mockup reads blue.
   - The dark-flower stamens/anthers are weak.
4. HIGH Leaves and vines are hand-typed (≈80 CLUSTERS tuples + rng), then clipped to the mask. Trace them leaf by leaf (position, axis, length, tone). The FL right vine and the dark leaves by the welt are thinner than the mockup.
5. MED Fish:
   - Size is a typed 0.82 × the mockup length (FL big fish ≈ 80 %). Use the full mockup length unless the founder says otherwise.
   - The body is flat silver/white; the reference is lavender-blue faceted. Make the red stripe less blocky.
   - Measure the proportions from reference_fish.png instead of typed polygons.
6. MED Hem lilies stop 10 mm above the band and 15 mm off the zip (asked on G4). ~195 mm² of mockup blue in the band zone is unstitched. Keep as a founder question.
7. MED The stitch count fell vs Rev A (FR 43,470 → 40,325; FL 27,513 → 25,897). Explain it (tetras vs koi) and confirm no flora was thinned.
8. LOW Welt angle text: 61° vs 60°. Make it one value from the file.
9. LOW Fish compare: add a reference-outline vs DST overlay at equal scale.
10. LOW Delete the dead koi code in kb_motifs.py (KO-* groups).
11. LOW L/XL share the M FR art. This is a founder question (grading).
