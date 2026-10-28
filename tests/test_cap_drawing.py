"""Hat flats (engine/cap_pages.py) are drawn from the POM chart, so the DRAWING is measured here, not the code that
makes it (LESSONS: measure, don't eyeball).

- The brim is drawn at the chart's ratio: centre depth / width = E / F within 10 % on the TOP and UNDER-BRIM views
  (2026-10-28: the ASCE brim, E 7 x F 18 = 0.39, was drawn near-square, ~0.8).
- No dimension / callout label crosses an outline or seam on H3 (2026-10-28: 'G 2.5 cm' sat on the brim edge, 'head
  length' ran over the crown, 'head width' over the back seam), and the BACK 'C' dimension stops at the button."""
import math, re
import pytest

import capstyle as CS
import cap_pages as CP
from shapely.geometry import LineString, Polygon, Point
from shapely import affinity

CAPS = [k for k, s in CS.load().styles.items() if s.kind == "cap"]
OUTLINE_STROKES = {CP.LINE.lower(), "#1a1a1a", CP.STITCH.lower()}


def _num(s): return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", s)]


def paths(svg):
    """[(stroke, LineString)] for every outline / seam path and circle drawn in an outline colour"""
    out = []
    for m in re.finditer(r'<path d="([^"]+)"[^>]*?stroke="([^"]+)"', svg):
        d, stroke = m.groups()
        if stroke.lower() not in OUTLINE_STROKES: continue
        for sub in re.split(r"(?=M)", d):
            pts = list(zip(*[iter(_num(sub))] * 2))
            if len(pts) < 2: continue
            if "Z" in sub: pts = pts + [pts[0]]
            out.append((stroke, LineString(pts)))
    for m in re.finditer(r'<circle cx="([^"]+)" cy="([^"]+)" r="([^"]+)"[^>]*?stroke="([^"]+)"', svg):
        cx, cy, r, stroke = m.groups()
        if stroke.lower() in OUTLINE_STROKES:
            out.append((stroke, Point(float(cx), float(cy)).buffer(float(r)).exterior))
    return out


def labels(svg, box=None):
    """[(text, Polygon)] — each text's ink box (page mm), rotated like the text"""
    out = []
    for m in re.finditer(r'<text x="([^"]+)" y="([^"]+)"[^>]*font-size="([^"]+)" font-weight="(\d+)"[^>]*text-anchor="(\w+)"'
                         r'(?: transform="rotate\(([^ ]+) ([^ ]+) ([^)]+)\)")?>([^<]*)</text>', svg):
        x, y, size, w, anchor, ang, rx, ry, s = m.groups()
        x, y, size = float(x), float(y), float(size)
        wid = len(s) * size * (0.60 if int(w) >= 600 else 0.55)
        x0 = x - wid / 2 if anchor == "middle" else x - wid if anchor == "end" else x
        pg = Polygon([(x0, y - 0.72 * size), (x0 + wid, y - 0.72 * size), (x0 + wid, y + 0.2 * size), (x0, y + 0.2 * size)])
        if ang: pg = affinity.rotate(pg, float(ang), origin=(float(rx), float(ry)))
        if box and not Polygon([(box[0], box[1]), (box[0] + box[2], box[1]), (box[0] + box[2], box[1] + box[3]),
                                 (box[0], box[1] + box[3])]).contains(pg.centroid):
            continue
        out.append((s, pg))
    return out


def page_svg(key, code):
    return next(ss[0] for c, _, ss in CP.pages(key) if c == code)


def brim_ratio(pts, crown_front_x=None):
    """centre depth / width of a drawn brim outline (x, y): width = its y extent; depth = from the tip to the seam on
    the centre line (the brim's own inner edge, or the crown front when the brim runs under the crown)"""
    pg = Polygon(pts).buffer(0)
    ys = [p[1] for p in pts]; width = max(ys) - min(ys)
    tip = min(p[0] for p in pts)
    if crown_front_x is None:
        cut = pg.intersection(LineString([(tip - 10, 0), (max(p[0] for p in pts) + 10, 0)]))
        depth = cut.length
    else:
        depth = crown_front_x - tip
    return depth / width


