"""Build the three element specs (01 back, 02 fronts, 03 sleeves) from the size-M art + stitch files.
usage: python3 run_spec.py [01 02 03]"""
import cfcore
import sys, pickle
import espec

REF = ("Rev B: mockup (placement + scale) + founder close-ups inputs/closeups/ (front, back left, back right, sleeves; registered by thin-plate spline on matched "
       "features and traced, LESSONS A12/A13) + reference.png (structure where an AI close-up is garbled). Redrawn from the LOW-RES MOCKUP only (no close-up): "
       "SL gate tower, village house rows (objects placed on the traced building tones).")
PROD_COMMON = ["Embroider the cut panel flat, BEFORE any seam.", "Navy 12 oz duck: 75/11 sharp, 2.5 oz cutaway,",
               "  no topping. Pre-wash the shell first.", "≤ 12 threads per file (factory limit), 40wt.",
               "Frame (factory.json): split files + registration", "  crosses sewn in stop 1's thread (G5 / G6).",
               "Sew-out on production canvas before bulk;", "  measure the design size vs spec (F1)."]
CFG = {
 "01": dict(id="01", short="back scene", title="BACK SCENE — waterfall mountains, cherry trees, village",
            sub="Direct embroidery on the cut back panel (B01, one piece across CB) · mm, finished size · art files 1:1",
            coords="x from CB, + = wearer's right; y down from the CB neck seam",
            p1_notes=["!Armholes are wrap seams: art stops 3 mm short of the", "!  seam; the sleeve art continues on S01 / S02 (03).",
                      "Collar lying flat covers 70 below the back neck: art", "  starts below it (+6). Sides 15, hem-rib seam 10.",
                      "!4 hoopings on the factory frame (2 × 2 split files, G6)."],
            dm_crops=[("BK", (-200, 300, -150, 340), "falls (vertical tatami) + cliff"), ("BK", (-215, 470, -165, 510), "florets on the blossom ground"),
                      ("BK", (-40, 140, 10, 180), "cloud tones + petals")],
            crops=[("BK", (-205, 300, -155, 350), "waterfall + cliff"), ("BK", (-225, 460, -175, 510), "cherry florets"),
                   ("BK", (-60, 480, -10, 530), "village"), ("BK", (-40, 130, 10, 180), "clouds + petals")],
            mock_crop=(768 + 115, 150, 768 + 600, 600),
            changes=["Layout + every tone area traced from the mockup", "  (40 tone clusters → 18 tones, 12 threads in this file).",
                     "Bare navy shell where the mockup shows fabric", "  (upper back between the clouds).",
                     "Blossom masses: tone ground + ~1 floret / 22 mm²", "  (5-petal satin, Ø 3.6–5.6) on top, as the close-up.",
                     "Falling petals redrawn as notched petal satins.", "Mockup CB fold line is not art: filled across.",
                     "Back left + right close-ups registered (TPS) + traced:", "  rope-cord falls (2nd fall kept), strata, clumps, lobes.",
                     "Floret centres cream, petal bases deep rose (close-ups).",
                     "Thread merges for 12 colours: moss light → leaf", "  green, sky light → sky, vermilion → blossom deep,",
                     "  bark tan → bark dark, gold → cloud cream (p4)."],
            production=PROD_COMMON, reference=REF),
 "02": dict(id="02", short="front scene", title="FRONT SCENE — castle, falls, pagoda, bridge (split at zip)",
            sub="Direct embroidery on both cut front panels, before zip + welts · FR (F02) + FL (F01) · mm, finished size · art files 1:1",
            coords="x from CF, + = wearer's left; y down from the CF neck seam",
            p1_notes=["!Zip: art stops 15 each side of CF; the bridge, sky", "!  and clouds continue across it (both halves traced",
                      "!  from the same mockup columns).", "Welt boxes: art 6 clear on every size (T13).",
                      "Composition = reference (founder decision 2026-10-19):", "  closed tree arch, castle on the falls rock, karamon gate.",
                      "!2 hoopings per piece (split files S1 / S2, G6)."],
            dm_crops=[("FL", (60, 180, 110, 220), "castle roof tiles + gold trims"), ("FR", (-180, 235, -130, 275), "pagoda"),
                      ("FL", (130, 400, 180, 440), "bridge + florets")],
            crops=[("FL", (70, 180, 120, 230), "castle top tiers"), ("FR", (-180, 235, -130, 285), "pagoda"),
                   ("FL", (40, 390, 90, 440), "falls beside the castle rock"), ("FR", (-150, 60, -100, 110), "clouds + petals")],
            mock_crop=(175, 150, 655, 600),
            changes=["Traced from the front close-up (registered TPS) on the", "  mockup layout; composition as reference.png (founder).",
                     "Castle as objects: 3 tiers, tile-rib roofs, gold eaves +", "  white studs, window bands, gables, shachi, lantern band,",
                     "  red balustrade; karamon gate at the rock foot.", "Pagoda: 3 tiers, upturned eaves, red bodies, gold rail,", "  ringed gold finial. Falls: rope cords + mist foot.",
                     "Village: house rows (redrawn, low-res mockup).", "Welts at the mockup position (T3); art clears 6.",
                     "Merges (12 colours): FR moss light → green, bark tan →", "  bark dark, sky light → sky, pink → pale, cream → white;",
                     "  FL pinks → pink, moss light → green, cream → white,", "  sky light → sky (p4)."],
            production=PROD_COMMON, reference=REF),
 "03": dict(id="03", short="sleeve scenes", title="SLEEVE SCENES — mountains, blossom, clouds (S01 + S02)",
            sub="Direct embroidery on both cut sleeves (S01 right, S02 left), flat, before the underarm seam · mm, finished size · art files 1:1",
            coords="x across the sleeve from the centre line, y down from the underarm line",
            p1_notes=["Centre fold (top of the arm): the mockup's flat-lay edge is", "  filled with the tones beside it where art runs both sides.", "!Cap = wrap seam: art stops 3 mm short; the body art", "!  continues on the back / fronts (01 / 02).",
                      "Underarm seams 15, cuff seam 10.", "Front half traced from the front view, back half from the",
                      "  back view of the mockup; the render's sleeves are ~1.7×", "  narrower than the pattern, so shapes are stretched across",
                      "  (motif sizes stay library mm).", "!4 hoopings per sleeve (2 × 2 split files, G6)."],
            dm_crops=[("SR", (-150, 270, -100, 310), "florets + foliage"), ("SL", (40, 120, 90, 160), "cloud tones"),
                      ("SL", (-175, 265, -125, 305), "gate tower")],
            crops=[("SR", (-150, 270, -100, 320), "cherry florets"), ("SR", (0, 150, 50, 200), "cliff foliage"),
                   ("SL", (-175, 260, -125, 310), "gate tower"), ("SL", (50, 110, 100, 160), "clouds + petals")],
            mock_crop=(0, 150, 220, 690),
            changes=["FULL WRAP (Rev B): front + back halves traced from the", "  founder's sleeve close-up (4 views), placed on the mockup.",
                     "SL back: cliff waterfall (rope cords) as the close-up.", "Gate tower (SL front) redrawn as an object from the",
                     "  low-res mockup (not in the sleeve close-up).",
                     "Florets + petals as on the back (01).", "Merges (12 colours): sky light → sky, moss light →",
                     "  green, bark tan → bark dark, gold → cream; SR", "  vermilion → blossom deep, SL pink → pale (p4)."],
            production=PROD_COMMON, reference=REF),
}

if __name__ == "__main__":
    art = pickle.load(open("art_M.pkl", "rb"))
    for e in sys.argv[1:] or ["01", "02", "03"]:
        r = espec.build(CFG[e], art); print(e, r["spec"], {k: round(v, 1) for k, v in r["WC"].items() if v >= 1.0}, flush=True)
