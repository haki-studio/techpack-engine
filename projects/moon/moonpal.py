"""Moon jacket thread palette + region rules, injected into the engine's shared tables (motifs2.PAL/HEX,
tech.COLOUR_ORDER/RULES/LAYER_NAMES, dst2 angle/blend sets). Import this FIRST in every moon script — before
specbase / dst2 — so thread matching (specbase.TH) and stop ordering see the moon colours.
(Engine change proposed in ENGINE_NOTES.md: per-project palette instead of this injection.)"""
import motifs2, motifs, tech

FABRIC = "#25304D"          # washed navy 12 oz duck (mockup sample) — PROPOSED, lab dip to confirm
PAL = {   # key: (hex, name, use)   — sampled from the mockup, PROPOSED
    "mivory":  ("#F7F0DA", "Moon ivory",     "moon highlight (upper left)"),
    "mcream":  ("#EADDB6", "Moon cream",     "moon body (low-density fill)"),
    "mgold":   ("#D2B979", "Moon pale gold", "moon rim shading, crater floors"),
    "mtaupe":  ("#9C9478", "Moon taupe",     "maria (dark seas), crater rims"),
    "cwhite":  ("#EEEAF6", "Cloud white",    "cloud highlight caps"),
    "clav":    ("#B5B4DE", "Cloud lavender", "cloud upper body, wisps"),
    "cperi":   ("#8587C4", "Cloud periwinkle", "cloud body"),
    "cindigo": ("#4C4E8E", "Cloud indigo",   "cloud underside shadow, scallop lines"),
    "plight":  ("#BDBAB4", "Pole light grey", "pole highlight, insulators"),
    "pgrey":   ("#86847F", "Pole grey",      "pole body, crossarms, transformer cans, WIRES"),
    "pchar":   ("#3B3A3C", "Pole charcoal",  "pole shading, bands, outlines"),
}
ORDER = ["mcream", "mivory", "mgold", "mtaupe", "cperi", "clav", "cindigo", "cwhite", "pgrey", "plight", "pchar"]

def install():
    for k, v in PAL.items():
        motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]
    for k in ORDER:
        if k not in tech.COLOUR_ORDER: tech.COLOUR_ORDER.append(k)
    # layers (sew order, back to front)
    tech.LAYER_NAMES.update({11: "Moon", 12: "Moon craters", 13: "Clouds", 14: "Wires", 15: "Pole", 16: "Pole hardware"})
    R = {
     "MN":        ("Moon body",                  "Tatami (low density)", "0° (horizontal rows)", "0.55", "4.5", "edge run + tatami 90° @ 4.0", "0.20", "low density on purpose: no stiff dome"),
     "MN-hl":     ("Moon highlight",             "Tatami (low density)", "0°",                   "0.55", "4.5", "edge run",                      "0.20", "blends 2 rows into the body"),
     "MN-rim":    ("Moon rim shading",           "Tatami (low density)", "0°",                   "0.55", "4.0", "edge run",                      "0.20", "blends 2 rows into the body"),
     "MN-mare":   ("Maria (dark seas)",          "Tatami (low density)", "30°",                  "0.60", "3.5", "edge run",                      "0.20", "sewn on top of the body: split, no satin dome"),
     "MN-crater": ("Crater floor",               "Satin",                "auto",                 "0.42", "—",   "none",                          "0.15", "≥ 1.2 wide"),
     "MN-ring":   ("Crater rims + rays",         "Run (single)",         "follows line",         "—",    "2.0", "none",                          "—",    "0.6 line, sewn on top"),
     "CL":        ("Cloud body",                 "Tatami",               "0° (horizontal)",      "0.45", "3.5", "edge run + tatami 90° @ 2.0",   "0.25", ""),
     "CL-top":    ("Cloud upper body (light)",   "Tatami",               "0°",                   "0.45", "3.0", "edge run",                      "0.25", "blends 1.5 into body"),
     "CL-shade":  ("Cloud underside shadow",     "Tatami",               "0°",                   "0.45", "3.0", "edge run",                      "0.25", "blends 1.5 into body"),
     "CL-hl":     ("Cloud highlight caps",       "Satin, turning",       "across the cap",       "0.42", "—",   "centre run",                    "0.20", "≥ 1.4 wide"),
     "CL-line":   ("Cloud scallop lines",        "Bean (triple run)",    "follows line",         "—",    "2.0", "none",                          "—",    "0.7 line, sewn on top"),
     "CL-wisp":   ("Cloud wisps / tails",        "Satin, turning",       "across the wisp",      "0.42", "—",   "centre run",                    "0.15", "blunt tips ≥ 1.0"),
     "WR":        ("Wires",                      "Bean (triple run)",    "follows line",         "—",    "2.2", "none",                          "—",    "0.8 line; ends 3 short of seams"),
     "PL":        ("Pole body",                  "Tatami",               "90° (along pole)",     "0.45", "3.5", "edge run + tatami 0° @ 2.0",    "0.25", ""),
     "PL-shade":  ("Pole shade side",            "Tatami",               "90°",                  "0.45", "3.0", "edge run",                      "0.25", "blends 1.5 into body"),
     "PL-hl":     ("Pole highlight strip",       "Satin",                "across strip",         "0.42", "—",   "centre run",                    "0.20", ""),
     "PL-band":   ("Pole bands, bolts, steps",   "Satin",                "auto",                 "0.42", "—",   "none",                          "0.15", ""),
     "PL-arm":    ("Crossarms",                  "Satin, turning",       "across the arm",       "0.42", "—",   "centre run",                    "0.20", "split satin if > 7"),
     "PL-ins":    ("Insulators",                 "Satin",                "auto",                 "0.42", "—",   "none",                          "0.15", ""),
     "PL-can":    ("Transformer cans",           "Tatami",               "90°",                  "0.45", "3.5", "edge run + tatami @ 2.0",       "0.25", ""),
     "PL-line":   ("Pole outlines + grain",      "Bean (triple run)",    "follows line",         "—",    "2.0", "none",                          "—",    "0.7 line, last in its stop"),
    }
    tech.RULES.update(R)

