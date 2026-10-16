"""Moon jacket thread palette + region rules, injected into the engine's shared tables (motifs2.PAL/HEX,
tech.COLOUR_ORDER/RULES/LAYER_NAMES, dst2 angle/blend sets). Import this FIRST in every moon script — before
specbase / dst2 — so thread matching (specbase.TH) and stop ordering see the moon colours.
(Engine change proposed in ENGINE_NOTES.md: per-project palette instead of this injection.)"""
import motifs2, motifs, tech

FABRIC = "#25304D"          # washed navy 12 oz duck (mockup sample) — PROPOSED, lab dip to confirm
PAL = {   # key: (hex, name, use) — Rev B: sampled from the mockup by k-means on the moon / cloud / pole pixels. PROPOSED
    "m1": ("#F1E5D2", "Moon highlight",  "lightest moon face"),
    "m2": ("#EADCC1", "Moon cream",      "moon body"),
    "m3": ("#E0CDAB", "Moon warm",       "warm tone, rim"),
    "m4": ("#D4C5A4", "Moon crater light", "crater + mare light tone"),
    "m5": ("#B2A98B", "Moon crater dark",  "crater + mare dark tone (grey-green)"),
    "c1": ("#DED6E6", "Cloud white",     "highlight caps"),
    "c2": ("#B8AECB", "Cloud lavender",  "light band"),
    "c3": ("#8E8AB0", "Cloud periwinkle", "cloud body"),
    "c4": ("#73729F", "Cloud violet",    "lower band"),
    "c5": ("#535A8A", "Cloud indigo",    "underside + scallop lines"),
    "p1": ("#C1B6AC", "Pole light grey", "highlights, insulators"),
    "p2": ("#7A747C", "Pole grey",       "pole body, hardware, WIRES"),
    "p3": ("#4E484F", "Pole dark grey",  "shade side, can ribs"),
    "p4": ("#2A282E", "Pole charcoal",   "outlines, bands, wood grain"),
}
ORDER = ["m2", "m1", "m3", "m4", "m5", "c3", "c2", "c4", "c1", "c5", "p2", "p1", "p3", "p4"]
# mockup tones used to SEGMENT the image (screen colours of the render) -> thread key
SEG = {"m1": (233, 218, 196), "m2": (228, 210, 180), "m3": (218, 197, 164), "m4": (201, 180, 148), "m5": (170, 152, 126),
       "c1": (188, 176, 193), "c2": (146, 139, 165), "c3": (115, 113, 147), "c4": (82, 89, 127), "c5": (64, 70, 104),
       "p1": (193, 181, 170), "p2": (117, 111, 116), "p3": (76, 70, 76), "p4": (18, 17, 22),
       "navy": (33, 43, 66), "navy2": (25, 33, 52)}

def install():
    for k, v in PAL.items():
        motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]
    for k in ORDER:
        if k not in tech.COLOUR_ORDER: tech.COLOUR_ORDER.append(k)
    # layers (sew order, back to front)
    tech.LAYER_NAMES.update({11: "Moon", 12: "Moon craters", 13: "Clouds", 14: "Wires", 15: "Pole", 16: "Pole hardware"})
    R = {
     "MN":        ("Moon body (cream)",          "Tatami", "turning: rows concentric (15° sectors)", "0.45", "3.5", "edge run + tatami 90° @ 2.0", "0.20", "traced tonal region"),
     "MN-hl":     ("Moon highlight",             "Tatami", "concentric (15° sectors)", "0.45", "3.5", "edge run (+ lattice if > 60 mm²)", "0.20", "short-stitch blend 1.0"),
     "MN-warm":   ("Moon warm tone + rim",       "Tatami", "concentric (15° sectors)", "0.45", "3.5", "edge run (+ lattice if > 60 mm²)", "0.20", "short-stitch blend 1.0"),
     "MN-crater": ("Crater / mare light",        "Tatami", "concentric (15° sectors)", "0.45", "3.5", "edge run",                      "0.20", "short-stitch blend 1.0"),
     "MN-mare":   ("Crater / mare dark",         "Tatami", "concentric (15° sectors)", "0.45", "3.5", "edge run",                      "0.20", "short-stitch blend 1.0"),
     "CL":        ("Cloud body (periwinkle)",    "Tatami / satin < 3", "0° (horizontal banding)", "0.45", "3.5", "edge run + tatami 90° @ 2.0", "0.25", "traced band"),
     "CL-top":    ("Cloud light band (lavender)", "Tatami / satin < 3", "0°",     "0.45", "3.5", "edge run",                      "0.25", "blend 1.0"),
     "CL-hl":     ("Cloud highlight (white)",    "Tatami / satin < 3", "0°",     "0.45", "3.5", "edge run",                      "0.20", "blend 1.0"),
     "CL-mid":    ("Cloud lower band (violet)",  "Tatami / satin < 3", "0°",     "0.45", "3.5", "edge run",                      "0.25", "blend 1.0"),
     "CL-shade":  ("Cloud underside (indigo)",   "Tatami / satin < 3", "0°",     "0.45", "3.5", "edge run",                      "0.25", ""),
     "CL-line":   ("Cloud scallop lines",        "Bean (triple run)", "follows line", "—", "2.0", "none",                      "—",    "0.7 line, sewn on top"),
     "CL-wisp":   ("Cloud wisps / tails",        "Satin, turning",    "across the wisp", "0.42", "—", "centre run",           "0.15", "blunt tips ≥ 1.0"),
     "WR":        ("Wires",                      "Bean (triple run)", "follows line", "—", "2.2", "none",                      "—",    "0.8 line; ends 3 short of seams"),
     "PL":        ("Pole grey (body, hardware)", "Tatami / satin < 3", "along long axis", "0.45", "3.5", "edge run + tatami @ 2.0", "0.25", "traced"),
     "PL-hl":     ("Pole light grey",            "Tatami / satin < 3", "along long axis", "0.45", "3.5", "edge run",             "0.20", ""),
     "PL-shade":  ("Pole dark grey",             "Tatami / satin < 3", "along long axis", "0.45", "3.5", "edge run",             "0.25", ""),
     "PL-band":   ("Pole charcoal (bands, edges)", "Satin / tatami",  "auto",          "0.42", "—", "none",                      "0.15", ""),
     "PL-line":   ("Pole wood grain + outlines", "Bean (triple run)", "follows line", "—", "2.0", "none",                      "—",    "0.7 line, last in its stop"),
    }
    tech.RULES.update(R)

install()

def patch_dst2():
    """Rev B: no density override (fidelity first, production density everywhere); only blends + pull for the moon codes."""
    import dst2
    dst2.BLEND.update({"MN-hl": 1.0, "MN-warm": 1.0, "MN-crater": 1.0, "MN-mare": 1.0, "CL-top": 1.0, "CL-hl": 1.0, "CL-mid": 1.0})
    return dst2
