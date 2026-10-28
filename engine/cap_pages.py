#!/usr/bin/env python3
"""Hat pack pages built from ONE catalogue style (families/cap/styles.yaml, engine/capstyle.py).

Every number on a page is read from the style (or the shared cap family) — nothing is typed here. Proposed values print
amber with "[proposed — confirm]" and every one of them is listed on F1. The flats are DRAWN from the POM chart (head
circumference -> crown base oval, crown depth -> crown height, brim length / width / curve -> brim, panel count -> seams),
so changing a POM changes the drawing; the chart governs, the drawing is a sketch.

  H1 style sheet (block, dies, construction callouts)    H2 points of measure + how to measure
  H3 flats: front / side / back / top / under-brim / inside   (knit: K1 knit spec page instead — no cut-and-sew flats)
  H4 embroidery positions + cap-frame limits             H5 construction + BOM
  F1 factory requests: the conflicts + every [proposed — confirm] value

  python3 engine/cap_pages.py <style-key> [--product "Name"] [--out DIR]   -> DIR/<key>_hatpack.pdf + DIR/pages/*.png
"""
import math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import sheet as SHT
from sheet import t, doc, SW, SH, INK, MUTED, RED, GREEN
from render import f
from family.spec import V, TAG, val, is_prop
from family.draw import PROP, ALT, GUIDE, wrap, para, vpara, path_d, dim, badge
from family.tee_pages import table
import capstyle as CS

CROWN = "#E9E4DA"; BRIM = "#D9D2C3"; MESH = "#EEF2F5"; LINE = "#2B2B2B"; STITCH = "#6E6E6E"


# ----------------------------------------------------------------------------- geometry (mm, y UP)
def ell_perim(a, b):
    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))


def _len(pts):
    return sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))


class CapGeom:
    """crown + brim of a cut-and-sew cap from its POMs. x = from the CF base edge towards the back (side view),
    y = lateral (top view, + = wearer's left), z = up. Every dimension comes from the style's chart."""

    def __init__(self, st):
        self.st = st
        fam = st.fam["block"]
        r = float(val(fam["head_ratio"]))
        A = st.pom["A"].mm
        self.b = A / ell_perim(r, 1.0); self.a = r * self.b        # head base oval semi-axes (front-back, side-side)
        self.L, self.W = 2 * self.a, 2 * self.b
        prof = str(val(st.get("crown_profile"))).lower()
        self.n = 3.0 if ("square" in prof or st.structured()) else 2.2
        self.xp = self.L * (0.42 if st.structured() else 0.47)     # button position from the front
        self.panels = st.num("panels")
        D = st.pom["D"].mm
        lo, hi = 20.0, 400.0                                         # crown height so the profile arc = crown depth D
        for _ in range(60):
            mid = (lo + hi) / 2
            if _len(self._profile(mid)) < D: lo = mid
            else: hi = mid
        self.h = (lo + hi) / 2
        self.E, self.F, self.G = st.pom["E"].mm, st.pom["F"].mm, st.pom["G"].mm
        self.B, self.C = st.pom["B"].mm, st.pom["C"].mm
        self.so_w = float(val(fam["strap_opening_w_cm"])) * 10; self.so_h = float(val(fam["strap_opening_h_cm"])) * 10
        self.rows = int(val(fam["brim_topstitch_rows"]))
        self.si = float(val(fam["brim_inner_depth_cm"])) * 10
        self._oval = self._oval_pts(720)
        self.seams = self._seam_fracs()

    def _profile(self, h, n=None, k=60):
        """side profile (x, z) from the CF base over the button to the CB base"""
        n = n or self.n; e = 2 / n; xp, L = self.xp, self.L
        fr = [(xp * (1 - math.cos(th) ** e), h * math.sin(th) ** e) for th in (i * math.pi / 2 / k for i in range(k + 1))]
        bk = [(xp + (L - xp) * math.sin(th) ** e, h * math.cos(th) ** e) for th in (i * math.pi / 2 / k for i in range(1, k + 1))]
        return fr + bk

    def profile(self): return self._profile(self.h)

    def _oval_pts(self, k):
        """base oval, from CF (x=0, y=0) round the wearer's left (+y) back to CF; with cumulative arc fraction"""
        pts = [(self.a - self.a * math.cos(2 * math.pi * i / k), self.b * math.sin(2 * math.pi * i / k)) for i in range(k + 1)]
        cum = [0.0]
        for p, q in zip(pts, pts[1:]): cum.append(cum[-1] + math.dist(p, q))
        return pts, [c / cum[-1] for c in cum], cum[-1]

    def at(self, frac):
        """point on the base oval at a fraction of the perimeter from CF (+ = wearer's left)"""
        pts, cum, _ = self._oval
        frac %= 1.0
        for i in range(1, len(cum)):
            if cum[i] >= frac:
                u = (frac - cum[i - 1]) / ((cum[i] - cum[i - 1]) or 1)
                return (pts[i - 1][0] + u * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + u * (pts[i][1] - pts[i - 1][1]))
        return pts[-1]

    def _seam_fracs(self):
        """crown seams as perimeter fractions; panel base widths J/K/M are used when charted, else equal panels
        (5-panel: the front panel = two 6-panel fronts)"""
        P = self._oval[2]
        pom = self.st.pom
        if self.panels == 6:
            if all(c in pom for c in "JKM"):
                j, k = pom["J"].mm / P, pom["K"].mm / P
                return [0.0, j, j + k, 0.5, 1 - j - k, 1 - j]
            return [0.0, 1 / 6, 2 / 6, 0.5, 4 / 6, 5 / 6]
        if all(c in pom for c in "JKM"):
            j, k = pom["J"].mm / P / 2, pom["K"].mm / P
            return [j, j + k, 0.5, 1 - j - k, 1 - j]
        return [1 / 6, 2 / 6, 0.5, 4 / 6, 5 / 6]

    def brim_ends(self):
        """brim ends (x, ±y): F apart straight across (POM F), set back behind CF by the inner (seam) curve depth"""
        return (self.si, self.F / 2), (self.si, -self.F / 2)

    def brim_poly(self, k=60):
        """brim outline (x, y), the same seen from above and laid flat under the brim: centre depth = E (crown seam at
        CF to the tip), width = F (end to end), so it is drawn at the chart's E/F. Inner (seam) edge = a curve from
        one end through CF to the other; outer edge = a rounded D from end to end through the tip at x = -E."""
        si, F2, E = self.si, self.F / 2, self.E
        inner = [(si * u * u, F2 * u) for u in (-1 + 2 * i / k for i in range(k + 1))]
        e = 2 / 2.6
        outer = []
        for i in range(k + 1):
            th = math.pi / 2 - math.pi * i / k                   # +y end -> tip -> -y end
            c, s = math.cos(th), math.sin(th)
            outer.append((si - (E + si) * abs(c) ** e, F2 * math.copysign(abs(s) ** e, s)))
        return inner + outer[1:-1]

    def brim_outer(self, k=60):
        """the outer (free) edge alone, end to end through the tip — the topstitch rows follow it"""
        return self.brim_poly(k)[k + 1:]

    def front_outline(self, w2=None, k=60):
        """crown seen from the front (y, z): superellipse half from the base width to the crown height"""
        w2 = w2 or self.b; e = 2 / self.n
        return [(w2 * math.copysign(abs(math.cos(th)) ** e, math.cos(th)), self.h * math.sin(th) ** e)
                for th in (math.pi * i / k for i in range(k + 1))]


