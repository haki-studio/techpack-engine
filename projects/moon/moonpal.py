"""Moon jacket thread palette + region rules, injected into the engine's shared tables (motifs2.PAL/HEX,
tech.COLOUR_ORDER/RULES/LAYER_NAMES, dst2 angle/blend sets). Import this FIRST in every moon script — before
specbase / dst2 — so thread matching (specbase.TH) and stop ordering see the moon colours.
(Engine change proposed in ENGINE_NOTES.md: per-project palette instead of this injection.)"""
import motifs2, motifs, tech

FABRIC = "#25304D"          # washed navy 12 oz duck (mockup sample) — PROPOSED, lab dip to confirm
PAL = {   # key: (hex, name, use) — Rev B: from the close-ups (inputs/closeups), k-means of moon / cloud / pole pixels. PROPOSED
    "m1": ("#F7E6CA", "Moon highlight",    "lightest moon face"),
    "m2": ("#F2D2A0", "Moon cream",        "moon body"),
    "m3": ("#E5BE85", "Moon pale gold",    "warm tone, rim"),
    "m4": ("#CFA872", "Moon crater light", "crater + mare light tone"),
    "m5": ("#9A8E74", "Moon crater dark",  "crater + mare dark tone (grey-green taupe), rays"),
    "c1": ("#DCCFE2", "Cloud white-pink",  "highlight tops"),
    "c2": ("#A9A1C8", "Cloud lavender",    "light band"),
    "c3": ("#8682AE", "Cloud periwinkle",  "cloud body"),
    "c4": ("#66699A", "Cloud violet",      "lower band"),
    "c5": ("#464B7D", "Cloud indigo",      "underside + scale lines"),
    "p1": ("#CBBEBE", "Pole light grey",   "highlights, insulators"),
    "p2": ("#8B7C7E", "Pole grey",         "pole body, hardware, WIRES, registration crosses"),
    "p3": ("#645659", "Pole dark grey",    "shade side, can ribs"),
    "p4": ("#2E2729", "Pole charcoal",     "outlines, bands, wood grain"),
}
ORDER = ["m2", "m1", "m3", "m4", "m5", "c3", "c2", "c4", "c1", "c5", "p2", "p1", "p3", "p4"]
# manufacturer limit (factory.json, 2026-10-16): <= 12 colours per stitch file incl. basting/registration.
# Two pairs merged in every file (pole dark grey -> charcoal ΔE 10.9, cloud violet -> periwinkle ΔE 9.3) so the moon keeps all
# 5 close-up tones (fidelity first); the in-between tone comes
# from the short-stitch density blends at the tone edges instead of a 13th thread.
FILE_MERGE = {"p1": "c1", "c4": "c3"}
USED = [k for k in ORDER if k not in FILE_MERGE]
REG_COL = "p2"      # registration crosses (removable runs) in a colour the file already has
PH_COL = "m2"       # placeholder outline in moon cream: hidden under the 01b moon-in-box fill
# mockup tones used to SEGMENT the image (screen colours of the render) -> thread key
SEG = {"m1": (233, 218, 196), "m2": (228, 210, 180), "m3": (218, 197, 164), "m4": (201, 180, 148), "m5": (170, 152, 126),
       "c1": (188, 176, 193), "c2": (146, 139, 165), "c3": (115, 113, 147), "c4": (82, 89, 127), "c5": (64, 70, 104),
       "p1": (193, 181, 170), "p2": (117, 111, 116), "p3": (76, 70, 76), "p4": (18, 17, 22),
       "navy": (33, 43, 66), "navy2": (25, 33, 52)}

def HEXK(k): return PAL[k][0]