def drawn_paths(view, g, *args):
    """run a view on a 1:1 un-flipped figure and return its filled paths in drawing order (geometry mm)"""
    o = []
    fg = CP.Fig(0, 0, 1.0, flip=False)
    view(o, g, fg, False, *args) if args else view(o, g, fg, False)
    return [list(zip(*[iter(_num(re.sub(r"Z", "", d)))] * 2)) for d in re.findall(r'<path d="([^"]+)" fill="(?!none)', "".join(o))]


@pytest.mark.parametrize("key", CAPS)
def test_brim_drawn_at_E_over_F(key):
    st = CS.load().get(key); g = CP.CapGeom(st)
    want = st.pom["E"].cm / st.pom["F"].cm
    under = drawn_paths(CP.view_under, g)[0]                      # first filled path = the brim
    got = brim_ratio(under)
    assert abs(got / want - 1) <= 0.10, f"{key} UNDER-BRIM brim depth/width {got:.2f}, chart E/F {want:.2f}"
    top = drawn_paths(CP.view_top, g)
    brim, crown = top[0], top[1]
    got = brim_ratio(brim, crown_front_x=min(p[0] for p in crown))
    assert abs(got / want - 1) <= 0.10, f"{key} TOP brim depth/width {got:.2f}, chart E/F {want:.2f}"


@pytest.mark.parametrize("key", CAPS)
def test_brim_not_near_square(key):
    """the whole flat brim (seam curve included) stays a crescent, never a square block"""
    g = CP.CapGeom(CS.load().get(key))
    pts = drawn_paths(CP.view_under, g)[0]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    assert (max(xs) - min(xs)) / (max(ys) - min(ys)) < 0.65


BOXES = {"FRONT": (12, 30, 90, 78), "SIDE": (104, 30, 90, 78), "BACK": (196, 30, 90, 78),
         "TOP": (12, 112, 90, 84), "UNDER-BRIM": (104, 112, 90, 84), "INSIDE": (196, 112, 90, 84)}


@pytest.mark.parametrize("key", CAPS)
def test_h3_labels_clear_of_outlines(key):
    svg = page_svg(key, "H3")
    lines = paths(svg)
    bad = []
    for name, box in BOXES.items():
        for s, pg in labels(svg, box):
            if s == name: continue
            hit = [st for st, ln in lines if ln.intersects(pg)]
            if hit: bad.append(f"{name}: '{s}'")
    assert not bad, f"{key}: labels on an outline / seam: {bad}"


def test_label_check_catches_an_overlap():
    """the guard itself: a label written across an outline is caught (prove-the-guard)"""
    svg = page_svg("asce-dad", "H3")
    crown = min((ln for _, ln in paths(svg) if ln.bounds[0] > 12 and ln.bounds[2] < 102 and 30 < ln.bounds[1] < 108),
                key=lambda ln: ln.bounds[0])                      # the FRONT crown's left outline
    x, y = crown.bounds[0], (crown.bounds[1] + crown.bounds[3]) / 2  # a label centred on it
    svg = svg.replace("</svg>", f'<text x="{x}" y="{y}" font-family="x" font-size="1.6" font-weight="700" fill="#000" '
                                f'text-anchor="middle">PROBE LABEL ACROSS THE CROWN</text></svg>')
    lines = paths(svg)
    probe = [pg for s, pg in labels(svg, BOXES["FRONT"]) if s.startswith("PROBE")]
    assert probe and any(ln.intersects(probe[0]) for _, ln in lines)


@pytest.mark.parametrize("key", CAPS)
def test_back_C_stops_at_the_button(key):
    """C is measured along the back seam to the button: its dimension ends at the button, never above the crown"""
    st = CS.load().get(key); g = CP.CapGeom(st)
    o = []; fg = CP.Fig(0, 0, 1.0, flip=True)
    CP.view_back(o, g, fg, True)
    svg = "".join(o)
    m = re.search(r'<line x1="([^"]+)" y1="([^"]+)" x2="([^"]+)" y2="([^"]+)"/>(?:<line[^>]*/>){2}</g><text[^>]*>C ', svg)
    assert m, "BACK has no C dimension"
    _, y1, _, y2 = map(float, m.groups())
    assert abs(min(y1, y2) - (-g.h)) < 0.5, f"C top at {min(y1, y2):.1f}, button at {-g.h:.1f}"
    assert abs(max(y1, y2) - 0) < 0.5
    assert "along the back seam" in svg
