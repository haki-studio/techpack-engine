"""Moon jacket pattern = the Drum Island pattern (engine/pattern.py) unchanged in shape; only the material
labels and piece notes differ (navy-black corduroy + rib, washed navy duck). Import this before pattern_out /
emb_place so every caller (DXF, plot PDF, pages) sees the moon labels."""
import pattern as PT

STYLE = "HK-JK-DRUM-MOON"
MAT = {"C01": "Corduroy — 14 wale, navy-black", "C02": "Corduroy — 14 wale, navy-black",
       "R01": "Rib knit 1×1 — navy-black", "R02": "Rib knit 1×1 — navy-black"}
SHELL = "Shell — 12 oz duck, washed navy"
NOTE = {"B01": "embroidery 01 sewn on the cut panel; licensed-figure placeholder box marked",
        "F01": "welt pocket marked; embroidery 02L + 03L placement", "F02": "welt pocket marked; embroidery 02R + 03R placement",
        "S01": "embroidery 04R sleeve clouds", "S02": "embroidery 04L sleeve clouds"}

_draft = PT.draft
_cache = {}
def draft(size):
    if size in _cache: return _cache[size]
    g, mt = _draft(size)
    for code, pc in g.items():
        if code in MAT: pc.material = MAT[code]
        elif pc.material.startswith("Shell — 12 oz duck"): pc.material = SHELL
        if code in NOTE: pc.note = NOTE[code]
        if code.startswith("I") and "R0" in code: pass
    g["R01"].note = "folded double; wales run across the height; ends into the zip"
    add_wire_notches(size, g, mt)
    _cache[size] = (g, mt)
    return g, mt

def add_wire_notches(size, g, mt):
    """labelled wire notches (DXF layer 4 + text): the heights above the hem seam where 01 + 03 wires cross the side
    seams (same number on back and front), and where the 03 wires / wisps meet the zip keep-out (CF edge, both fronts)."""
    import scene, os, pickle
    sc = scene.SCALE[scene.GRADE[size][0]]
    def put(pc, edge_name, hs, from_hem_end, label):
        e = next(x for x in g[pc].edges if x.name == edge_name); L = e.length
        pc_ = g[pc]; pc_.wire_notches = getattr(pc_, "wire_notches", [])
        for h in hs:
            s = h if from_hem_end else L - h
            e.notches.append(s)
            p, _ = PT.at(e.pts, s); pc_.wire_notches.append((p, f"{label}{h:.0f}"))
    HL = [h * sc for h in scene.H_LEFT]; HR = [h * sc for h in scene.H_RIGHT]
    put("B01", "side L", HL, False, "W"); put("B01", "side R", HR, True, "W")
    put("F01", "side", HL, False, "W"); put("F02", "side", HR, False, "W")
    ap = f"art_{size}.pkl"
    if os.path.exists(ap):
        mk = pickle.load(open(ap, "rb"))["info"]["marks"]
        for pc, key in (("F01", "zip_L"), ("F02", "zip_R")):
            e = next(x for x in g[pc].edges if x.name == "CF / zip")
            ys = sorted({round(y) for grp, y in mk[key] if grp == "WR"})
            hs = [mt["hem_f"] - y for y in ys]
            from_hem = abs(e.pts[0][1] - mt["hem_f"]) < 1e-6
            for h in hs:
                s_ = h if from_hem else e.length - h
                e.notches.append(s_); p, _ = PT.at(e.pts, s_)
                g[pc].wire_notches = getattr(g[pc], "wire_notches", []) + [(p, f"Z{h:.0f}")]
PT.draft = draft
if not hasattr(PT, "_moon"):
    PT._moon = True