class BucketGeom:
    """bucket hat: head oval (A), crown band height B, top oval length T, all-round brim width E (sloped 30 deg)"""
    def __init__(self, st):
        fam = st.fam["block"]; r = float(val(fam["head_ratio"]))
        self.b = st.pom["A"].mm / ell_perim(r, 1.0); self.a = r * self.b
        self.Bh = st.pom["B"].mm; self.T = st.pom["T"].mm; self.E = st.pom["E"].mm
        self.ta = self.T / 2; self.tb = self.ta / r
        self.ang = math.radians(30)
        self.rows = int(val(fam["brim_topstitch_rows"]))


# ----------------------------------------------------------------------------- page helpers
def foot(st, product):
    fam = st.fam
    return (f"HAKI STUDIOS · {product or st.name} · hat style {st.key} ({st.name}) · cap family {val(fam.get('rev'))} · "
            f"{val(fam.get('date'))}")


def H(st, product, title, sub, page):
    SHT.FOOT = foot(st, product)
    return SHT.header(title, sub, page)


def vtxt(v):
    """V -> display text (lists as 'a x b')"""
    if isinstance(v, V) and isinstance(v.v, list):
        return V(" x ".join(f"{float(val(x)):g}" for x in v.v), v.proposed, v.source, v.note, v.path)
    return v


def sline(o, x, y, label, v, width=150, lsize=1.7, vsize=1.75, lw=34):
    """label + value (amber if proposed) + its source / note in grey; returns y below"""
    v = vtxt(v)
    o.append(t(x, y, label, lsize, 400, MUTED))
    yy = vpara(o, x + lw, y, v, width - lw, vsize, vsize * 1.5)
    extra = (v.note if v.proposed else v.source) if isinstance(v, V) else None
    if extra: yy = para(o, x + lw, yy, extra, width - lw, 1.3, 2.0, 400, MUTED)
    return yy + 0.9


class Fig:
    """geometry mm -> page mm. flip=True: z up on the page"""
    def __init__(self, ox, oy, s, flip=True): self.ox, self.oy, self.s, self.flip = ox, oy, s, flip
    def P(self, p): return (self.ox + p[0] * self.s, self.oy + (-p[1] if self.flip else p[1]) * self.s)
    def d(self, pts, close=True): return path_d([self.P(p) for p in pts], close)


def poly(o, fg, pts, fill, stroke=LINE, sw=0.3, close=True, dash=None, op=1.0):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    o.append(f'<path d="{fg.d(pts, close)}" fill="{fill if close else "none"}" fill-opacity="{op}" stroke="{stroke}" '
             f'stroke-width="{sw}" stroke-linejoin="round"{da}/>')


def curve(o, fg, pts, stroke=STITCH, sw=0.16, dash="0.7 0.5"):
    poly(o, fg, pts, "none", stroke, sw, False, dash)


def bez(p0, p1, p2, k=24):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]) for u in (i / k for i in range(k + 1))]


def label(o, x, y, s, size=1.9):
    o.append(t(x, y, s, size, 700, INK, "middle"))


def pom_lab(st, c):
    p = st.pom[c]
    return f"{c} {p.cm:g} cm" + (" *" if p.proposed else "")


