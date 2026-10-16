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
    _cache[size] = (g, mt)
    return g, mt
PT.draft = draft
if not hasattr(PT, "_moon"):
    PT._moon = True
