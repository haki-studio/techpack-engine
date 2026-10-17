"""Build both element specs (01 front, 02 sleeves) from the size-M art + stitch files.  usage: python3 run_spec.py [01] [02]"""
import kbcore
import pickle, json, sys
import espec
D = pickle.load(open("art_M.pkl", "rb")); META = json.load(open("scene_meta.json"))
C = META["counts"]
CUR = json.load(open("dst_current.json"))
def hoops(P): return len(CUR[P]["splits"]["sections"])
def n(P, k): return C[P][k]
REF = ("Art redrawn, not traced: layout counted from the low-res mockup (inputs/front.png, ~1 px per mm); motif look from the AI close-up "
       "of the upper right front (inputs/closeup_mockup_koi.png). No original artwork exists — send it if it does.")
PROD = ["Embroider the cut panels flat, BEFORE zip, welts,",
        "  side seams, sleeve seams and hem band / cuffs.",
        "12 threads, 40wt polyester (G3); stop order p4.",
        "Washed navy duck: 75/11 sharp, 2.5 oz navy/black",
        "  cutaway, no topping. Pre-wash the shell first.",
        "Mark CF / sleeve centre, keep-out lines + needle",
        "  start (G6, DXF layer 13) before hooping.",
        "Frame (factory.json): split files S1 + S2,",
        "  registration crosses open stop 1 (G6).",
        "Sew-out on production canvas before bulk."]
CFG = {
 "01": dict(id="01", short="front koi", title="FRONT — koi school + blue lilies (split at the zip)",
   sub="Direct embroidery on both cut front panels (F02 wearer's right, F01 wearer's left) · mm, finished size · art files 1:1",
   coords="PLACEMENT (x from CF, + = wearer's left; y down from the CF neck seam)",
   view_note="Front view, size M (0.23:1). Gold bar = zip at CF, dark = welt boxes. Hood not drawn (no embroidery on the hood).",
   p1_notes=[f"FR: {n('FR','koi')} koi, {n('FR','flowers')} lilies, {n('FR','leaves')} leaves, {n('FR','petals')} petals — FL: {n('FL','koi')} koi,",
             f"  {n('FL','flowers')} lilies, {n('FL','leaves')} leaves, {n('FL','petals')} petals (counted on the mockup, A2).",
             "!Zip: art stops 15 each side of CF; nothing crosses the zip,",
             "!  so the two halves need no match marks.",
             "!Hem band: art stops 10 above the band seam (G2).",
             f"!Hoopings on the factory frame (size M): FR {hoops('FR')}, FL {hoops('FL')} (G5/G6)."],
   dm_crops=[("FR", (-225, 105, -170, 135), "Lily: two-tone petals, zig-zag tone steps, stamens"),
             ("FR", (-115, 110, -60, 140), "Koi: body satin, red patches, fins + tail rays"),
             ("FL", (100, 380, 155, 410), "Lily cluster at the hem band, leaves")],
   crops=[("FR", (-220, 100, -165, 160), "Lily, size M 1:1"), ("FR", (-120, 100, -70, 160), "Koi pair + petals"),
          ("FL", (60, 210, 115, 270), "Koi school"), ("FL", (95, 380, 150, 440), "Hem-band lily")],
   mock_file="inputs/front.png", mock_crop=(110, 290, 630, 800),
   changes=["Layout counted on the mockup and mapped to the size-M",
            "  Drum Island fronts; motif detail from the close-up.",
            "Zip: art stops 15 each side of CF (mockup lilies touch it);",
            "  FR bottom lily moved ~15 off the zip.",
            "Hem band: mockup petals cross the band seam; the FL + FR",
            "  clusters end 10 above it (whole petals, nothing cut).",
            "Side seam: FR vine leaves kept 15 inside the seam (the",
            "  render draws them under the sleeve).",
            "Welts at the mockup position + angle (60°), Drum Island",
            "  size 1.4 × 13; art keeps 6 clear on every size.",
            "Long-and-short shading = 2–4 tone bands per petal / leaf."],
   production=PROD, reference=REF),
 "02": dict(id="02", short="sleeve koi", title="SLEEVES — koi, lilies + petals",
   sub="Direct embroidery on the front half of both cut sleeves (S01 wearer's right, S02 wearer's left) · mm, finished size · art files 1:1",
   coords="PLACEMENT (sleeve pattern coords: x from the sleeve centre line, y down from the underarm line)",
   view_note="Both sleeve pieces, size M (0.19:1). Shaded = back half (no embroidery). Thin line = sleeve centre (shoulder) line.",
   p1_notes=[f"SR: {n('SR','koi')} koi, {n('SR','flowers')} lily, {n('SR','leaves')} leaves, {n('SR','petals')} petals — SL: {n('SL','koi')} koi,",
             f"  {n('SL','petals')} petals (counted on the mockup, A2).",
             "!Front half only: the mockup shows the sleeves from the",
             "!  front; the back half is assumed plain [proposed — confirm].",
             "!Cuff: art stops 10 above the cuff seam; cap + underarm 15.",
             f"!Hoopings on the factory frame (size M): SR {hoops('SR')}, SL {hoops('SL')} (G5/G6)."],
   dm_crops=[("SR", (25, 390, 80, 420), "Cuff lily + leaves"), ("SL", (-100, 270, -45, 300), "Long koi"),
             ("SR", (40, 60, 95, 90), "Top koi")],
   crops=[("SR", (25, 390, 80, 450), "Cuff lily, 1:1"), ("SL", (-105, 250, -55, 310), "Long koi"),
          ("SR", (50, 330, 105, 390), "Koi + petals"), ("SL", (-140, 340, -85, 400), "Koi near the cuff")],
   mock_file="inputs/front.png", mock_crop=(0, 450, 180, 930), mock_w=28,
   changes=["Placed from the mockup's front view: each point mapped",
            "  onto the sleeve pattern (outer fold = centre line,",
            "  inner edge = front underarm seam, cylinder projection).",
            "Koi + petals sized like the fronts (one motif scale).",
            "Cuff: the mockup lily runs over the cuff seam; the",
            "  cluster ends 10 above it.",
            "Back half of the sleeves: plain [proposed — confirm]."],
   production=PROD, reference=REF)}

if __name__ == "__main__":
    for el in (sys.argv[1:] or ["01", "02"]):
        print(espec.build(CFG[el], D))