# ----------------------------------------------------------------------------- the six views (cap)
def view_side(o, g, fg, dims=True, emb=None):
    st = g.st
    pr = g.profile()
    poly(o, fg, pr + [(g.L, 0)], CROWN)
    # brim seen from the side: tip in front, ends wrap back to the brim end x and droop by the curve G
    (xe, _), _ = g.brim_ends()
    tip = (-g.E * math.cos(math.radians(10)), -g.E * math.sin(math.radians(10)))
    lower = bez(tip, (xe * 0.2, -g.G * 1.6), (xe, -2))
    poly(o, fg, [(0, 0), tip] + lower[1:] + [(xe, 0)], BRIM)
    for fr in g.seams:                                               # near-side seams (wearer's left = +y) to the button
        x, y = g.at(fr)
        if y >= -1e-6 and 0 < fr < 0.5 + 1e-9:
            curve(o, fg, bez((x, 0), (x + (g.xp - x) * 0.15, g.h * 0.8), (g.xp, g.h)), LINE, 0.22, None)
    o.append(f'<circle cx="{f(fg.P((g.xp, g.h))[0])}" cy="{f(fg.P((g.xp, g.h))[1])}" r="{f(max(0.6, 8 * fg.s))}" fill="{BRIM}" stroke="{LINE}" stroke-width="0.25"/>')
    if g.st.closure_kind() != "none":                                # strap opening edge at the back
        poly(o, fg, bez((g.L - 2, 0), (g.L - 1, g.so_h * 0.6), (g.L - g.so_w * 0.35, g.so_h)), "none", LINE, 0.2, False)
    if dims:
        o.append(dim(fg.P((g.L + 6, 0)), fg.P((g.L + 6, g.h)), 0, f"crown height {g.h / 10:.1f} cm (from D)", 1.4, MUTED))
        o.append(dim(fg.P(tip), fg.P((0, 0)), -3, pom_lab(st, "E"), 1.6))
        tx, tz = tip                                                 # G beside the tip, clear of the brim edge
        o.append(dim(fg.P((tx - 3, tz)), fg.P((tx - 3, tz - g.G)), 1.5, pom_lab(st, "G"), 1.5))
        mid = pr[len(pr) // 2]
        o.append(t(fg.P(mid)[0], fg.P(mid)[1] - max(0.6, 8 * fg.s) - 1.6, f"D {st.pom['D'].cm:g} cm over the top" + (" *" if st.pom['D'].proposed else ""), 1.6, 700, PROP if st.pom['D'].proposed else INK, "middle"))


def view_front(o, g, fg, dims=True):
    st = g.st
    ol = g.front_outline()
    poly(o, fg, ol, CROWN)
    for fr in g.seams:                                               # seams on the front half
        x, y = g.at(fr)
        if x < g.a:
            curve(o, fg, bez((y, 0), (y * 0.95, g.h * 0.75), (0, g.h)), LINE, 0.22, None)
    if g.panels == 6: curve(o, fg, [(0, 0), (0, g.h)], LINE, 0.22, None)
    o.append(f'<circle cx="{f(fg.P((0, g.h))[0])}" cy="{f(fg.P((0, g.h))[1])}" r="{f(max(0.6, 8 * fg.s))}" fill="{BRIM}" stroke="{LINE}" stroke-width="0.25"/>')
    (_, ye), _ = g.brim_ends()
    band = bez((-ye, -g.G * 0.9), (0, g.G * 0.5), (ye, -g.G * 0.9))
    lowr = bez((ye, -g.G * 0.9 - 6), (0, -6), (-ye, -g.G * 0.9 - 6))
    poly(o, fg, band + lowr, BRIM)
    if dims:
        o.append(dim(fg.P((-ye, -g.G - 14)), fg.P((ye, -g.G - 14)), 0, pom_lab(st, "F") + " (flat)", 1.6))
        o.append(dim(fg.P((g.b * 0.5, 0)), fg.P((g.b * 0.5, g.B)), 0, pom_lab(st, "B"), 1.6))
        o.append(f'<line x1="{f(fg.P((g.b * 0.5 - 4, g.B))[0])}" y1="{f(fg.P((0, g.B))[1])}" x2="{f(fg.P((g.b * 0.5 + 4, g.B))[0])}" y2="{f(fg.P((0, g.B))[1])}" stroke="{GUIDE}" stroke-width="0.2"/>')


def view_back(o, g, fg, dims=True):
    st = g.st
    ol = g.front_outline()
    poly(o, fg, ol, MESH if "mesh" in str(val(st.get("structure"))).lower() else CROWN)
    for fr in g.seams:
        x, y = g.at(fr)
        if x > g.a - 1e-6 or abs(fr - 0.5) < 1e-9:
            curve(o, fg, bez((-y, 0), (-y * 0.95, g.h * 0.75), (0, g.h)), LINE, 0.22, None)
    ck = st.closure_kind()
    if ck != "none":
        w2, hh = g.so_w / 2, g.so_h
        arch = [(w2 * math.cos(th), hh * math.sin(th)) for th in (math.pi * i / 30 for i in range(31))]
        poly(o, fg, arch, "#FFFFFF")
        poly(o, fg, [(-w2 - 12, 0), (w2 + 12, 0), (w2 + 12, 16), (-w2 - 12, 16)], BRIM, LINE, 0.25)
        if ck == "snap":
            for i in range(6):
                cx = -w2 - 6 + i * (g.so_w + 12) / 5
                o.append(f'<circle cx="{f(fg.P((cx, 8))[0])}" cy="{f(fg.P((cx, 8))[1])}" r="{f(2.2 * fg.s)}" fill="#FFFFFF" stroke="{LINE}" stroke-width="0.15"/>')
        else:
            sx = w2 * 0.5
            poly(o, fg, [(sx, -2), (sx + 18, -2), (sx + 18, 18), (sx, 18)], "#BFBFBF", LINE, 0.22)
    o.append(f'<circle cx="{f(fg.P((0, g.h))[0])}" cy="{f(fg.P((0, g.h))[1])}" r="{f(max(0.6, 8 * fg.s))}" fill="{BRIM}" stroke="{LINE}" stroke-width="0.25"/>')
    if dims:
        # C runs ALONG the back seam (base -> button over the curved back), so its straight projection is the crown
        # height: dimension base -> button, outside the crown, and say it is measured along the seam
        off = (g.b + 8) * fg.s
        o.append(dim(fg.P((0, g.h)), fg.P((0, 0)), off, pom_lab(st, "C") + " along the back seam", 1.5))
        if ck != "none":
            H_ = st.pom["H"]
            o.append(dim(fg.P((-g.so_w / 2 - 12, -6)), fg.P((g.so_w / 2 + 12, -6)), 0,
                         f"strap: H {H_.cm:g} cm effective" + (" *" if H_.proposed else ""), 1.5))


def view_top(o, g, fg, dims=True):
    st = g.st
    pts, _, _ = g._oval
    poly(o, fg, brim_drawn(g, "top"), BRIM)
    poly(o, fg, pts, CROWN)
    for fr in g.seams:
        x, y = g.at(fr)
        curve(o, fg, bez((x, y), ((x + g.xp) / 2, y * 0.55), (g.xp, 0)), LINE, 0.22, None)
    if g.panels == 6: curve(o, fg, [(0, 0), (g.xp, 0)], LINE, 0.22, None)
    o.append(f'<circle cx="{f(fg.P((g.xp, 0))[0])}" cy="{f(fg.P((g.xp, 0))[1])}" r="{f(max(0.6, 8 * fg.s))}" fill="{BRIM}" stroke="{LINE}" stroke-width="0.25"/>')
    for i, fr in enumerate(g.seams):                                 # eyelets: mid-panel, upper third
        nx = g.seams[(i + 1) % len(g.seams)] + (1 if i == len(g.seams) - 1 else 0)
        if g.panels == 5 and (fr > 0.8 and nx > 1.0): continue        # the wide 5-panel front has none
        mx, my = g.at((fr + nx) / 2)
        ex, ey = mx + (g.xp - mx) * 0.62, my * 0.38
        o.append(f'<circle cx="{f(fg.P((ex, ey))[0])}" cy="{f(fg.P((ex, ey))[1])}" r="{f(4 * fg.s)}" fill="#FFFFFF" stroke="{LINE}" stroke-width="0.18"/>')
    if dims:
        top = max(g.b, g.F / 2)                                      # labels sit OUTSIDE the outlines
        o.append(dim(fg.P((0, -top)), fg.P((g.L, -top)), -2.5, f"head length {g.L / 10:.1f} cm (from A)", 1.4, MUTED))
        o.append(dim(fg.P((g.L, -g.b)), fg.P((g.L, g.b)), -3, f"head width {g.W / 10:.1f} cm", 1.4, MUTED))
        bx, by = fg.P((g.a, g.b))
        o.append(t(bx, by + 3.4, pom_lab(st, "A") + " round", 1.6, 700, PROP if st.pom["A"].proposed else INK, "middle"))


def brim_rows(g):
    from shapely.geometry import Polygon, LineString
    bp = Polygon(g.brim_poly()).buffer(0)
    outer = LineString(g.brim_outer())
    gap = min(5.0, (g.E - 4) / (g.rows + 0.5))                     # rows fit inside the brim's centre depth E
    rows = []
    for k in range(1, g.rows + 1):
        try: ln = outer.offset_curve(gap * k)                        # + = left of the +y -> -y run = inwards
        except Exception: continue
        ln = ln.intersection(bp.buffer(-1.5))
        for gg in getattr(ln, "geoms", [ln]):
            if gg.length > 10: rows.append(list(gg.coords))
    return rows


def brim_drawn(g, view="under"):
    """the brim outline exactly as a view draws it (tests measure it: centre depth / width = E / F).
    under = laid flat: the brim alone. top = on the cap: the same brim, its seam edge carried round under the crown
    to the head sides (the crown is drawn over it), so no gap shows between the brim and the crown."""
    if view == "under": return g.brim_poly()
    from shapely.geometry import MultiPoint
    front = [p for p in g._oval[0] if p[0] <= g.a * 0.6]
    return list(MultiPoint(g.brim_poly() + front).convex_hull.exterior.coords)[:-1]


def view_under(o, g, fg, dims=True):
    st = g.st
    poly(o, fg, brim_drawn(g), BRIM)
    rows = brim_rows(g)
    for r in rows: curve(o, fg, r)
    (xe, ye), _ = g.brim_ends()
    if dims:                                                         # every label outside the brim
        o.append(dim(fg.P((xe, -ye)), fg.P((xe, ye)), -3, pom_lab(st, "F") + " end to end", 1.6))
        o.append(dim(fg.P((-g.E, 0)), fg.P((0, 0)), (ye + 5) * fg.s, pom_lab(st, "E") + " at the centre", 1.6))
    X, Y = fg.P((-g.E * 0.35, -ye))
    o.append(t(X, Y - 2.5, f"{len(rows)} topstitch rows", 1.4, 700,
               PROP if is_prop(st.fam["block"]["brim_topstitch_rows"]) else INK, "middle"))


def view_inside(o, g, fg, dims=True):
    """looking up into the crown: sweatband ring, inner label at CF, seam tape over every seam, inside character"""
    st = g.st
    pts, _, _ = g._oval
    poly(o, fg, pts, "#FFFFFF")
    inner = [(g.a + (x - g.a) * 0.86, y * 0.86) for x, y in pts]
    poly(o, fg, pts + inner[::-1], "#CFC8B8", LINE, 0.2)
    for fr in g.seams:
        x, y = g.at(fr)
        poly(o, fg, [(x * 0.97 + g.a * 0.03, y * 0.86), (g.xp, 0)], "none", "#1A1A1A", 0.9, False)
    if g.panels == 6: poly(o, fg, [(g.a * 0.14, 0), (g.xp, 0)], "none", "#1A1A1A", 0.9, False)
    lx = g.a * 0.07
    poly(o, fg, [(lx - 3, -20), (lx + 5, -20), (lx + 5, 20), (lx - 3, 20)], "#FFFFFF", LINE, 0.2)
    cx = g.xp * 0.5
    poly(o, fg, [(cx - 12, -14), (cx + 12, -14), (cx + 12, 14), (cx - 12, 14)], "#EAF3FB", GUIDE, 0.22, dash="1 0.6")
    if not st.structured():
        poly(o, fg, [(g.a * 0.16, -g.b * 0.55), (g.xp * 0.95, -g.b * 0.45), (g.xp * 0.95, g.b * 0.45), (g.a * 0.16, g.b * 0.55)], "none", "#0A84D6", 0.18, dash="0.4 0.4")
    # labels outside the crown, each with a thin leader to what it names
    sx, sy = g.at(g.seams[1] if g.panels == 5 else g.seams[2])     # a point on a taped seam, lower half
    tape = (sx + (g.xp - sx) * 0.35, sy * 0.86 * 0.65)
    ring = g.at(0.62); ring = (g.a + (ring[0] - g.a) * 0.93, ring[1] * 0.93)
    labs = [((lx + 1, 0), (-14, -g.b * 0.75), "label"), ((cx, -14), (cx, -g.b - 10), "character"),
            (tape, (tape[0], g.b + 10), "seam tape"), (ring, (ring[0] + 10, -g.b - 10), "sweatband")]
    for p, q, s in labs:
        (x0, y0), (x1, y1) = fg.P(p), fg.P(q)
        o.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1 + (1.0 if y1 < y0 else -1.6))}" stroke="{MUTED}" stroke-width="0.12"/>')
        o.append(t(x1, y1 + (0 if y1 < y0 else 0.8), s, 1.35, 600, MUTED, "middle"))


