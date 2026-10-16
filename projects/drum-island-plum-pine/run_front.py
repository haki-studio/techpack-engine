import pickle, sys, json
from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely import affinity
import front as F
import espec

VIS = pickle.load(open("front_vis.pkl", "rb"))

def clearances(p):
    u = unary_union([r["geom"] for r in VIS[p]]); b = u.bounds
    side = "R" if b[2] < 0 else "L"
    mir = (lambda g: g) if side == "R" else (lambda g: affinity.scale(g, -1, 1, origin=(0, 0)))
    arm = mir(F.ARM_R); sd = mir(F.SIDE_R); col = F.COLLAR_R if side == "R" else F.COLLAR_L; wl = F.WELT_R if side == "R" else F.WELT_L
    cf = LineString([(0, -50), (0, 900)]); hem = LineString([(-400, F.HEM), (400, F.HEM)])
    return [("Art box " + p, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}"),
            ("  x range", f"{b[0]:+.0f} to {b[2]:+.0f}"), ("  y range", f"{b[1]:.0f} to {b[3]:.0f}"),
            ("  → CF (zip centre)", f"{u.distance(cf):.0f}"), ("  → armhole / shoulder seam", f"{u.distance(arm):.0f}"),
            ("  → side seam", f"{u.distance(sd):.0f}"), ("  → collar (lying flat)", f"{u.distance(col):.0f}"),
            ("  → welt pocket", f"{u.distance(wl):.0f}"), ("  → hem seam", f"{u.distance(hem):.0f}")]

COMMON_PROD = ["Embroider the cut front panels flat, BEFORE",
               "  zip, welt pockets and side seams.",
               "Same 16-thread palette + parameters as 01.",
               "Canvas: 75/11 sharp, 2.5 oz cutaway, no",
               "  topping. Polyester thread; wash test if",
               "  garment-washed.",
               "Welt pockets are cut after embroidery: mark",
               "  welt position on the panel before hooping.",
               "Sew-out on production canvas before bulk."]

CFG = {
 "02": dict(id="02", slug="chest-branch", short="chest branch", title="CHEST PLUM BRANCH (split at zip)",
   sub="Direct embroidery on both cut front panels, before zip + welts · two pieces registered across the CF zip · mm, finished size · art files 1:1",
   pieces=["02R", "02L"], placement=lambda B: clearances("02R") + clearances("02L"),
   marks=None,
   p1_notes=["!Zip: art stops 15 each side of CF (teeth + tape + topstitch).",
             "The main limb is cut on the same y-band each side so it reads",
             "as one branch passing behind the zip. Check marks below.",
             "Collar keep-out: art stays 6 clear of the collar lying flat."],
   dm_crops=[((-230, 185, -185, 210), "Blossom L + leaves: radial satin, feather leaves"),
             ((-125, 190, -80, 215), "Main limb: tatami along limb, padded snow across"),
             ((15, 225, 60, 250), "Limb after the zip (02L): same angles continue")],
   crops=[((-229, 185, -179, 235), "Blossom L Ø 35 + leaf cluster"), ((-128, 182, -78, 232), "Main limb snow, gnarled bark"),
          ((20, 219, 70, 269), "02L at the zip: limb restarts")],
   mock_crop=(100, 180, 760, 640),
   changes=["Composition traced from the mockup: branch from the right",
            "  shoulder across the zip to the left chest; blossoms + buds",
            "  at the mockup positions, plus spray twigs + bud clusters.",
            "Zip: the mockup runs the branch over the zip — impossible.",
            "  Split into 02R + 02L, each stopping 15 from CF.",
            "Shoulder: mockup tip touches the armhole seam. Starts 15",
            "  inside it (art is cut cleanly at the limb end).",
            "Collar: twig tips under the collar point pulled 6 clear.",
            "Snow + bark + petals use the 01 system (3 tones, padded snow)."],
   production=COMMON_PROD + ["Hoop each front panel once; the two pieces", "  must be registered to the CF line ±1."]),
 "03": dict(id="03", slug="chest-pine", short="chest pine", title="CHEST WHITE PINE + MIST",
   sub="Direct embroidery on the cut wearer's-left front panel · mm, finished size · art files 1:1",
   pieces=["03"], placement=lambda B: clearances("03"),
   p1_notes=["Sits below the 02L branch tips; keep ≥ 10 between", "the two (measured: see clearances).",
             "!Welt pocket below: art stays 6 clear of the welt box."],
   dm_crops=[((160, 318, 205, 343), "White pine: turning tatami from hub, gold inner, padded snow"),
             ((120, 345, 165, 370), "Branch + mist: tatami along branch, bean mist")],
   crops=[((165, 314, 215, 364), "Centre fan + snow cap"), ((120, 330, 170, 380), "Side fan + branch + mist")],
   mock_crop=(540, 460, 760, 640),
   changes=["Three white pine fans on a snowy branch with mist, as in",
            "  the mockup. Fans seated directly on the branch (mockup",
            "  stems are hidden under the fans).",
            "Gold inner zone blended into the cream fan as on 01.",
            "Mist moved up 8 so it clears the welt pocket keep-out."],
   production=COMMON_PROD),
 "04": dict(id="04", slug="lower-bamboo", short="lower bamboo", title="LOWER-FRONT BAMBOO + MIST",
   sub="Direct embroidery on the cut wearer's-right front panel, below the welt pocket · mm, finished size · art files 1:1",
   pieces=["04"], placement=lambda B: clearances("04"),
   p1_notes=["!Mockup runs the lower cluster into the rib knit:", "lifted to stop 10 above the hem seam.",
             "Upper cluster clears the welt pocket by ≥ 6."],
   dm_crops=[((-210, 480, -165, 505), "Upper cluster: feather satin ±55°, snow caps vertical"),
             ((-250, 525, -205, 550), "Lower cluster + mist bands")],
   crops=[((-208, 470, -158, 520), "Bamboo hub + snow"), ((-250, 520, -200, 570), "Lower cluster over mist")],
   mock_crop=(100, 580, 460, 920),
   changes=["Two drooping bamboo clusters with snow caps over mist, as",
            "  in the mockup; blades drawn with blunt satin tips",
            "  (needle-point tips won't stitch).",
            "Lower cluster lifted ~25 so it stops 10 above the hem",
            "  seam (rib knit can't be embroidered).",
            "Mist bands kept long as in the mockup; they pass under",
            "  the welt corner but stay 6 clear of the welt box."],
   production=COMMON_PROD),
}
CFG["02"]["marks"] = F.zip_marks()

if __name__ == "__main__":
    res = {}
    for k in sys.argv[1:]:
        r = espec.build(CFG[k], F, VIS)
        res[k] = {p: round(v) for p, v in r["TOT"].items()}
        print(k, res[k], {c: round(v, 1) for c, v in r["WC"].items() if v >= 1.0}, flush=True)