install()

def patch_dst2():
    """densities per region code (dst2 has global knobs): moon codes sew at low density, others at production density."""
    import dst2
    for k, v in tech.RULES.items():
        if k in dst2.PULL or v[6] in ("—", ""): continue
        dst2.PULL[k] = float(v[6])
    for k in ("MN", "MN-hl", "MN-rim", "MN-mare", "CL", "CL-top", "CL-shade", "PL", "PL-shade", "PL-can"):
        dst2.PULL[k] = float(tech.RULES[k][6])
    dst2.BLEND.update({"MN-hl": 2.0, "MN-rim": 2.0, "CL-top": 1.5, "CL-shade": 1.5, "PL-shade": 1.5})
    if getattr(dst2, "_moon_patched", False): return dst2
    orig = dst2.build_object
    LOW = {"MN": (0.55, 4.0), "MN-hl": (0.55, 4.0), "MN-rim": (0.55, 4.0), "MN-mare": (0.60, 3.5)}
    def build_object(r, earlier):
        code = tech.rule_for(r["grp"])
        if code in LOW:
            sp, lat = LOW[code]; keep = (dst2.SP_TAT, dst2.LATTICE_MIN)
            dst2.SP_TAT = sp
            if code != "MN": dst2.LATTICE_MIN = 1e12        # only the body gets the light underlay
            try:
                bl = _low_underlay(r, earlier, orig, lat) if code == "MN" else orig(r, earlier)
            finally:
                dst2.SP_TAT, dst2.LATTICE_MIN = keep
            return bl
        return orig(r, earlier)
    def _low_underlay(r, earlier, orig, lat):
        # body: edge run + one light 90° tatami underlay at `lat` mm (instead of the 2.0 lattice), then the 0.55 fill
        keep = dst2.LATTICE_MIN; dst2.LATTICE_MIN = 1e12
        try: bl = orig(r, earlier)
        finally: dst2.LATTICE_MIN = keep
        und = []
        for p in dst2.polys(r["geom"]):
            if p.area > 60: und += dst2.join_rows(dst2.tatami_rows(p.buffer(-0.8), (r["ang"] if isinstance(r["ang"], (int, float)) else 0) + 90, lat, 4.5))
        return und + bl
    dst2.build_object = build_object
    dst2._moon_patched = True
    return dst2