# ----------------------------------------------------------------------------- bucket views
def bucket_views(o, st, boxes):
    g = BucketGeom(st)
    out = {}
    def fit(box, w, h):
        x, y, bw, bh = box; s = min((bw - 8) / w, (bh - 12) / h); return Fig(x + bw / 2, y + bh - 8, s)
    br = g.E * math.cos(g.ang); drop = g.E * math.sin(g.ang)
    for name in ("FRONT", "SIDE", "BACK"):
        half = g.b if name != "SIDE" else g.a; top = g.tb if name != "SIDE" else g.ta
        fg = fit(boxes[name], 2 * (half + br) + 10, g.Bh + drop + 10); fg.oy -= drop * fg.s
        poly(o, fg, [(-half - br, -drop), (-half, 0), (half, 0), (half + br, -drop)], BRIM)
        poly(o, fg, [(-half, 0), (-top, g.Bh), (top, g.Bh), (half, 0)], CROWN)
        for k in range(1, g.rows + 1):
            u = k / (g.rows + 1)
            curve(o, fg, [(-half - br * u, -drop * u), (half + br * u, -drop * u)])
        o.append(dim(fg.P((half + 4, 0)), fg.P((top + 4, g.Bh)), -3, f"B {st.pom['B'].cm:g} cm" + (" *" if st.pom['B'].proposed else ""), 1.5))
        # drawn tip -> crown so dim() puts the label below the line, clear of the brim edge
        o.append(dim(fg.P((-half - br, -drop - 4)), fg.P((-half, -drop - 4)), 0, f"E {st.pom['E'].cm:g} cm" + (" *" if st.pom['E'].proposed else ""), 1.5))
        out[name] = fg
    for name, scale in (("TOP", 1.0), ("UNDER-BRIM", 1.0), ("INSIDE", 1.0)):
        x, y, bw, bh = boxes[name]; R = g.a + br
        s = min((bw - 8) / (2 * R), (bh - 12) / (2 * (g.b + br))); fg = Fig(x + bw / 2, y + bh / 2 - 2, s, flip=False)
        ell = lambda A_, B_: [(A_ * math.cos(2 * math.pi * i / 90), B_ * math.sin(2 * math.pi * i / 90)) for i in range(90)]
        poly(o, fg, ell(g.a + br, g.b + br), BRIM)
        if name == "TOP":
            poly(o, fg, ell(g.ta, g.tb), CROWN)
            o.append(dim(fg.P((-g.ta, 0)), fg.P((g.ta, 0)), -3, f"T {st.pom['T'].cm:g} cm" + (" *" if st.pom['T'].proposed else ""), 1.5))
        else:
            poly(o, fg, ell(g.a, g.b), "#FFFFFF" if name == "INSIDE" else BRIM)
            for k in range(1, g.rows + 1):
                u = k / (g.rows + 1); curve(o, fg, ell(g.a + br * u, g.b + br * u) + [ell(g.a + br * u, g.b + br * u)[0]])
            if name == "INSIDE":
                poly(o, fg, ell(g.a * 0.88, g.b * 0.88), "none", LINE, 0.2)
                o.append(t(fg.P((0, 0))[0], fg.P((0, 0))[1], f"A {st.pom['A'].cm:g} cm sweatband" + (" *" if st.pom['A'].proposed else ""), 1.5, 700, INK, "middle"))
        out[name] = fg
    return out


