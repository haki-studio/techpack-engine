"""Build the two element specs (01 beast head, 02 sleeve streaks) from the size-M art + stitch files."""
import rbcore
import pickle, json
import front as F, espec, emb_place as EP
D = pickle.load(open("art_M.pkl", "rb")); VIS = {P: D[P] for P in rbcore.PIECES}
CUR = json.load(open("dst_current.json")); REG = json.load(open("inputs/closeup_reg.json")); WELT = json.load(open("welt.json"))

def clear_rows(P):
    c = EP.clearances("M")[P]; b = EP.outline("M", P).bounds; mn = F.piece_min(P)
    return [(f"Art box {P} ({rbcore.PIECE_NAME[P]})", f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}"),
            ("  x range / y range", f"{b[0]:+.0f} to {b[2]:+.0f} / {b[1]:.0f} to {b[3]:.0f}")] + \
           [(f"  → {k}", f"{v:.1f}  (min {mn[k]:.0f})") for k, v in c.items()]

REF = ["REFERENCE PER PART (no original artwork files; the art was redrawn from these sources):",
       f"- Beast head (FL: jaws, teeth, eye, snout, throat): TRACED from the close-up detail panel (right half of inputs/flat.png), registered onto",
       f"  the mockup by a projective fit ({REG['inliers']} SIFT matches, residual {REG['resid_mm_median']:.1f} mm median / {REG['resid_mm_p90']:.1f} mm p90): tones AND stitch direction (flow field).",
       "- Mane, flame strands, lightning branches (FR) + slash streaks (both fronts): redrawn from the LOW-RES MOCKUP only (~1.15 mm/px);",
       "  no close-up of these yet (requested: inputs/closeup_request.md [front_right]). Stroke widths + directions at that resolution are approximate."]

WHY01 = ["Red hair strokes + streaks first, crimson shade strokes + cord under-edges next: their travel hides under the black sewn after them (B2/B14).",
         "Black ground strokes (mouth, throat, between the strands), then the cream cords + teeth so they sit raised on top, then the white",
         "tooth edges last. Same thread may repeat as a stop where merging would cross art. Every stroke is its own object (Rev B)."]
WHY02 = ["Red streaks first, crimson streaks next, cream branch tip last on top (SR only). SL: red + crimson only (2 stops).",
         "No black ground on the sleeves. Each streak is an island on bare fabric, so most trims here are unavoidable jumps between streaks."]
NTH = {P: CUR[P]["threads"] for P in rbcore.PIECES}
CFG01 = dict(id="01", why=WHY01, short="beast head", title="BEAST HEAD — fronts, split at the zip",
   sub="Direct embroidery on both cut front panels, before zip + welts · two pieces registered across the CF zip · mm, finished size · art files 1:1",
   coords="PLACEMENT (x from CF, + = wearer's left; y down from CF neck seam)",
   view_caption="Front view, size M (0.23:1). Orange = keep-out boundary (art area), gold bar = zip, dark boxes = welt pockets [PROPOSED position].",
   placement=lambda: clear_rows("FR") + clear_rows("FL"),
   p1_notes=["!Zip: art stops 15 each side of CF; both halves are graded",
             "about the CF neck point, so the jaw, outline and strands meet",
             "the zip keep-out at the same height on FR and FL (±1).",
             "!Welts moved 45 out / 27.5 down from the render: the render",
             "draws the FL welt under the lower jaw. [PROPOSED — confirm]",
             "!2 hoopings per piece on the factory frame (split files, G5/G6)."],
   dm_crops=[((150, 212, 195, 234), "Teeth: satin along each tooth + white edge; black strokes"),
             ((40, 152, 85, 174), "Hair: red + crimson strokes, satin along the flow"),
             ((-215, 40, -170, 62), "Lightning: cord 2.5 root → 1.0 tip, every fork")],
   crops=[("FL", (160, 205, 215, 260), "Fangs + mouth"), ("FL", (215, 190, 270, 245), "Snout + nose"),
          ("FR", (-190, 120, -135, 175), "Mane strokes")],
   mock_src="inputs/front.png", mock_crop=(130, 280, 640, 720),
   reference=REF,
   changes=["Body: the render's body is narrower + longer than the Drum Island",
            "  block; art mapped at one scale (1.15 mm/px, no stretch) from CF +",
            "  the neck seam, so the nose sits 22 inside the side seam as drawn.",
            "Zip: art split into FR + FL 15 each side of CF (zip + topstitch).",
            "Keep-outs cut the art straight where it ran over a seam: armhole /",
            "  side 15, shoulder 15, hood/neck seam 10, hem band 10, welt 6.",
            "!Streaks + branch tips that cross the armhole in the render end",
            "!  15 short on the front (no wrap onto the sleeve) [PROPOSED].",
            "!Welt pockets moved 45 out, 27.5 down (render: FL welt under the",
            f"!  jaw, {WELT['mock_head_cut_mm2']:.0f} mm² of head lost; now {WELT['head_cut_mm2']:.0f} mm²) [PROPOSED].",
            "Rev B: mouth + throat black is directional black strokes with red",
            "  + crimson strokes over it (close-up), not a flat fill; hair = 1.5–3",
            "  wide strokes along the traced flow; cords 2.5–3 with a crimson",
            "  under-edge; teeth one object each; streaks tapered columns.",
            "Specks < 8 mm² with no neighbour (render highlights) dropped."],
   production=["Embroider the cut front panels flat, BEFORE",
               "  zip, welt pockets, hood and side seams.",
               f"{max(NTH['FR'], NTH['FL'])} threads, 40wt polyester (G3); stop order p4.",
               "Washed black 12 oz duck: 75/11 sharp, 2.5 oz",
               "  black cutaway, no topping. Pre-wash shell.",
               "Mark CF + welt box (drills) on each panel.",
               "Frame (factory.json): split files S1 + S2,",
               "  registration crosses open stop 1 (G6).",
               f"Dense head (FL {CUR['FL']['stitches']:,} st., DST): check",
               "  puckering on the strike-off before bulk.",
               "Sew-out on production canvas before bulk."])

