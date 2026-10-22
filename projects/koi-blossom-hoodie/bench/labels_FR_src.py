# Source of bench/labels_FR.json (the session wrote the labels as this script so the windows stay editable):
#   python3 projects/koi-blossom-hoodie/bench/labels_FR_src.py projects/koi-blossom-hoodie/bench/labels_FR.json
import json, sys
LIGHT = ["kb_white", "kb_lav", "kb_ice", "kb_sky"]
def sq(x, y, r=2.2): return [[x - r, y - r], [x + r, y - r], [x + r, y + r], [x - r, y + r]]
def fish(mid, what, tail_win, root, body_win, body_seed, red_win, eye, conf=0.85):
    parts = [
      {"id": "tail", "what": "tail fin: a fan from the root", "primitive": "radial", "hint": {"polygons": [tail_win], "seeds": [root]},
       "tones": LIGHT, "z": 7.0, "direction": {"intent": "radial"}, "colour": "auto", "confidence": conf,
       "alternatives": ["lobe"], "params": {"shape": "traced", "centres": "seeds", "bead": False, "min_mass_mm2": 6.0}},
      {"id": "body", "what": "body (fins inside it)", "primitive": "lobe", "hint": {"polygons": [body_win], "seeds": [body_seed],
       "except": [f"{mid}.tail"]}, "tones": LIGHT, "z": 7.2, "direction": {"intent": "outline"}, "colour": "auto",
       "confidence": conf, "params": {"lobe_sep_mm": 60, "min_lobe_mm2": 10, "min_mass_mm2": 8, "tone": "lit"}},
    ]
    if red_win:
        parts.append({"id": "stripe", "what": "red stripe along the back", "primitive": "band", "hint": {"polygons": [red_win]},
                      "tones": ["kb_red"], "z": 7.4, "direction": {"intent": "along"}, "colour": "kb_red", "confidence": conf,
                      "params": {"min_part_mm2": 6, "min_mass_mm2": 6, "min_band_mm": 2}})
    if eye:
        parts.append({"id": "eye", "what": "eye", "primitive": "dot", "hint": {"polygons": [sq(*eye)], "seeds": [eye]},
                      "tones": ["kb_black", "kb_duck", "kb_duck_lt", "kb_navy"], "z": 7.6, "direction": {"intent": "none"},
                      "colour": "kb_black", "confidence": conf, "params": {"min_mm2": 0.2, "max_mm2": 6}})
    return {"id": mid, "what": what, "confidence": conf, "parts": parts}