# ----------------------------------------------------------------------------- pages
INDEX_CAP = [("H1", "Style sheet: block, dies, construction"), ("H2", "Points of measure + how to measure"),
             ("H3", "Flats: front, side, back, top, under-brim, inside"), ("H4", "Embroidery positions + cap-frame limits"),
             ("H5", "Construction + bill of materials"), ("F1", "Factory requests + open questions")]
INDEX_KNIT = [("H1", "Style sheet"), ("H2", "Points of measure + how to measure"), ("K1", "Knit spec (no cut-and-sew flats)"),
              ("H4", "Embroidery positions"), ("H5", "Construction + bill of materials"), ("F1", "Factory requests + open questions")]

FIELDS = [("factory", "Factory"), ("crown_die", "Crown die"), ("brim_die", "Brim die"), ("panels", "Crown panels"),
          ("structure", "Structure"), ("crown_profile", "Crown profile"), ("brim", "Brim"), ("closure", "Closure"),
          ("size", "Size"), ("mesh", "Mesh")]


def p_style(st, product):
    o = H(st, product, f"{(product or st.name).upper()} — HAT STYLE {st.key}",
          f"Block: {st.name} · {st.raw['status']} · amber = proposed by Haki, please confirm (all on F1)", "H1")
    y = 33
    if st.raw.get("nda"):
        o.append(t(12, y, st.raw["nda"], 1.9, 700, RED)); y += 4.5
    for k, lab in FIELDS:
        if k in st.t: y = sline(o, 12, y, lab, st.t[k], 132, lw=30)
    if st.kind == "knit":
        for k, v in st.t["knit"].items(): y = sline(o, 12, y, f"Knit · {k}", v, 132, lw=30)
    y += 1.5
    o.append(t(12, y, "PRODUCTS ON THIS STYLE", 2.0, 700)); y += 3.8
    prods = st.raw.get("products") or []
    if not prods: o.append(t(14, y, "none yet (sample only)", 1.6, 400, MUTED)); y += 3
    for p in prods:
        y = para(o, 14, y, p["name"] + (f"  {TAG} {p['proposed']}" if p.get("proposed") else ""), 128, 1.55, 2.4,
                 700 if p.get("proposed") else 400, PROP if p.get("proposed") else INK) + 0.2
    # right: side view with construction callouts (cap / bucket), contents
    o.append(t(160, 33, "CONTENTS", 2.2, 700)); yi = 37.5
    for c, ttl in (INDEX_KNIT if st.kind == "knit" else INDEX_CAP):
        o.append(t(160, yi, c, 1.6, 700)); o.append(t(168, yi, ttl, 1.6)); yi += 3.2
    if st.kind == "cap":
        g = CapGeom(st)
        s = min(110 / (g.L + g.E + 30), 70 / (g.h + g.G + 20)); fg = Fig(178 + (g.E + 10) * s, 140, s)
        view_side(o, g, fg, dims=False)
        fam = st.fam
        calls = [((g.xp, g.h), "button", fam["button"]["spec"]), ((g.xp * 0.55, g.h * 0.93), "eyelets", fam["eyelets"]["spec"]),
                 ((g.L * 0.75, g.h * 0.6), "seam tape inside", fam["seam_tape"]["spec"]), ((g.L * 0.4, 6), "sweatband + label", fam["sweatband"]["spec"]),
                 ((-g.E * 0.5, -3), "brim", st.t["brim"]), ((g.L - 4, 12), "closure", st.t["closure"]),
                 ((g.xp * 0.4, g.h * 0.45), "front", V("mesh guard behind the embroidery") if not st.structured() else st.t["structure"])]
        ly = 152
        for i, (p, nm, v) in enumerate(calls, 1):
            X, Y = fg.P(p); o.append(badge(X, Y, i, 1.6, 1.5))
            o.append(t(160, ly, f"{i}", 1.6, 700)); ly = vpara(o, 165, ly, V(f"{nm}: {val(v)}", is_prop(v)), 120, 1.5, 2.3) + 0.4
    o.append(t(160, SH - 14, "Sources: " + "; ".join(st.raw["sources"])[:190], 1.3, 400, MUTED))
    return o


def p_pom(st, product):
    o = H(st, product, "POINTS OF MEASURE — how to measure", f"{st.name} ({st.key}) · one size · cm · finished cap · amber = proposed (not recorded) → F1", "H2")
    rows = []
    pset = CS.load().pom_set(st.kind)
    ftol = st.fam["pom_tolerance_cm"]                              # family default: proposed, listed on F1
    for c, p in st.pom.items():
        src = (p.v.note if p.proposed else p.v.source) or ""
        tol = st.raw["pom"][c].get("tol") if isinstance(st.raw["pom"][c], dict) else None
        rows.append([c, p.name, p.how, V(f"{p.cm:g}", p.proposed, path=p.path), f"{p.cm / 2.54:.2f}",
                     V(f"{float(val(ftol)):g}", is_prop(ftol), path=ftol.path) if tol is None else f"{tol}", src])
    cols = [("", 0, 6), ("Point of measure", 7, 28), ("How to measure", 36, 70), ("cm", 107, 22), ("in", 130, 9), ("Tol ± cm", 140, 22), ("Source / note", 163, 110)]
    y = table(o, 12, 34, cols, rows, 1.6, 3.6)
    missing = [c for c, d in pset.items() if c not in st.pom]
    if missing:
        y = para(o, 12, y + 2, "Not charted for this style (optional): " + ", ".join(f"{c} {pset[c]['name']}" for c in missing)
                 + " — send them with the mould sheet.", 270, 1.5, 2.4, 600, PROP)
    y += 3
    fam = st.fam
    if st.kind == "cap":
        y = sline(o, 12, y, "Strap rule", fam["strap"]["rule"], 270, lw=26)
    y = sline(o, 12, y, "Size sheet", fam["sizes"]["range"], 270, lw=26)
    y = sline(o, 12, y, "One size", fam["sizes"]["caps"], 270, lw=26)
    y = sline(o, 12, y, "Tolerance", V(f"± {float(val(ftol)):g} cm on every row without its own", is_prop(ftol), ftol.source, ftol.note, ftol.path), 270, lw=26)
    para(o, 12, y + 1, "Every measurement is on the finished cap, strap / snap at its middle setting.", 270, 1.5, 2.4, 400, INK)
    return o