CFG02 = dict(id="02", why=WHY02, short="sleeve streaks", title="SLASH STREAKS — both sleeves",
   sub="Direct embroidery on the cut sleeve panels (front half of each sleeve), before the sleeve seams · mm, finished size · art files 1:1",
   coords="PLACEMENT (sleeve pattern coords: y = 0 underarm line, cap top -cap_h)",
   view_caption="Sleeves, size M (S01 wearer's right left | S02 wearer's left right). Orange = keep-out boundary: cap 15, underarms 15, cuff seam 10.",
   placement=lambda: clear_rows("SR") + clear_rows("SL"),
   p1_notes=["Streaks sit on the FRONT half of each sleeve (S01 x > 0,",
             "S02 x < 0), as seen in the render's front view.",
             "!The render shows only the sleeve fronts: streaks end at the",
             "!sleeve top line (outer fold) [PROPOSED — back of sleeve plain].",
             "The wearer's-right sleeve carries the tip of a cream",
             "lightning branch (it crosses from the front in the render).",
             "SR fits one hooping; SL needs 2 (split files, G5/G6)."],
   dm_crops=[((60, 20, 105, 45), "Streaks: tapered satin columns, one per streak"),
             ((150, 10, 195, 35), "Branch tip: forked cream satin over streaks")],
   crops=[("SR", (120, 0, 175, 55), "Right sleeve: streaks + branch"), ("SL", (-180, 60, -125, 115), "Left sleeve streaks"),
          ("SL", (-150, 200, -95, 255), "Lower streaks")],
   mock_src="inputs/front.png", mock_crop=(0, 360, 724, 800),
   p3_note="Streaks: one tapered pointed satin column per streak (1.2–2.5 wide), parallel bundles as traced. No black ground on the sleeves (the dark in the render there is fold shading).",
   reference=["REFERENCE: both sleeves redrawn from the LOW-RES MOCKUP front view only (~1.15 mm/px) - no close-up exists (requested:",
              "inputs/closeup_request.md [sleeves]). Unwrapped onto the sleeve pattern (outer silhouette = sleeve top line, inner edge = front",
              "underarm seam, cylinder unwrap across). Streak count + angles as the render; widths at that resolution are approximate."],
   changes=["Mapped from the render's hanging sleeves onto the flat sleeve",
            "  pattern (front half): the arm's curve is unwrapped, so streaks",
            "  near the outer fold are wider than they look in the render.",
            "!Streaks end 15 short of the armhole/cap seam and do not wrap",
            "!  onto the fronts [PROPOSED]; they end at the sleeve top line.",
            "Cuff seam keep-out 10 (self-fabric cuff, never embroidered).",
            "Shell fold shading in the render is NOT stitched (no black)."],
   production=["Embroider the cut sleeve panels flat,",
               "  BEFORE the underarm seams + cuffs.",
               f"Threads per file (PES): SR {NTH['SR']}, SL {NTH['SL']}.",
               "Same backing / needle as 01.",
               "Mark the cap top notch + sleeve centre line",
               "  on each panel (DXF) before hooping.",
               "SL: split files S1 + S2 (G6)."])

if __name__ == "__main__":
    espec.build(CFG01, VIS); espec.build(CFG02, VIS)
