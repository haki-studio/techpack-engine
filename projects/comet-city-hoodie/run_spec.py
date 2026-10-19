"""Build the element specs (5 pages each) from the size-M art + stitch files: 01 front scene (FR + FL), 02 sleeves (SR + SL).
usage: python3 run_spec.py [01] [02]"""
import cccore
import pickle, json, sys
from PIL import Image, ImageDraw
from shapely import affinity
import front as F, espec, stitchrender as SR
D = pickle.load(open("art_M.pkl", "rb")); VIS = {P: D[P] for P in cccore.PIECES}
M = json.load(open("scene_meta.json"))
SM = M.get("sleeves", {})

def clear_rows(p):
    import emb_place as EP
    c = EP.clearances("M")[p]; b = EP.place("M")[0][p][1].bounds; mn = EP.mins(p)
    return [(f"Art box {p} ({cccore.PIECE_NAME[p]})", f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}"), ("  x range / y range", f"{b[0]:+.0f} to {b[2]:+.0f} / {b[1]:.0f} to {b[3]:.0f}")] + \
           [(f"  → {k}", f"{v:.1f}  (min {mn[k]:.0f})") for k, v in c.items()]

def sleeve_view(V):
    """both sleeves flat, front half facing up: left sleeve (S02) on the left, right sleeve (S01) on the right"""
    g, _ = F.pieces("M"); ppm = 2.4; gap = 20
    imgs = []
    for P, code in (("SL", "S02"), ("SR", "S01")):
        pc = g[code].sew_poly(); b = pc.bounds; bb = (b[0] - 6, b[1] - 6, b[2] + 6, b[3] + 6)
        im = SR.render(V[P], bb, ppm, base=cccore.FABRIC)
        mask = Image.new("L", im.size, 0); T = lambda cs: [((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in cs]
        ImageDraw.Draw(mask).polygon(T(pc.exterior.coords), fill=255)
        out = Image.new("RGB", im.size, (255, 255, 255)); out.paste(im, (0, 0), mask); d = ImageDraw.Draw(out)
        d.line(T(pc.exterior.coords), fill=(90, 70, 50), width=3)
        d.line(T([(0, b[1]), (0, b[3])]), fill=(0, 163, 255), width=2)
        cl = F.sleeve_clip("M", "R" if P == "SR" else "L"); d.line(T(cl.exterior.coords), fill=(230, 120, 40), width=1)
        imgs.append(out)
    W = sum(i.width for i in imgs) + int(gap*ppm); H = max(i.height for i in imgs)
    canvas = Image.new("RGB", (W, H), (255, 255, 255)); x = 0
    for i in imgs: canvas.paste(i, (x, 0)); x += i.width + int(gap*ppm)
    wmm = W / ppm; hmm = H / ppm
    return canvas, (0, 0, wmm, hmm), ppm, ("Both sleeves flat, size M: left sleeve S02 (left), right sleeve S01 (right). Blue = sleeve centre line (shoulder notch); "
                                           "orange = keep-out (cap 15, underarm 15, cuff 10). Art on the front-facing half only.")

marks = pickle.load(open("art_M.pkl", "rb"))["info"]["marks"]
REF = ("References: the founder's close-up (inputs/closeup_mockup_comet.png) registered onto the fronts (7 matched features, exact fit) - the comet "
       "is traced from it; mockup (~1 px/mm) for placement + clouds (5 traced tones); city, figure, lamp, bike drawn in the close-up's style. Not originals.")
CFG01 = dict(id="01", slug="front-scene", short="front scene", title="FRONT SCENE — comet over a night city (split at the zip)",
   sub="Direct embroidery on both cut front panels, before zip + welts · two pieces registered across the CF zip · mm, finished size · art files 1:1",
   pieces=["FR", "FL"], placement=lambda B: clear_rows("FR") + clear_rows("FL"),
   marks=[(m["name"], m["x"], m["y"]) for m in marks],
   p1_notes=["!Zip: art stops 15 each side of CF (teeth + tape + topstitch).",
             "The comet, top rail and kerb line are cut on the same lines on",
             "both pieces: match the marks on FR + FL to ±1 at the zip.",
             "Hood neck 10, welt 8 (6 + 2 cut-out) [proposed — confirm].",
             "!2 hoopings per piece on the factory frame (split files, G5)."],
   dm_crops=[((110, 100, 155, 125), "Comet: tapered turning satin strands, 5 threads"),
             ((-215, 150, -170, 175), "Clouds: 3 tone areas, short tatami rows (0° / 8°)"),
             ((40, 395, 85, 420), "City: vertical tatami buildings, satin windows, railing")],
   crops=[((-85, 255, -45, 305), "Comet head + cloud"), ((25, 270, 65, 320), "Falling star"), ((40, 380, 80, 430), "Figure + windows")],
   mock_crop=(120, 300, 620, 810),
   changes=["Comet: broad body = the whole traced extent (9 bands,",
            f"  core position traced) + {M['n_comet_strands']} tapering streaks, own core stops.",
            "Clouds: 5 tones at thread-luminance midpoints (pale tops,",
            "  dark undersides), rounded tone edges, lobed bank ends.",
            f"City: {M['n_towers']} towers ({M['n_far']} far, {M['n_near']} near), {M['n_lit_edges']} lit edges,",
            f"  {M['n_windows']} windows in floor grids, {M['n_signs']} signs, haze + violet/rose glow.",
            f"Stars {M['n_stars']}, {M['n_meteors']} meteors (white heads), falling star + halo.",
            "Figure solid navy, dusk raglan sleeves, azure rim, hands.",
            "Lamp: dark lantern + ice rim; bike dark tubes + glints.",
            "Bike lifted 14; welt margin 8 (art 8.7) [proposed]."],
   reference=REF,
   generated=["Traced (A14 gate, fidelity.json): comet extent + colour bands, every cloud, every meteor streak, falling-star position.",
              "GENERATED, NOT TRACED: skyline towers + windows (original skyline, IP), figure (own pose, IP), lamp, bicycle, railing, bush,",
              "star shapes (positions traced), comet strand texture (inside the traced extent). Redrawn from a low-res mockup + one close-up."],
   production=["Embroider the cut front panels flat, BEFORE",
               "  zip, welt pockets and side seams.",
               "12 threads per file, 40wt polyester (G3).",
               "Navy duck: 75/11 sharp, 2.5 oz black",
               "  cutaway, no topping. Pre-wash shell first.",
               "Mark CF, top rail line + welt box (drills)",
               "  on each panel before hooping.",
               "Frame (factory.json): split files S1 + S2,",
               "  registration crosses open stop 1 (G6).",
               "Sew-out on production shell before bulk."])
CFG02 = dict(id="02", slug="sleeve-garden", short="sleeves", title="SLEEVES — night garden, clouds and stars",
   sub="Direct embroidery on both cut sleeve panels, before the underarm seam · one file per sleeve per size · mm, finished size · art files 1:1",
   pieces=["SL", "SR"], placement=lambda B: clear_rows("SR") + clear_rows("SL"), view=sleeve_view,
   coords="PLACEMENT (sleeve pattern coords: x from the sleeve centre line, y down from the underarm line)",
   p1_notes=["Art on the front-facing half of each sleeve (the half seen",
             "from the front), reaching 30 past the centre line [proposed].",
             "!Back half of each sleeve plain [proposed — confirm].",
             "Sleeves are not mirror images: SL carries the tall garden",
             f"  ({SM['SL']['plants']} motifs), SR the stars, meteor + lower garden ({SM['SR']['plants']})."],
   dm_crops=[((-90, 300, -45, 325), "Palm fronds: two-tone satin leaflets on a satin rib"),
             ((-170, 200, -125, 225), "Cloud: 3 tone areas, short tatami rows"),
             ((75, 52, 120, 77), "Stars: tapered satin arms, white centres")],
   crops=[((-100, 300, -60, 350), "Palm plant"), ((-170, 190, -130, 240), "Cloud + leaves"), ((76, 42, 116, 92), "Stars")],
   mock_crop=(0, 560, 160, 840), mock_w=34,
   changes=[f"Foliage: SL {SM['SL']['plants']}, SR {SM['SR']['plants']} motifs (palms at the mockup",
            "  rosettes + ferns, broad leaves, sprigs by area), 5 blues,",
            f"  back plants dark, front bright; fireflies SR {SM['SR']['fireflies']}, SL {SM['SL']['fireflies']}.",
            "Clouds = the mockup's areas in 4 shaded tones, re-mapped",
            "  from the hanging (curved) sleeve onto the flat piece.",
            f"Stars: SR {SM['SR']['stars']}, SL {SM['SL']['stars']} at the mockup positions; SR meteor.",
            "Art stops 15 from cap + underarm seams, 10 from cuff."],
   reference=REF,
   generated=["Traced (A14 gate, fidelity.json): every sleeve cloud (incl. undersides) and the foliage AREA (undergrowth fill).",
              "GENERATED, NOT TRACED: the individual leaves / palms / ferns (below the hanging-sleeve mockup's resolution, ~1 px/mm),",
              "star shapes (positions traced). Redrawn from the low-res mockup: no sleeve close-up exists (prompt in inputs/closeup_request.md)."],
   production=["Embroider the cut sleeve panels flat,",
               "  BEFORE the underarm seam and cuff.",
               "Sleeve threads: see G3 / p4 (10 colours).",
               "Mark the centre line + cuff seam before",
               "  hooping. Frame: split files (G6).",
               "Same backing / needle as the fronts."])

if __name__ == "__main__":
    which = sys.argv[1:] or ["01", "02"]
    for c in (CFG01, CFG02):
        if c["id"] in which:
            r = espec.build(c, F, VIS)
            print(c["id"], {k: round(v, 1) for k, v in r["WC"].items() if v >= 1.0})