def p_flats(st, product):
    o = H(st, product, "FLATS — drawn from the POM chart", f"{st.name} · {st.num('panels') if st.kind == 'cap' else ''}{' crown panels · ' if st.kind == 'cap' else ''}"
          "letters = POM codes (H2); * = proposed value; sketch proportions come from the chart, the chart governs", "H3")
    boxes = {"FRONT": (12, 30, 90, 78), "SIDE": (104, 30, 90, 78), "BACK": (196, 30, 90, 78),
             "TOP": (12, 112, 90, 84), "UNDER-BRIM": (104, 112, 90, 84), "INSIDE": (196, 112, 90, 84)}
    for nm, (x, y, w, h) in boxes.items():
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="#DDD" stroke-width="0.2"/>')
        o.append(t(x + 2, y + 4, nm, 1.9, 700))
    if st.kind == "bucket":
        bucket_views(o, st, boxes); return o
    g = CapGeom(st)
    def fig(box, w, h, cx, cy, flip=True):
        x, y, bw, bh = box; s = min((bw - 14) / w, (bh - 18) / h)
        return Fig(x + bw / 2 - cx * s, y + 8 + (bh - 8) / 2 + (cy * s if flip else -cy * s), s, flip)
    W2 = max(g.b, g.F / 2) + 6
    view_front(o, g, fig(boxes["FRONT"], 2 * W2, g.h + g.G + 26, 0, (g.h - g.G - 22) / 2))
    view_side(o, g, fig(boxes["SIDE"], g.L + g.E + 22, g.h + g.G + 14, (g.L - g.E) / 2, (g.h - g.G) / 2))
    view_back(o, g, fig(boxes["BACK"], 2 * W2, g.h + 30, 0, (g.h - 12) / 2))
    TW = 2 * max(g.b, g.F / 2)
    view_top(o, g, fig(boxes["TOP"], g.L + g.E + 30, TW + 40, (g.L - g.E) / 2 + 6, 6, False))
    view_under(o, g, fig(boxes["UNDER-BRIM"], g.E + g.si + 40, g.F + 50, (g.si - g.E) / 2 + 8, 4, False))
    view_inside(o, g, fig(boxes["INSIDE"], g.L + 40, g.W + 40, g.a - 6, 0, False))
    return o


def p_knit(st, product):
    o = H(st, product, "KNIT SPEC — cuffed beanie (knitted, not cut-and-sew)", f"{st.name} · no flats: knitted tube with a fold-up cuff · amber = proposed → F1", "K1")
    Wv, Lv, Cv = st.pom["W"], st.pom["L"], st.pom["C"]
    s = min(110 / (Wv.mm + 40), 140 / (Lv.mm + 30)); fg = Fig(70, 180, s)
    w2 = Wv.mm / 2; Lh = Lv.mm; c = Cv.mm
    body = [(-w2, c)] + [(w2 * math.cos(th) * 0.98, Lh - 30 + 30 * math.sin(th)) for th in (math.pi * i / 30 for i in range(31))][::-1] + [(w2, c)]
    body = [(-w2, c), (-w2, Lh - 30)] + [(-w2 * math.cos(th), Lh - 30 + 30 * math.sin(th) ** 0.6) for th in (math.pi / 2 * i / 15 for i in range(16))] + \
           [(w2 * math.sin(th), Lh - 30 + 30 * math.cos(th) ** 0.6) for th in (math.pi / 2 * i / 15 for i in range(16))] + [(w2, Lh - 30), (w2, c)]
    poly(o, fg, body, "#F3D9E2")
    for i in range(1, 14):                                       # knit wales (texture hint only)
        x = -w2 + i * Wv.mm / 14; curve(o, fg, [(x, c + 2), (x, Lh - 12)], "#C99AAB", 0.12, None)
    for k in (-0.5, 0.5, -0.16, 0.16):                           # 4-point crown decrease
        curve(o, fg, [(k * w2 * 1.6, Lh - 36), (0, Lh - 2)], "#9C6B7D", 0.16, "0.8 0.5")
    poly(o, fg, [(-w2 - 2, 0), (w2 + 2, 0), (w2 + 2, c), (-w2 - 2, c)], "#E8B9C9")
    for i in range(1, 22):
        x = -w2 + i * Wv.mm / 22; curve(o, fg, [(x, 1), (x, c - 1)], "#B07A8E", 0.12, None)
    o.append(dim(fg.P((-w2, -6)), fg.P((w2, -6)), 0, f"W {Wv.cm:g} cm flat" + (" *" if Wv.proposed else ""), 1.7))
    o.append(dim(fg.P((w2 + 8, 0)), fg.P((w2 + 8, Lh)), 0, f"L {Lv.cm:g} cm" + (" *" if Lv.proposed else ""), 1.7))
    o.append(dim(fg.P((-w2 - 8, 0)), fg.P((-w2 - 8, c)), 0, f"C {Cv.cm:g} cm" + (" *" if Cv.proposed else ""), 1.6))
    emb = st.raw.get("embroidery") or {}
    if "front" in emb:
        poly(o, fg, [(-25, c * 0.2), (25, c * 0.2), (25, c * 0.8), (-25, c * 0.8)], "#EAF3FB", GUIDE, 0.22, dash="1 0.6", op=0.8)
        o.append(t(fg.P((0, c / 2))[0], fg.P((0, c / 2))[1] + 0.5, "embroidery", 1.4, 700, GUIDE, "middle"))
    o.append(t(70, 190, "FRONT, laid flat, cuff folded", 1.9, 700, INK, "middle"))
    y = 34
    o.append(t(150, y, "KNIT", 2.2, 700)); y += 4.5
    for k, v in st.t["knit"].items(): y = sline(o, 150, y, k.capitalize(), v, 135, lw=22)
    y += 2; o.append(t(150, y, "MEASUREMENTS (cm)", 2.2, 700)); y += 4.5
    for c_, p in st.pom.items(): y = sline(o, 150, y, f"{c_} {p.name}", p.v, 135, lw=30)
    y += 2
    para(o, 150, y, "History: the January 2026 sample was rejected ('not looking like we wanted', 2026-01-28). Hearts cannot be "
                    "jacquarded — they are embroidered on the cuff (Emmie 2026-01-30).", 135, 1.5, 2.4, 600, INK)
    return o


POS_NAMES = {"front": "Front (centred)", "left_side": "Left side", "right_side": "Right side", "back": "Back (above the strap opening)",
             "inside_front": "Inside front", "under_brim": "Under the brim"}


def emb_rows(st):
    """[(pos, style w V|None, style h V|None, frame w V, frame h V, ok bool|None, note)]"""
    out = []
    for pos, e in (st.raw.get("embroidery") or {}).items():
        e = e or {}
        te = st.t["embroidery"][pos] if isinstance(st.t["embroidery"].get(pos), dict) else {}
        w, h = te.get("w_cm"), te.get("h_cm")
        fw, fh = st.frame(pos)
        ok = None
        if w is not None or h is not None:
            ok = (w is None or float(val(w)) <= float(val(fw))) and (h is None or float(val(h)) <= float(val(fh)))
        out.append((pos, w, h, fw, fh, ok, e.get("note", "")))
    return out


