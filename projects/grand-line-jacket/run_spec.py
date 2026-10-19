"""Build the 01 front-scene element spec (5 pages) from the size-M art + stitch files."""
import glcore
import pickle, json
import front as F, espec
D = pickle.load(open("front_M.pkl", "rb")); VIS = {"FR": D["FR"], "FL": D["FL"]}
M = json.load(open("scene_meta.json"))
_ns = [s for s in M.get("star_trace", []) if s.get("dropped")] + [s for s in M.get("islets", []) if s.get("dropped")]
_cut = [s for s in M.get("star_trace", []) if s.get("cut_by_keepout")]
NOT_SEWN = (f"{len(_ns)} wholly inside keep-outs not sewn, " if _ns else "") + (f"{len(_cut)} cut at a keep-out (G4)" if _cut else "none cut")

def clear_rows(p):
    import emb_place as EP
    c = EP.clearances("M")[p]; b = EP.place("M")[0][p][1].bounds
    return [(f"Art box {p} ({glcore.PIECE_NAME[p]})", f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}"), ("  x range / y range", f"{b[0]:+.0f} to {b[2]:+.0f} / {b[1]:.0f} to {b[3]:.0f}")] + \
           [(f"  → {k}", f"{v:.1f}  (min {F.MIN[k]:.0f})") for k, v in c.items()]

marks = [m for m in pickle.load(open("front_M.pkl", "rb"))["info"]["marks"]]
CFG = dict(id="01", slug="front-scene", short="front scene", title="FRONT SCENE — sunrise over a sea of clouds (split at the zip)",
   sub="Direct embroidery on both cut front panels, before zip + welts · two pieces registered across the CF zip · mm, finished size · art files 1:1",
   pieces=["FR", "FL"], placement=lambda B: clear_rows("FR") + clear_rows("FL"),
   marks=[("Horizon line", None, m["y"]) if m["name"] == "horizon" else (m["name"], m["x"], m["y"]) for m in marks][:9],
   p1_notes=["!Zip: art stops 15 each side of CF (teeth + tape + topstitch).",
             "The horizon and every sun ray are cut on the same lines on",
             "both pieces: match the horizon mark on FR + FL to ±1 at the zip.",
             "Sun sits on FL (45 from CF); its rays continue on FR.",
             "!2 hoopings per piece on the factory frame (split files, G5)."],
   dm_crops=[((25, 170, 70, 195), "Sun: satin core (no ring), 20 hairline rays (long gold bean + dot, short pale run), sparse glow"),
             ((-150, 140, -105, 165), "Cloud lobes: concentric tatami rows per lobe (14° sectors), traced tones, arc rows on sage/slate"),
             ((60, 225, 105, 250), "Sea: horizontal tatami dashes, 4 teals, hairline dashed rays")],
   crops=[((20, 170, 70, 220), "Sun, burst, glitter path"), ((-170, 130, -120, 180), "Cloud bank lobes"),
          ((80, 270, 130, 320), "Islet over the sea, ray")],
   mock_crop=(110, 120, 640, 620),
   changes=["Clouds traced from the close-ups: row scale clamped (no tower",
            "  lobes), banks regrown with whole lobes at keep-outs + border,",
            "  tones by thread family (>= 18 mm2), sage top / cream base.",
            "Islets: every silhouette traced from the mockup, lobe rows",
            "  inside it; cut (never moved) at keep-outs (A14).",
            "Stars: centre, EACH arm length, diagonals, root width fitted;",
            "  " + NOT_SEWN + ".",
            "Sea: dash layout traced from the mockup; zip shadow + mockup",
            "  welts filled from the row (A15); glitter = broken bars ON it.",
            "Sun: no ring, hairline rays. Solid sea rays + welt position:",
            "  approved by Devin 19 Oct. Welts 18 toward CF (mockup touches seam)."],
   reference="Clouds traced from AI close-ups (~4.5 px/mm) registered onto the mockup; islets, stars, sea layout traced from the mockup (~1 px/mm). No originals.",
   generated=["Generated, not traced (no reference at stitch resolution): sea dash lengths / colours inside the traced layout, sun core + 20 burst rays,",
              "sky-glow hairlines, cloud arc rows (texture), star arm taper. Gates (qa_fidelity, from the shipped DSTs) on the compare sheets."],
   production=["Embroider the cut front panels flat, BEFORE",
               "  zip, welt pockets and side seams.",
               "12 threads, 40wt polyester (G3); stop order p4.",
               "Navy 12 oz duck: 75/11 sharp, 2.5 oz black",
               "  cutaway, no topping. Pre-wash shell first.",
               "Mark CF, horizon line + welt box (drills)",
               "  on each panel before hooping.",
               "Frame (factory.json): split files S1 + S2,",
               "  registration crosses open stop 1 (G6).",
               "Sew-out on production canvas before bulk."])
if __name__ == "__main__":
    r = espec.build(CFG, F, VIS)
    print({p: round(v) for p, v in r["TOT"].items()}, {c: round(v, 1) for c, v in r["WC"].items() if v >= 1.0})