def install():
    for k, v in PAL.items():
        motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]
    for k in ORDER:
        if k not in tech.COLOUR_ORDER: tech.COLOUR_ORDER.append(k)
    # layers (sew order, back to front)
    tech.LAYER_NAMES.update({11: "Moon", 12: "Moon craters", 13: "Moon crater centres", 14: "Wires", 15: "Pole", 16: "Pole hardware"})
    R = {
     "MN":        ("Moon body (cream)",          "Flow tatami (ground) / satin (cells)", "along the close-up swirl (streamlines)", "0.40", "3.5", "edge run + 45° lattice @ 2.0 (> 60 mm²)", "0.20", "traced tone region; cells satin on top"),
     "MN-hl":     ("Moon highlight",             "Flow tatami / satin", "along the swirl; cells: long axis", "0.40", "3.5", "edge run + lattice (> 60 mm²)", "0.20", "tones overlap 0.3"),
     "MN-warm":   ("Moon warm tone + rim",       "Flow tatami / radial satin rim", "swirl; rim radial", "0.40", "3.5", "edge run + lattice (> 60 mm²)", "0.20", "tones overlap 0.3"),
     "MN-crater": ("Crater / mare light",        "Flow tatami / satin", "swirl; cells: long axis", "0.40", "3.5", "edge run",                      "0.20", "tones overlap 0.3"),
     "MN-mare":   ("Crater / mare dark (star craters)", "Flow tatami / radial satin (stars)", "swirl; stars radial", "0.40", "3.5", "edge run",     "0.20", "traced star outlines"),
     "MN-ray":    ("Crater rays + rim strokes",  "Run (single)",      "follows line", "—", "2.0", "none",                      "—",    "0.6 line, sewn on top"),
     "CL":        ("Cloud body (periwinkle)",    "Satin scales + flow tatami", "scales along the close-up rows", "0.42 / 0.45", "3.5", "edge run (tatami)", "0.25", "scallop rows, top row first"),
     "CL-top":    ("Cloud light band (lavender)", "Tatami / satin < 3", "0°",     "0.45", "3.5", "edge run",                      "0.25", "blend 1.0"),
     "CL-hl":     ("Cloud highlight (white)",    "Tatami / satin < 3", "0°",     "0.45", "3.5", "edge run",                      "0.20", "blend 1.0"),
     "CL-mid":    ("Cloud lower band (violet)",  "Tatami / satin < 3", "0°",     "0.45", "3.5", "edge run",                      "0.25", "blend 1.0"),
     "CL-shade":  ("Cloud underside (indigo)",   "Tatami / satin < 3", "0°",     "0.45", "3.5", "edge run",                      "0.25", ""),
     "CL-line":   ("Cloud scallop lines",        "Bean (triple run)", "follows line", "—", "2.0", "none",                      "—",    "0.7 line, sewn on top"),
     "CL-wisp":   ("Cloud wisps / tails",        "Satin, turning",    "across the wisp", "0.42", "—", "centre run",           "0.15", "blunt tips ≥ 1.0"),
     "WR":        ("Wires (twisted cord)",       "Satin, turning",    "across the cord", "0.42", "—", "centre run",           "0.15", "1.6 wide; ends 3 short of seams"),
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
    import stitchrender as SR, shapely
    from shapely.validation import make_valid
    if not getattr(SR, "_moon_safe", False):
        _h = SR.hatch
        def hatch(p, ang, sp):
            try: return _h(p, ang, sp)
            except Exception:                 # pinched blend zones from unions: snap + retry, else skip that zone
                try: return _h(shapely.set_precision(make_valid(p).buffer(0), 0.01).buffer(0), ang, sp)
                except Exception: return []
        SR.hatch = hatch; SR._moon_safe = True
    if not getattr(dst2, "_moon_rows", False):
        _bo = dst2.build_object
        def build_object(r, earlier_tones):
            if r.get("rows") is None: return _bo(r, earlier_tones)
            return flow_blocks(dst2, r)
        dst2.build_object = build_object; dst2._moon_rows = True
    dst2.BLEND.update({"MN-hl": 1.0, "MN-warm": 1.0, "MN-crater": 1.0, "MN-mare": 1.0, "CL-top": 1.0, "CL-hl": 1.0, "CL-mid": 1.0})
    return dst2

def flow_blocks(dst2, r, L=3.5, sp=0.45):
    """Rev C moon ground (moon3.py): tatami rows ALONG precomputed streamlines (r['rows']) clipped to this object,
    edge run + light 45° lattice underlay first, rows chained nearest-end-first (reversing as needed), 3.5 mm stitches
    staggered by row like tatami. Rows are 0.45 mm apart (= dst2.SP_TAT)."""
    import math
    from shapely.geometry import LineString
    p = r["geom"]; out = []
    if p.is_empty or p.area < 0.06: return out
    for q in dst2.polys(p):
        out += dst2.edge_run(q, 0.6)
        if q.area > dst2.LATTICE_MIN: out += dst2.join_rows(dst2.tatami_rows(q.buffer(-0.8), 45, 2.0, 4.0))
    ml = r["rows"].intersection(p.buffer(0.2))
    segs = [g for g in getattr(ml, "geoms", [ml]) if g.geom_type == "LineString" and g.length > 0.6]
    if not segs: return [b for b in out if len(b) > 1]
    ends = [(s.coords[0], s.coords[-1]) for s in segs]; used = [False] * len(segs); order = []
    import numpy as np
    from scipy.spatial import cKDTree
    E = np.array([e for a_b in ends for e in a_b]); tree = cKDTree(E)
    pos = ends[0][0]
    for _ in range(len(segs)):
        k = 8; j = None
        while j is None:
            dd, ii = tree.query(pos, k=min(k, len(E)))
            for i_ in np.atleast_1d(ii):
                if not used[i_ // 2]: j = int(i_); break
            if j is None:
                if k >= len(E):
                    j = next(2 * i for i, u in enumerate(used) if not u)
                k *= 4
        si = j // 2; used[si] = True
        cs = list(segs[si].coords)
        if j % 2 == 1: cs = cs[::-1]
        order.append(cs); pos = cs[-1]
    rows = []
    for n, cs in enumerate(order):
        ln = LineString(cs); D = ln.length; off = (n % 3) * L / 3
        ts = [0.0] + [t for t in np.arange(off if off > 0.4 else L, D - 0.4, L)] + [D]
        rows.append([ln.interpolate(t).coords[0] for t in ts])
    out += dst2.join_rows(rows)
    return [b for b in out if len(b) > 1]
