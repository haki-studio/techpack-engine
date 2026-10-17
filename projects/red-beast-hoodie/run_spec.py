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

REF = [f"Art traced, not redrawn by hand: the head from the mockup's own detail panel (right half of inputs/flat.png),",
       f"registered onto the full mockup by a projective fit ({REG['inliers']} SIFT matches, residual {REG['resid_mm_median']:.1f} mm median / {REG['resid_mm_p90']:.1f} mm p90);",
       "mane, lightning, streaks + sleeves from the low-res mockup (~1.15 mm/px). No original artwork files."]

WHY01 = ["Red hair strokes first, crimson shadow strokes next: their travel hides under the black ground sewn after them (LESSONS B2/B14).",
         "Black ground fills between the red strokes as one connected area (few trims), then the cream outlines + teeth sew LAST so they sit",
         "raised on top of red and black, as the mockup's white raised outline. Same thread may repeat as a stop where merging would cross art."]
WHY02 = ["Red streaks first, crimson shadow strokes next (they sit inside and beside the red streaks), cream branch tip last on top (SR only).",
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
   dm_crops=[((150, 212, 195, 234), "Teeth + mouth: cream satin teeth, black ground"),
             ((40, 152, 85, 174), "Hair strokes: red satin columns + tatami cells"),
             ((-215, 40, -170, 62), "Lightning branch: forked cream satin")],
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
            "Black ground: stitched black between the red strokes, in the mouth",
            "  + under the jaw, as the detail panel shows (black on black).",
            "Specks < 3 mm² on bare fabric (denim highlights) dropped."],
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
   dm_crops=[((60, 20, 105, 45), "Streak strokes: satin columns along the slash"),
             ((150, 10, 195, 35), "Branch tip: forked cream satin over streaks")],
   crops=[("SR", (120, 0, 175, 55), "Right sleeve: streaks + branch"), ("SL", (-180, 60, -125, 115), "Left sleeve streaks"),
          ("SL", (-150, 200, -95, 255), "Lower streaks")],
   mock_src="inputs/front.png", mock_crop=(0, 360, 724, 800),
   p3_note="Streaks: red + crimson satin strokes; wide parts tatami along the slash. No black ground on the sleeves (the dark in the render there is fold shading).",
   reference=["Sleeve art traced from the low-res mockup front view (~1.15 mm/px), unwrapped onto the sleeve pattern",
              "(outer silhouette = sleeve top line, inner edge = front underarm seam, cylinder unwrap across). Counts + angles as the render;",
              "stroke widths at that resolution are approximate. No close-up of the sleeves exists."],
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