M = [
 fish("fish1", "fish, top (head lower right)",
      [[-187, 34], [-174, 39], [-166, 43], [-166, 50], [-176, 53], [-188, 51]], [-167.5, 46.8],
      [[-167, 41], [-154, 43], [-140, 47], [-128, 57], [-121, 66], [-123, 73], [-140, 72], [-156, 68], [-167, 56]], [-137, 66],
      [[-168, 45], [-158, 45], [-136, 54], [-127, 63], [-137, 67], [-160, 59], [-168, 53]], [-132.2, 66.4]),
 fish("fish2", "fish, second",
      [[-143, 86], [-133, 91], [-124, 97], [-124, 104], [-133, 105], [-143, 104]], [-125.3, 101.2],
      [[-125, 96], [-112, 99], [-100, 107], [-91, 116], [-86, 124], [-89, 131], [-100, 129], [-113, 123], [-125, 107]], [-97, 124],
      [[-126, 99], [-112, 100], [-97, 112], [-93, 120], [-100, 122], [-115, 116], [-126, 106]], [-96.0, 122.2]),
 fish("fish3", "fish, middle (tail reaches the upper flower)",
      [[-178, 166], [-170, 159], [-158, 156], [-146, 163], [-144, 170], [-147, 177], [-162, 181], [-178, 181]], [-145.2, 171.5],
      [[-146, 164], [-130, 164], [-114, 173], [-100, 182], [-89, 191], [-88, 201], [-100, 204], [-121, 199], [-140, 191], [-146, 180]], [-100, 197],
      [[-146, 167], [-130, 168], [-108, 179], [-102, 186], [-108, 190], [-128, 185], [-146, 176]], [-98.4, 195.4]),
 fish("fish4", "fish, right edge (head outside the crop)",
      [[-81, 145], [-70, 148], [-63, 155], [-63, 163], [-72, 164], [-81, 158]], [-64.0, 160.5],
      [[-66, 154], [-50, 158], [-50, 183], [-61, 181], [-67, 170]], [-55, 176],
      [[-66, 158], [-50, 161], [-50, 175], [-58, 172], [-66, 166]], None),
 fish("fish5", "fish, bottom right",
      [[-109, 223], [-101, 212], [-93, 208], [-87, 227], [-87, 238], [-96, 239], [-109, 231]], [-89.5, 234.5],
      [[-90, 227], [-78, 229], [-64, 241], [-51, 256], [-46, 265], [-49, 274], [-62, 273], [-82, 264], [-90, 241]], [-58, 268],
      [[-91, 230], [-78, 232], [-62, 248], [-55, 257], [-60, 260], [-77, 252], [-91, 240]], [-53.0, 267.4]),
]
FLORA_T = ["kb_navy", "kb_cobalt", "kb_royal", "kb_corn", "kb_sky", "kb_ice", "kb_white", "kb_lav"]
M += [
 {"id": "flower_upper", "what": "the pale upper lily: petals with dark shading", "confidence": 0.75, "parts": [
   {"id": "petals", "primitive": "lobe", "hint": {"polygons": [[[-222, 94], [-186, 90], [-150, 108], [-147, 128], [-158, 160], [-196, 182], [-222, 180]]]},
    "tones": FLORA_T, "z": 6.0, "direction": {"intent": "grain"}, "colour": "auto", "confidence": 0.75,
    "params": {"layers": "shade", "lobe_sep_mm": 6, "min_lobe_mm2": 40, "tone": "lit"}}]},
 {"id": "flower_lower", "what": "the dark lower flower", "confidence": 0.6, "parts": [
   {"id": "petals", "primitive": "lobe", "hint": {"polygons": [[[-214, 182], [-176, 174], [-140, 188], [-134, 222], [-166, 241], [-200, 239], [-216, 214]]],
    "except": ["fish3.tail", "fish3.body"]},
    "tones": FLORA_T, "z": 5.0, "direction": {"intent": "grain"}, "colour": "auto", "confidence": 0.6,
    "question": "dark petals or leaves? the mockup is soft here", "alternatives": ["band"],
    "params": {"layers": "shade", "lobe_sep_mm": 6, "min_lobe_mm2": 40}}]},
 {"id": "stems", "what": "stems rising from the lower left", "confidence": 0.55, "parts": [
   {"id": "stems", "primitive": "cord", "hint": {"polygons": [[[-222, 240], [-178, 240], [-178, 300], [-222, 300]]]},
    "tones": ["kb_navy", "kb_cobalt", "kb_royal"], "z": 4.0, "direction": {"intent": "along"}, "colour": "auto", "confidence": 0.55,
    "question": "stems or the edge of a leaf?", "alternatives": ["lobe", "stroke"]}]},
 {"id": "leaves_petals", "what": "leaves and the floating petals", "confidence": 0.8, "parts": [
   {"id": "lobes", "primitive": "lobe", "hint": {"polygons": [[[-220, 30], [-50, 30], [-50, 300], [-220, 300]]]},
    "tones": FLORA_T, "z": 3.0, "direction": {"intent": "outline"}, "colour": "auto", "confidence": 0.8,
    "params": {"lobe_sep_mm": 5, "min_lobe_mm2": 15, "min_mass_mm2": 6, "tone": "dominant"}}]},
]
d = {"schema": "techpack.labels/1",
     "source": {"view": "F", "crop": [-220, 30, -50, 300], "by": "session f5e7f669 (builder-techpack-engine-g2)", "date": "2026-10-22",
                "image": "the run's vision sheet (digitize.labels.sheet on run_fr_labels.yaml: mockup + informing close-up), 3 and 5 px/mm"},
     "_doc": "ENGINE_PLAN G2: written by the session looking at the vision sheet once (no API). Each fish = radial tail (a fan from its root seed) + lobe body + band stripe + dot eye; flora = lobes / cord. Geometry is traced from the input pixels inside each window (A14).",
     "review_below": 0.6, "motifs": M}
json.dump(d, open(sys.argv[1], "w"), indent=1)
