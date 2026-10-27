"""Rev K (2026-10-23, founder pivot): KCOS becomes a washed-black kangaroo-pocket PULLOVER hoodie on the EE / Come Over
hoodie block (PLM product type "Hoodie - Akimbo": Equivalent Exchange Hoodie, Come Over Hoodie).

The engine has no pullover block (td-chair-r1 C-05) and no factory pattern was found. What exists is the PUBLISHED
size chart (PLM pipeline.size_charts "Hoodie Sizing Chart - Akimbo", inches, XS-XXL): body length (HPS to hem), shoulder
width, chest width (flat), sleeve length (shoulder seam to cuff end). Those four come from the chart; every other number
below is PROPOSED and printed amber in the pack. The outlines are for EMBROIDERY PLACEMENT ONLY: the factory sews this
hoodie already and cuts from its own EE / Come Over pattern; we ask for its DXF / panel sizes (F1) and re-place.

Coords (mm, y down): body panels x from CF / CB (+ = wearer's left on the front, wearer's right on a back view),
y from the HPS line; sleeve x from the sleeve centre line, y from the cap top; hood x from the face edge, y from the crown;
pocket x from its centre, y from its top edge. All outlines below are CUT lines (net + SA)."""
from shapely.geometry import Polygon, LineString
from shapely import affinity

IN = 25.4
# PLM pipeline.size_charts 801ed167 "Hoodie Sizing Chart - Akimbo" (published), inches
CHART = {"XS": (24.0, 25.6, 23.0, 21.1), "S": (24.8, 26.4, 24.0, 21.5), "M": (25.6, 27.2, 25.0, 21.9),
         "L": (26.4, 28.0, 26.0, 22.2), "XL": (27.2, 28.7, 27.0, 22.6), "XXL": (28.0, 29.5, 28.0, 23.0)}
CHART_COLS = ("body length", "shoulder width", "chest width (flat)", "sleeve length")
SA = 10.0                      # seam allowance [proposed]
P = dict(rib_hem=70.0, rib_cuff=70.0, neck_half=105.0, front_drop=95.0, back_drop=25.0, shoulder_drop=45.0,
         armhole=250.0, cap_h=60.0, cuff_half=125.0, hood_w=330.0, hood_h=380.0, face_band=30.0,
         pocket_top=300.0, pocket_bot=440.0, pocket_h=210.0, pocket_from_rib=0.0)
PROPOSED = {"rib_hem": "hem rib depth", "rib_cuff": "cuff rib depth", "neck_half": "neck half width",
            "front_drop": "front neck drop", "back_drop": "back neck drop", "shoulder_drop": "shoulder slope",
            "armhole": "armhole depth (straight)", "cap_h": "sleeve cap height", "cuff_half": "sleeve width at cuff seam (half)",
            "hood_w": "hood side width", "hood_h": "hood side height", "face_band": "hood face turn-back",
            "pocket_top": "pocket top width", "pocket_bot": "pocket bottom width", "pocket_h": "pocket height"}

def poms(size):
    bl, sh, ch, sl = (v * IN for v in CHART[size])
    return dict(body_length=bl, shoulder=sh, chest=ch, sleeve=sl)

def _cut(net): return net.buffer(SA, join_style=2)

def body(size, front=True):
    import math
    m = poms(size); L = m["body_length"] - P["rib_hem"]; W = m["chest"] / 2; S = m["shoulder"] / 2
    nh = P["neck_half"]; nd = P["front_drop"] if front else P["back_drop"]; sd = P["shoulder_drop"]; ah = P["armhole"]
    neck = [(nh * math.sin(t / 16 * math.pi / 2), nd * math.cos(t / 16 * math.pi / 2)) for t in range(17)]   # CF/CB -> HPS
    arm = [(S + (W - S) * (t / 10) ** 1.6, sd + ah * (t / 10)) for t in range(11)]                       # drop shoulder
    right = neck + arm + [(W, L), (0.0, L)]
    pts = right + [(-x, y) for x, y in reversed(right[1:-1])]
    return _cut(Polygon(pts).buffer(0))

def sleeve(size):
    m = poms(size); top = m["sleeve"] - P["rib_cuff"]
    import math
    hw = math.hypot(m["shoulder"] / 2 - m["chest"] / 2, P["armhole"]) + 8.0             # armhole seam + cap ease [proposed]
    cap = [(hw * (t / 10 * 2 - 1), P["cap_h"] * (abs(t / 10 * 2 - 1) ** 1.8)) for t in range(11)]
    pts = cap + [(P["cuff_half"], P["cap_h"] + top), (-P["cuff_half"], P["cap_h"] + top)]
    return _cut(Polygon(pts).buffer(0))

def hood():
    w, h = P["hood_w"], P["hood_h"]
    pts = [(0, 30), (60, 4), (170, 0), (260, 30), (315, 95), (w, 180), (w - 25, h), (0, h)]
    return _cut(Polygon(LineString(pts + [(0, 30)]).coords[:-1]).buffer(0).simplify(0.2))

def pocket():
    t, b, h = P["pocket_top"] / 2, P["pocket_bot"] / 2, P["pocket_h"]
    return _cut(Polygon([(-t, 0), (t, 0), (b, h), (-b, h)]))

def pocket_on_front(size):
    """net pocket footprint on the front panel: bottom edge sewn into the hem rib seam [proposed]"""
    m = poms(size); L = m["body_length"] - P["rib_hem"]
    t, b, h = P["pocket_top"] / 2, P["pocket_bot"] / 2, P["pocket_h"]
    return Polygon([(-t, L - h), (t, L - h), (b, L), (-b, L)])

def pieces(size):
    """cut outlines; HD1/HD2 = left/right hood side, SL/SR sleeves (mirror pair)"""
    s = sleeve(size); h = hood()
    return {"FR": body(size, True), "BK": body(size, False), "PK": pocket(), "SR": s, "SL": affinity.scale(s, -1, 1, origin=(0, 0)),
            "HR": h, "HL": affinity.scale(h, -1, 1, origin=(0, 0))}

NAMES = {"FR": "Front", "BK": "Back", "PK": "Kangaroo pocket", "SR": "Right sleeve", "SL": "Left sleeve",
         "HR": "Hood, right side", "HL": "Hood, left side"}

if __name__ == "__main__":
    for sz in CHART:
        g = pieces(sz); print(sz, {k: tuple(round(v) for v in (p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1])) for k, p in g.items()})
