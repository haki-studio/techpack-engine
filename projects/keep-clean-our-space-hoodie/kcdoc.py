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

from PIL import ImageFont
_FD = os.path.expanduser("~/.local/share/fonts")
_LF = {False: ImageFont.truetype(os.path.join(_FD, "LiberationSans-Regular.ttf"), 100), True: ImageFont.truetype(os.path.join(_FD, "LiberationSans-Bold.ttf"), 100)}
def mixed(x, y, parts, size=2.2, fill="#1A1A1A", w=400):
    """[(text, key|None), ...] on one line: Latin parts as SVG text, CJK parts as outlines. Returns svg + end x."""
    from sheet import t
    o = []; cx = x
    for s, key in parts:
        if key is None:
            o.append(t(cx, y, s, size, w, fill)); cx += _LF[w >= 600].getlength(s) / 100.0 * size * 1.03 + size * 0.4   # sheet font renders ~3 % wider; small fixed gap before the next (outlined) run
        else:
            h = size * 1.05; gl = KL.set_line(key, s, h, tracking=h*0.04)
            if gl:
                b = KL.ink_bounds(gl); o.append(text_path(cx + size*0.15, y + 0.1*size, s, key, h, fill)); cx += (b[2] - b[0]) + size*0.3
    return "".join(o), cx

def auto(x, y, s, size=2.2, fill="#1A1A1A", w=400):
    """one line of text, CJK / Hangul runs set as font outlines (jp / cn / kr picked per run)"""
    import re
    parts = []
    for seg in re.split(r"([\u3000-\u9fff\uac00-\ud7af]+)", s):
        if not seg: continue
        if re.match(r"[\u3000-\u9fff\uac00-\ud7af]", seg):
            if re.match(r"[\uac00-\ud7af]", seg): key = "kr"
            else:
                jp_ok = all(ord(c) in KL.font("jp").getBestCmap() for c in seg)
                key = "jp" if (jp_ok and not any(c in seg for c in "不要世界汚染污地球")) else "cn"
            parts.append((seg, key))
        else: parts.append((seg, None))
    return mixed(x, y, parts, size, fill, w)[0]

FOAM_WHERE = {"01": "badge 01 (JP)", "02": "badge 02 (EN)", "03": "badge 03 (CN text + dot ring)", "04": "the 04 KR oval ring"}
def foam_steps(r):
    """THE foam procedure of one written file (full or split section), read from its own stop list (review of PR #20:
    every page and the README print this, nothing else). Returns None for a file without puff, else dict(lay, tear,
    where, line) - lay = stop number to pause BEFORE; tear = stop to pause before, or None = after the last stop."""
    ps = r.get("per_stop", []); lay = r.get("foam_pause_before_stop")
    if not lay: return None
    els = sorted({e for p in ps if p.get("puff") for e in p.get("elements", [])})
    where = " + ".join(FOAM_WHERE.get(e, e) for e in els)
    tear = r.get("foam_tear_before_stop"); last = ps[-1]["stop"] if ps else None
    t_txt = f"STOP before stop {tear}: tear the foam away, then continue" if tear else f"after stop {last} (the last stop): unhoop, tear the loose foam away"
    return dict(lay=lay, tear=tear, last=last, where=where,
                line=f"STOP before stop {lay}: lay 3 mm black foam over {where}; {t_txt}.")

def load():
    CUR = json.load(open("dst_current.json")); ALL = json.load(open("dst_all.json")); META = json.load(open("scene_meta.json"))
    D = pickle.load(open("art_M.pkl", "rb"))
    return CUR, ALL, META, D

FONT_NAME = {"jp": "Zen Maru Gothic Bold", "en": "Nunito Black (wght 1000)", "cn": "Noto Sans SC (wght 800)", "kr": "Noto Sans KR (wght 450)"}
