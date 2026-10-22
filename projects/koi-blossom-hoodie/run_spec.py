"""Build both element specs (01 front, 02 sleeves) from the size-M art + stitch files.  usage: python3 run_spec.py [01] [02]"""
import kbcore
import pickle, json, sys
import espec
D = pickle.load(open("art_M.pkl", "rb")); META = json.load(open("scene_meta.json"))
C = META["counts"]
CUR = json.load(open("dst_current.json"))
def hoops(P): return len(CUR[P]["splits"]["sections"])
def n(P, k): return C[P][k]
REG = json.load(open("trace/closeup_reg.json"))
import front as _F
WELT_DEG = f"{_F.WELT_ANG:.0f}°"          # one value, read from the pattern's welt override (review item 8)
REF = {"01": ("Rev C: EVERY motif traced from the input pixels (no templates, no typed positions, no random numbers). The two FR upper lilies + their "
              f"leaves: from the AI close-up (inputs/closeup_mockup_koi.png, registered on the mockup, drift {REG['projective']['mean_mm']} mm: each lily pasted in its own disc). "
              "FR hem lily, FL hem lily + FL dark flower: traced from the low-res mockup (inputs/front.png, ~1 px/mm, REDRAWN at that resolution: petal fans read on 8-10x zooms, "
              "tones from the pixels). Leaves, stems + floating petals: traced one by one from the mockup pixels. FISH (founder change 19 Oct): tetras traced from "
              "inputs/reference_fish.png (facets from its pixels) at each mockup fish pose measured on the mockup pixels, 0.82 x the mockup length (founder decision). "
              "GENERATED, NOT TRACED: the petal-guide split of each lily silhouette into overlapping petals, stamen lines. No original artwork exists."),
       "02": ("Rev C: NO close-up of the sleeves — traced from the low-res mockup (inputs/front.png, ~1 px/mm, front view only, REDRAWN at that resolution): "
              "the SR cuff lily (its own petal fan), every leaf, stem + petal one by one from the pixels; fish = tetras traced from inputs/reference_fish.png at the "
              "mockup fish poses (0.82 x, founder decision). The SL lower fish swims head-down-left as the mockup shows (Rev B had it reversed). "
              "A sleeve close-up (inputs/closeup_request.md) would sharpen the leaves.")}
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
 "01": dict(id="01", short="front fish", title="FRONT — tetra fish school + blue lilies (split at the zip)",
   sub="Direct embroidery on both cut front panels (F02 wearer's right, F01 wearer's left) · mm, finished size · art files 1:1",
   coords="PLACEMENT (x from CF, + = wearer's left; y down from the CF neck seam)",
   view_note="Front view, size M (0.23:1). Gold bar = zip at CF, dark = welt boxes. Hood not drawn (no embroidery on the hood).",
   p1_notes=[f"FR: {n('FR','fish')} fish, {n('FR','flowers')} lilies, {n('FR','leaves')} leaves, {n('FR','petals')} petals — FL: {n('FL','fish')} fish,",
             f"  {n('FL','flowers')} lilies, {n('FL','leaves')} leaves, {n('FL','petals')} petals (counted on the mockup, A2).",
             "!Zip: art stops 15 each side of CF; nothing crosses the zip,",
             "!  so the two halves need no match marks.",
             "!Hem band: art stops 10 above the band seam (G2).",
             f"!Hoopings on the factory frame (size M): FR {hoops('FR')}, FL {hoops('FL')} (G5/G6)."],
   dm_crops=[("FR", (-225, 105, -170, 135), "Lily: traced petal fan, tone bands, long rows along each petal"),
             ("FR", (-115, 110, -60, 140), "Tetra: traced lavender-blue facets, cyan line, tapered red stripe, eye"),
             ("FL", (100, 380, 155, 410), "Lily cluster at the hem band, leaves")],
   crops=[("FR", (-220, 100, -165, 160), "Lily, size M 1:1"), ("FR", (-120, 100, -70, 160), "Fish pair + petals"),
          ("FL", (60, 210, 115, 270), "Fish school"), ("FL", (95, 380, 150, 440), "Hem-band lily")],
   mock_file="inputs/front.png", mock_crop=(110, 290, 630, 800),
   changes=["Layout counted on the mockup and mapped to the size-M",
            "  Drum Island fronts; motif detail from the close-up.",
            "Zip: art stops 15 each side of CF (mockup lilies touch it);",
            "  FR bottom lily moved ~15 off the zip.",
            "Hem band: mockup petals cross the band seam; the FL + FR",
            "  clusters end 10 above it (whole petals, nothing cut).",
            "Side seam: FR vine leaves kept 15 inside the seam (the",
            "  render draws them under the sleeve).",
            f"Welts at the mockup position + angle ({WELT_DEG}), Drum Island",
            "  size 1.4 × 13; art keeps 6 clear on every size.",
            "Rev C: all lilies, leaves, stems + petals traced",
            "  from the pixels (close-up / mockup), one by one.",
            "FOUNDER: tetras, not koi (reference_fish.png), at",
            "  0.82 x the mockup fish length (decision 19 Oct)."],
   production=PROD, reference=REF["01"]),
 "02": dict(id="02", short="sleeve fish", title="SLEEVES — tetra fish, lilies + petals",
   sub="Direct embroidery on the front half of both cut sleeves (S01 wearer's right, S02 wearer's left) · mm, finished size · art files 1:1",
   coords="PLACEMENT (sleeve pattern coords: x from the sleeve centre line, y down from the underarm line)",
   view_note="Both sleeve pieces, size M (0.19:1). Shaded = back half (no embroidery). Thin line = sleeve centre (shoulder) line.",
   p1_notes=[f"SR: {n('SR','fish')} fish, {n('SR','flowers')} lily, {n('SR','leaves')} leaves, {n('SR','petals')} petals — SL: {n('SL','fish')} fish,",
             f"  {n('SL','petals')} petals (counted on the mockup, A2).",
             "!Front half only: the mockup shows the sleeves from the",
             "!  front; the back half is assumed plain [proposed — confirm].",
             "!Cuff: art stops 10 above the cuff seam; cap + underarm 15.",
             f"!Hoopings on the factory frame (size M): SR {hoops('SR')}, SL {hoops('SL')} (G5/G6)."],
   dm_crops=[("SR", (25, 390, 80, 420), "Cuff lily + leaves"), ("SL", (-100, 270, -45, 300), "Fish"),
             ("SR", (40, 60, 95, 90), "Top fish")],
   crops=[("SR", (25, 390, 80, 450), "Cuff lily, 1:1"), ("SL", (-105, 250, -55, 310), "Fish"),
          ("SR", (50, 330, 105, 390), "Fish + petals"), ("SL", (-140, 340, -85, 400), "Fish near the cuff")],
   mock_file="inputs/front.png", mock_crop=(0, 450, 180, 930), mock_w=28,
   changes=["Placed from the mockup's front view: each point mapped",
            "  onto the sleeve pattern (outer fold = centre line,",
            "  inner edge = front underarm seam, cylinder projection).",
            "Fish (tetras, founder reference) + petals sized like",
            "  the fronts (one motif scale).",
            "Cuff: the mockup lily runs over the cuff seam; the",
            "  cluster ends 10 above it.",
            "Back half of the sleeves: plain [proposed — confirm]."],
   production=PROD, reference=REF["02"])}

