"""Document helpers for this project: CJK / Hangul strings drawn as font OUTLINES (the sheet font has no CJK glyphs and
the factory must see the exact characters), thread names, machine hours, data loading."""
import kccore
import json, os, pickle
from shapely import affinity
from shapely.ops import unary_union
from render import geom_to_path, f
import kclettering as KL
import factory as FA

PROF = FA.load(); FRAME = FA.largest_frame(PROF); FR_S = f"{FRAME[0]:.0f} × {FRAME[1]:.0f}"
def mh(r): return FA.machine_hours(r["stitches"], PROF, trims=r["trims"], colour_changes=r["stops"] - 1)

def text_path(x, y, s, key, h, fill="#1A1A1A", anchor="start"):
    """string s set in project font `key`, cap/em height h mm, baseline-ish at y (em box top = y - h)."""
    if not s: return ""
    gl = KL.set_line(key, s, h, tracking=h*0.04)
    if not gl: return ""
    b = KL.ink_bounds(gl); w = b[2] - b[0]
    dx = x - b[0] - (w if anchor == "end" else w/2 if anchor == "middle" else 0)
    dy = y - b[3]
    g = unary_union([affinity.translate(gg, dx, dy) for _, gg in gl])
    return f'<path d="{geom_to_path(g)}" fill="{fill}" fill-rule="evenodd"/>'

def mixed(x, y, parts, size=2.2, fill="#1A1A1A", w=400):
    """[(text, key|None), ...] on one line: Latin parts as SVG text, CJK parts as outlines. Returns svg + end x."""
    from sheet import t
    o = []; cx = x
    for s, key in parts:
        if key is None:
            o.append(t(cx, y, s, size, w, fill)); cx += len(s) * size * 0.50
        else:
            h = size * 1.05; gl = KL.set_line(key, s, h, tracking=h*0.04)
            if gl:
                b = KL.ink_bounds(gl); o.append(text_path(cx, y + 0.1*size, s, key, h, fill)); cx += (b[2] - b[0]) + size*0.3
    return "".join(o), cx

def load():
    CUR = json.load(open("dst_current.json")); ALL = json.load(open("dst_all.json")); META = json.load(open("scene_meta.json"))
    D = pickle.load(open("art_M.pkl", "rb"))
    return CUR, ALL, META, D

FONT_NAME = {"jp": "Zen Maru Gothic Black", "en": "Nunito ExtraBold (wght 820)", "cn": "Noto Sans SC (wght 720)", "kr": "Noto Sans KR (wght 560)"}