def p_embroidery(st, product):
    o = H(st, product, "EMBROIDERY POSITIONS + CAP-FRAME LIMITS",
          f"{st.name} · blue dashed = largest art box the cap frame sews (proposed until Emmie confirms) · solid = this style's size", "H4")
    fam = st.fam["embroidery"]
    rows = []
    for pos, w, h, fw, fh, ok, note in emb_rows(st):
        size = " x ".join(x for x in (f"{val(w):g} wide" if w is not None else "", f"{val(h):g} high" if h is not None else "") if x) or "per design"
        sv = V(size, is_prop(w) or is_prop(h))
        lim = V(f"{float(val(fw)):g} x {float(val(fh)):g}", is_prop(fw) or is_prop(fh))
        chk = "—" if ok is None else ("fits" if ok else "OVER THE FRAME LIMIT")
        rows.append([POS_NAMES[pos], sv, lim, chk, note or ""])
    cols = [("Position", 0, 40), ("This style (cm)", 42, 34), ("Cap-frame max w x h (cm)", 78, 40), ("Check", 120, 30), ("Note", 152, 120)]
    y = table(o, 12, 34, cols, rows, 1.6, 3.6)
    for r in rows:
        if r[3] == "OVER THE FRAME LIMIT":
            o.append(t(12, y + 1, f"{r[0]}: art is bigger than the cap frame sews — make it smaller or ask Emmie.", 1.8, 700, RED)); y += 3.5
    y += 3
    for lab, k in (("Method", "method"), ("Side + back", "side_back_stitch_max"), ("Back logo", "back_logo_width_cm"),
                   ("Colours", "max_colours"), ("Stitch files", "stitch_files")):
        v = fam[k]
        if k == "side_back_stitch_max": v = V(f"under {val(v):,} stitches each", is_prop(v), v.source, v.note, v.path)
        if k == "back_logo_width_cm": v = V(f"~{val(v):g} cm wide, centred", is_prop(v), v.source, v.note, v.path)
        y = sline(o, 12, y, lab, v, 140, lw=22)
    y = sline(o, 12, y, "Unstructured", st.fam["mesh_guard"]["spec"], 140, lw=22)
    y = sline(o, 12, y, "Corduroy", st.fam["backing_corduroy"]["spec"], 140, lw=22)
    if st.kind == "cap":                                       # three views in a row under the text, one scale
        g = CapGeom(st)
        s_ = min(84 / (g.L + g.E + 20), 84 / (2 * max(g.b, g.F / 2) + 12), 58 / (g.h + g.G + 16))
        base = 112 + g.h * s_ + 6                               # crown tops just under the text (text ends ~y 105)
        figs = {"front": Fig(60, base, s_), "side": Fig(150 - (g.L - g.E) / 2 * s_, base, s_), "back": Fig(240, base, s_)}
        view_front(o, g, figs["front"], dims=False)
        view_side(o, g, figs["side"], dims=False)
        view_back(o, g, figs["back"], dims=False)
        for nm, x in (("FRONT", 60), ("SIDE (wearer's left; right side = mirror)", 150), ("BACK", 240)):
            o.append(t(x, base + (g.G + 22) * s_ + 4, nm, 1.7, 700, INK, "middle"))
        where = {"front": ("front", (0, g.h * 0.45)), "left_side": ("side", (g.L * 0.5, g.h * 0.35))}
        for pos, w, h, fw, fh, ok, note in emb_rows(st):
            bw, bh = float(val(fw)) * 10, float(val(fh)) * 10
            if pos == "back":                                  # centred above the strap opening
                view, c = "back", (0, (g.so_h if st.closure_kind() != "none" else 0) + 4 + bh / 2)
            elif pos in where: view, c = where[pos]
            else: continue
            fgx = figs[view]
            x0, y0 = fgx.P((c[0] - bw / 2, c[1] + bh / 2)); x1, y1 = fgx.P((c[0] + bw / 2, c[1] - bh / 2))
            o.append(f'<rect x="{f(x0)}" y="{f(y0)}" width="{f(x1 - x0)}" height="{f(y1 - y0)}" fill="#EAF3FB" fill-opacity="0.5" stroke="{GUIDE}" stroke-width="0.22" stroke-dasharray="1 0.6"/>')
            if w is not None:
                aw = float(val(w)) * 10; ah = float(val(h)) * 10 if h is not None else min(bh, aw * 0.6)
                a0 = fgx.P((c[0] - aw / 2, c[1] + ah / 2)); a1 = fgx.P((c[0] + aw / 2, c[1] - ah / 2))
                o.append(f'<rect x="{f(a0[0])}" y="{f(a0[1])}" width="{f(a1[0] - a0[0])}" height="{f(a1[1] - a0[1])}" fill="none" stroke="{RED if ok is False else INK}" stroke-width="0.3"/>')
    return o


def p_construction(st, product):
    o = H(st, product, "CONSTRUCTION + BILL OF MATERIALS", f"{st.name} · shared cap construction (every cap) + this style · amber = proposed → F1", "H5")
    fam = st.fam
    rows = [[r["area"], r["spec"]] for r in st.t["construction"]]
    shared = [("Seam tape", fam["seam_tape"]["spec"]), ("Seam tape text", fam["seam_tape"]["text"]),
              ("Seam tape colour", fam["seam_tape"]["colour_trucker"] if "mesh" in st.raw else fam["seam_tape"]["colour_full_fabric"]),
              ("Seam tape rebrand", fam["seam_tape"]["rebrand"]), ("Sweatband", fam["sweatband"]["spec"]), ("Sweatband material", fam["sweatband"]["material"]),
              ("Inner label", fam["inner_label"]["spec"]), ("Inside character", fam["inside_character"]["spec"]),
              ("Button", fam["button"]["spec"]), ("Eyelets", fam["eyelets"]["spec"]), ("Eyelet count", fam["eyelets"]["count"])]
    if st.kind == "knit":
        shared = [("Inner label", fam["inner_label"]["spec"])]
    else:
        if st.closure_kind() == "strap": shared += [("Strap", fam["strap"]["rule"]), ("Strap colour", fam["strap"]["colour"])]
        if not st.structured(): shared.append(("Mesh guard", fam["mesh_guard"]["spec"]))
    o.append(t(12, 33, f"THIS STYLE ({st.key})", 2.1, 700))
    y = table(o, 12, 37.5, [("Area", 0, 30), ("Spec", 32, 100)], rows, 1.55, 3.4, head=False, width=134)
    y += 2; o.append(t(12, y, "EVERY CAP (cap family)", 2.1, 700)); y += 4.5
    y = table(o, 12, y, [("Area", 0, 30), ("Spec", 32, 100)], [[a, v] for a, v in shared], 1.5, 3.3, head=False, width=134)
    o.append(t(154, 33, "BILL OF MATERIALS", 2.1, 700))
    bom = [[r["item"], r["spec"]] for r in st.t["bom"]]
    bom += [["Brim protector", fam["brim_protector"]["spec"]], ["Hang tag", fam["hang_tag"]["spec"]], ["Hang tag attach", fam["hang_tag"]["attach"]],
            ["Polybag", fam["packing"]["bag"]], ["Per carton", V(f"{val(fam['packing']['pcs_per_carton'])} pcs", is_prop(fam['packing']['pcs_per_carton']), path="packing.pcs_per_carton")]]
    if st.kind == "knit": bom = [b for b in bom if b[0] not in ("Brim protector",)]
    table(o, 154, 37.5, [("Item", 0, 30), ("Spec", 32, 98)], bom, 1.55, 3.4, head=False, width=130)
    return o