# factory copy (Rev D, `run_spec.py --factory`, run by rfq.py): neutral reference + change notes, no build provenance
REF_FAC = {"01": "Artwork: every motif traced from the design mockup and its close-up. Fish: tetras at 0.82 x the mockup fish length (confirmed). "
                 "Stitch files are for SAMPLING: production-intent drafts, the fish fill is under revision — your digitizer checks density + pull on the shell before the strike-off.",
           "02": "Artwork: traced from the design mockup (front view; no sleeve close-up). Fish: tetras at the same scale as the fronts. "
                 "Stitch files are for SAMPLING: production-intent drafts, the fish fill is under revision — your digitizer checks density + pull on the shell before the strike-off."}
CHG_FAC = {"01": ["Layout from the design mockup, mapped to the size-M",
                  "  front pattern pieces.",
                  "Zip: art stops 15 each side of CF (mockup lilies touch it);",
                  "  FR bottom lily moved ~15 off the zip  [proposed — confirm].",
                  "Hem band: mockup petals cross the band seam; the FL + FR",
                  "  clusters end 10 above it  [proposed — confirm].",
                  "Side seam: FR vine leaves kept 15 inside the seam.",
                  f"Welts at the mockup position + angle ({WELT_DEG}),",
                  "  size 1.4 × 13; art keeps 6 clear on every size.",
                  "Fish: sew the tetras in the stitch files (they replace",
                  "  the mockup's fish), at 0.82 x the mockup fish length."],
           "02": [c.replace("Fish (tetras, founder reference) + petals sized like", "Fish: the files' tetras replace the mockup's fish;")
                   .replace("  the fronts (one motif scale).", "  sized like the fronts (one motif scale).") for c in CFG["02"]["changes"]]}

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--factory"]
    if "--factory" in sys.argv:
        kbcore.MODE = "factory"
        for el in CFG: CFG[el].update(reference=REF_FAC[el], changes=CHG_FAC[el])
    for el in (args or ["01", "02"]):
        print(espec.build(CFG[el], D))