# ----------------------------------------------------------------------------- F1
def item_label(st, p):
    m = re.match(r"styles\.[a-z0-9-]+\.(.*)", p)
    if m:
        rest = m.group(1)
        if rest.startswith("pom."):
            c = rest.split(".")[1]; return "Measurements", f"POM {c} {st.pom[c].name} (cm)"
        mm = re.match(r"(construction|bom)\[(\d+)\]", rest)
        if mm:
            r = st.raw[mm.group(1)][int(mm.group(2))]
            return ("Construction" if mm.group(1) == "construction" else "Bill of materials"), r.get("area") or r.get("item")
        if rest.startswith("knit."): return "Knit", rest.split(".")[1].capitalize()
        if rest.startswith("embroidery."):
            pos, k = rest.split(".")[1:3]; return "Embroidery", f"{POS_NAMES.get(pos, pos)} — {k.replace('_cm', ' (cm)').replace('_', ' ')}"
        if rest.startswith("products."): return "Products", "Product made on this style"
        return "Style (block)", dict(FIELDS).get(rest, rest.replace("_", " "))
    if p.startswith("cap_frame."):
        _, pos, k = p.split("."); return "Cap-frame limits", f"{POS_NAMES.get(pos, pos)} — max {'width' if 'w_' in k else 'height'} (cm)"
    if p == "pom_tolerance_cm": return "Measurements", "Tolerance ± (cm), every measurement without its own"
    if p.startswith("block."): return "Sketch constants (drawing only)", p.split(".")[1].replace("_cm", " (cm)").replace("_", " ")
    top = p.split(".")[0]
    return "Every cap (family)", " — ".join(x.replace("_cm", " (cm)").replace("_", " ") for x in p.split("."))


GROUP_ORDER = ["Style (block)", "Measurements", "Construction", "Bill of materials", "Knit", "Embroidery", "Cap-frame limits",
               "Every cap (family)", "Products", "Sketch constants (drawing only)"]


def open_items(st):
    items = [(*item_label(st, v.path), vtxt(v)) for v in st.proposed()]
    items.sort(key=lambda it: GROUP_ORDER.index(it[0]) if it[0] in GROUP_ORDER else 99)
    return items


def p_factory(st, product):
    pages, o, y = [], None, 0
    n = [0]
    fac = st.t["factory"]
    def new():
        nonlocal o, y
        n[0] += 1; code = "F1" if n[0] == 1 else f"F1.{n[0]}"
        o = H(st, product, "F1 · FACTORY REQUESTS — please answer before the sample",
              f"{product or st.name} · hat style {st.key} · for {val(fac)} · every amber value in this pack, in one list", code)
        pages.append(o); y = 33
    new()
    qs = [val(q) for q in (st.fam.get("factory_questions") or [])] + [val(q) for q in (st.t.get("factory_questions") or [])]
    o.append(t(12, y, "FIRST, PLEASE", 2.4, 700)); y += 4.6
    for i, q in enumerate(qs, 1):
        y = para(o, 16, y, f"{i}. {q}", 262, 1.8, 2.9, 700, PROP) + 0.8
    y += 2
    o.append(t(12, y, "PLEASE CONFIRM OR CORRECT EACH VALUE (we proposed it; it is not recorded)", 2.2, 700)); y += 4.6
    cur = None; k = 0
    for grp, lab, v in open_items(st):
        txt = v.text(tag=False); nt = v.note
        lines = len(wrap(txt, 150, 1.55)) + (len(wrap(nt, 160, 1.35)) if nt else 0)
        if y + lines * 2.7 + (5 if grp != cur else 0) > SH - 12: new()
        if grp != cur:
            o.append(t(12, y + 1, grp.upper(), 1.8, 700, MUTED)); y += 4.2; cur = grp
        k += 1
        o.append(f'<rect x="12" y="{f(y - 2.0)}" width="2.4" height="2.4" fill="none" stroke="{INK}" stroke-width="0.22"/>')
        o.append(t(16, y, f"{k}.", 1.55, 700)); para(o, 21, y, lab, 92, 1.55, 2.7, 700, INK)
        yy = para(o, 116, y, txt, 150, 1.55, 2.7, 600, PROP)
        if nt: yy = para(o, 116, yy, nt, 160, 1.35, 2.35, 400, MUTED)
        y = max(yy, y + len(wrap(lab, 92, 1.55)) * 2.7) + 0.9
    return pages


def pages(style, product=None):
    """[(code, title, [svg])] for a hat pack built from a catalogue style (key or Style)"""
    st = CS.load().get(style) if isinstance(style, str) else style
    if st.kind == "knit":
        plan = [("H1", "Style sheet", lambda: [p_style(st, product)]), ("H2", "Points of measure", lambda: [p_pom(st, product)]),
                ("K1", "Knit spec", lambda: [p_knit(st, product)]), ("H4", "Embroidery positions", lambda: [p_embroidery(st, product)]),
                ("H5", "Construction + BOM", lambda: [p_construction(st, product)]), ("F1", "Factory requests", lambda: p_factory(st, product))]
    else:
        plan = [("H1", "Style sheet", lambda: [p_style(st, product)]), ("H2", "Points of measure", lambda: [p_pom(st, product)]),
                ("H3", "Flats", lambda: [p_flats(st, product)]), ("H4", "Embroidery positions + cap-frame limits", lambda: [p_embroidery(st, product)]),
                ("H5", "Construction + BOM", lambda: [p_construction(st, product)]), ("F1", "Factory requests", lambda: p_factory(st, product))]
    return [(c, ttl, [doc(b) for b in fn()]) for c, ttl, fn in plan]


def render(style, out, product=None, png=True):
    """write <out>/<key>_hatpack.pdf + <out>/pages/<code>.png; returns (pdf, [png paths])"""
    import cairosvg
    from family.build import write_pdf
    os.makedirs(os.path.join(out, "pages"), exist_ok=True)
    ps = pages(style, product); svgs = []; pngs = []
    for code, _, ss in ps:
        for i, s in enumerate(ss):
            svgs.append(s)
            if png:
                p = os.path.join(out, "pages", f"{code}{'' if i == 0 else f'_{i + 1}'}.png")
                cairosvg.svg2png(bytestring=s.encode(), write_to=p, output_width=2400); pngs.append(p)
    key = style if isinstance(style, str) else style.key
    return write_pdf(svgs, os.path.join(out, f"{key}_hatpack.pdf")), pngs


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="cap_pages.py", description="hat pack pages from one catalogue style")
    ap.add_argument("style"); ap.add_argument("--product"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        st = CS.load().get(a.style)
    except CS.StyleError as e:
        print(f"ERROR: {e}"); return 1
    out = a.out or os.path.join(CS.ROOT, "families", "cap", "out", st.key)
    pdf, pngs = render(st, out, a.product)
    print(f"{st.name}: {len(pngs)} pages -> {pdf}\n  page PNGs: {os.path.join(out, 'pages')} · {len(st.proposed())} values {TAG} (F1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
