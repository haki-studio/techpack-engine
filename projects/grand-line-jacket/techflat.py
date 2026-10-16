"""Technical flats (Drum Island block) for the Grand Line jacket — washed navy, black collar + rib (line drawings in mm, size M). y from HPS line (0) down."""
import math
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity
import drum
from render import f

K = 1.0
LBL = 7.0
INK = "#111111"; MUT = "#9AA3B8"; SH = "#3C4560"; CORD = "#1E1E1E"; RIBC = "#262626"; CUFF = "#262626"; ZIP = "#A07C3C"

class Flat:
    def __init__(self, size="M"):
        b = drum.Block(size); self.b = b
        self.L = b.L; self.rib = b.rib; self.cuff = drum.PROPOSED["cuff_rib"]
        self.hps = (b.neck2, 0.0); self.sp = (b.sh2, b.drop); self.ua = (b.chest2, b.drop + b.arm_depth)
        self.hem_seam = b.L - b.rib; self.hem_edge = b.L
        self.sweep2 = drum.m("D", size) / 2
        self.fnd = b.fnd; self.bnd = b.bnd
        # sleeve: hangs down/out at 64° below horizontal
        th = math.radians(62); self.sdir = np.array([math.cos(th), math.sin(th)]); self.sperp = np.array([math.sin(th), -math.cos(th)])
        G = drum.m("G", size); H = drum.m("H", size); Fb = drum.m("F", size)
        sp = np.array(self.sp); self.cuff_out = sp + self.sdir * G
        self.cuff_in = self.cuff_out - self.sperp * H
        self.cuff_seam_out = sp + self.sdir * (G - self.cuff); self.cuff_seam_in = self.cuff_seam_out - self.sperp * H
        self.G, self.H, self.F = G, H, Fb

    # ---------------------------------------------------------------- outlines (right half = wearer's left on front view; mirrored)
    def body_half(self, back=False):
        nd = self.bnd if back else self.fnd
        neck = drum.curve((0, nd), self.hps, 6 if back else 26, 14)
        arm = drum.curve(self.sp, self.ua, -20, 24)
        side = [(self.ua[0], self.ua[1]), (self.ua[0] - 6, self.hem_seam * 0.7), (self.sweep2 + 6, self.hem_seam)]
        return neck + [self.sp] + arm[1:] + side[1:]
    def body(self, back=False):
        r = self.body_half(back); l = [(-x, y) for x, y in r][::-1]
        return Polygon(r + [(0, self.hem_seam)] + l).buffer(0)
    def sleeve(self, side=1):
        sp = np.array(self.sp); ua = np.array(self.ua)
        pts = [tuple(sp), tuple(self.cuff_seam_out), tuple(self.cuff_seam_in), tuple(ua)]
        cap = drum.curve(self.ua, self.sp, 20, 20)
        P = Polygon(pts + cap[1:-1]).buffer(0)
        return P if side == 1 else affinity.scale(P, -1, 1, origin=(0, 0))
    def cuff_poly(self, side=1):
        P = Polygon([tuple(self.cuff_seam_out), tuple(self.cuff_out), tuple(self.cuff_in), tuple(self.cuff_seam_in)])
        return P if side == 1 else affinity.scale(P, -1, 1, origin=(0, 0))
    def hem_rib(self):
        w = self.sweep2 + 6
        return Polygon([(-w, self.hem_seam), (w, self.hem_seam), (w - 4, self.hem_edge), (-(w - 4), self.hem_edge)])
    def collar_front(self):
        import front as FR
        return unary_union([FR.COLLAR_R, FR.COLLAR_L]).buffer(0.01).buffer(-0.01).union(Polygon([(-2, 0), (2, 0), (2, 30), (-2, 30)])).__class__(
            affinity.translate(unary_union([FR.COLLAR_R, FR.COLLAR_L]).buffer(1.0).buffer(-1.0), 0, self.fnd).exterior)
    def _collar_front_old(self):
        nd = self.fnd
        right = [(0, nd + 6), (40, nd + 30), (78, nd + 74), (118, nd + 2), (self.hps[0] + 34, 10), (self.hps[0] + 30, -18), (self.hps[0] - 10, -24)]
        left = [(-x, y) for x, y in right][::-1]
        return Polygon(right + left).buffer(0)
    def collar_back(self):
        w = self.hps[0] + 34
        return Polygon([(-w, -18), (w, -18), (w + 6, 62), (0, 66), (-w - 6, 62)]).buffer(0)
    def welt(self, side=1):
        import front as FR
        return affinity.translate(FR.WELT_L if side == 1 else FR.WELT_R, 0, self.fnd)
    def _welt_old(self, side=1):
        a = np.array([-118 * -1, 415.0]) if side == 1 else np.array([-118.0, 415.0])
        bpt = np.array([-230 * -1, 503.0]) if side == 1 else np.array([-230.0, 503.0])
        return LineString([tuple(a), tuple(bpt)]).buffer(8, cap_style="flat", join_style="mitre")

def path(cs, close=False):
    cs = list(cs)
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in cs) + (" Z" if close else "")

def poly_path(p):
    out = []
    for g in ([p] if p.geom_type == "Polygon" else list(p.geoms)):
        out.append(path(list(g.exterior.coords)[:-1], True))
    return " ".join(out)

def topstitch(p, inset, dash="1.6 1.0", w=0.22, col=MUT, parts=None):
    w = w * K
    q = p.buffer(-inset, join_style="mitre")
    if q.is_empty: return ""
    lines = []
    for g in ([q] if q.geom_type == "Polygon" else list(q.geoms)):
        lines.append(path(list(g.exterior.coords)))
    return f'<path d="{" ".join(lines)}" fill="none" stroke="{col}" stroke-width="{f(w)}" stroke-dasharray="{dash}"/>'

def dashed_line(cs, dash="1.6 1.0", w=0.22, col=MUT):
    w = w * K
    return f'<path d="{path(cs)}" fill="none" stroke="{col}" stroke-width="{f(w)}" stroke-dasharray="{dash}"/>'

def rib_lines(p, step=4.0, col="#4A4A4A"):
    x0, y0, x1, y1 = p.bounds; out = []
    for x in np.arange(x0 + step/2, x1, step):
        seg = p.intersection(LineString([(x, y0 - 1), (x, y1 + 1)]))
        if not seg.is_empty and seg.geom_type == "LineString":
            out.append(path(seg.coords))
    return f'<path d="{" ".join(out)}" stroke="{col}" stroke-width="{f(0.25*K)}" fill="none"/>'

def cord_lines(p, ang=0, step=3.0, col="#3A3A3A"):
    from stitchrender import hatch
    segs = hatch(p, ang, step); out = [path(s.coords) for s in segs if len(s.coords) > 1]
    return f'<path d="{" ".join(out)}" stroke="{col}" stroke-width="{f(0.3*K)}" fill="none" opacity="0.6"/>'

def draw_front(F, emb_boxes=(), callouts=True):
    o = []
    for s in (1, -1):
        sl = F.sleeve(s); o.append(f'<path d="{poly_path(sl)}" fill="{SH}" stroke="{INK}" stroke-width="{f(0.5*K)}"/>')
        o.append(topstitch(sl.intersection(F.sleeve(s).buffer(0)), 5))
        c = F.cuff_poly(s); o.append(f'<path d="{poly_path(c)}" fill="{CUFF}" stroke="{INK}" stroke-width="{f(0.5*K)}"/>'); o.append(rib_lines(c, 3.2, "#4A4A4A"))
    body = F.body(False)
    o.append(f'<path d="{poly_path(body)}" fill="{SH}" stroke="{INK}" stroke-width="{f(0.6*K)}"/>')
    # seams + topstitch
    for s in (1, -1):
        arm = [(s*x, y) for x, y in [F.sp] + drum.curve(F.sp, F.ua, -20, 24)[1:]]
        o.append(dashed_line([(s*(x - 6), y) for x, y in arm]))
        o.append(dashed_line([(s*F.hps[0], F.hps[1] + 6), (s*F.sp[0], F.sp[1] + 6)]))
    rib = F.hem_rib(); o.append(f'<path d="{poly_path(rib)}" fill="{RIBC}" stroke="{INK}" stroke-width="{f(0.5*K)}"/>'); o.append(rib_lines(rib, 3.2))
    o.append(dashed_line([(-F.sweep2, F.hem_seam - 5), (F.sweep2, F.hem_seam - 5)]))
    for s in (1, -1):
        w = F.welt(s); o.append(f'<path d="{poly_path(w)}" fill="#2E3550" stroke="{INK}" stroke-width="{f(0.45*K)}"/>')
        o.append(topstitch(w, 2.0))
        cs = list(w.exterior.coords); o.append(f'<path d="{path([cs[0], cs[1]])}" stroke="{INK}" stroke-width="{f(0.9*K)}"/>')
    # zip
    zt = box(-6, F.fnd, 6, F.hem_edge); o.append(f'<path d="{poly_path(zt)}" fill="#7A5C34" stroke="{INK}" stroke-width="{f(0.35*K)}"/>')
    o.append(f'<line x1="0" y1="{f(F.fnd)}" x2="0" y2="{f(F.hem_edge)}" stroke="#D2B062" stroke-width="{f(2.2*K)}" stroke-dasharray="0.7 0.5"/>')
    o.append(f'<rect x="-4" y="{f(F.fnd + 2)}" width="8" height="14" rx="1.5" fill="{ZIP}" stroke="{INK}" stroke-width="{f(0.3*K)}"/>')
    o.append(f'<rect x="-1.6" y="{f(F.fnd + 14)}" width="3.2" height="12" rx="1" fill="{ZIP}" stroke="{INK}" stroke-width="{f(0.3*K)}"/>')
    for s in (1, -1): o.append(dashed_line([(s*10, F.fnd + 4), (s*10, F.hem_seam - 2)]))
    neck = drum.curve((0, F.fnd), F.hps, 26, 14)
    stand = Polygon(neck + drum.curve(F.hps, (-F.hps[0], 0), 22, 16)[1:] + [(-x, y) for x, y in neck][::-1][1:]).buffer(0)
    o.append(f'<path d="{poly_path(stand)}" fill="#141414" stroke="{INK}" stroke-width="{f(0.5*K)}"/>'); o.append(cord_lines(stand, 90, 2.2, "#3A3A3A"))
    col = F.collar_front(); o.append(f'<path d="{poly_path(col)}" fill="{CORD}" stroke="{INK}" stroke-width="{f(0.6*K)}"/>'); o.append(cord_lines(col, 90, 2.2))
    o.append(topstitch(col, 4, "1.4 0.9", 0.25, "#6A6A6A"))
    for (x0, y0, x1, y1, lab) in emb_boxes:
        o.append(f'<rect x="{f(x0)}" y="{f(y0)}" width="{f(x1-x0)}" height="{f(y1-y0)}" fill="none" stroke="#C0392B" stroke-width="{f(0.5*K)}" stroke-dasharray="3 2"/>')
        o.append(f'<circle cx="{f(x0)}" cy="{f(y0)}" r="{f(LBL)}" fill="#C0392B"/><text x="{f(x0)}" y="{f(y0 + LBL*0.36)}" font-size="{f(LBL)}" font-weight="700" fill="#FFF" text-anchor="middle" font-family="Noto Sans CJK JP">{lab}</text>')
    return "".join(o)

def draw_back(F, emb_boxes=()):
    o = []
    for s in (1, -1):
        sl = F.sleeve(s); o.append(f'<path d="{poly_path(sl)}" fill="{SH}" stroke="{INK}" stroke-width="{f(0.5*K)}"/>')
        c = F.cuff_poly(s); o.append(f'<path d="{poly_path(c)}" fill="{CUFF}" stroke="{INK}" stroke-width="{f(0.5*K)}"/>'); o.append(rib_lines(c, 3.2, "#4A4A4A"))
    body = F.body(True); o.append(f'<path d="{poly_path(body)}" fill="{SH}" stroke="{INK}" stroke-width="{f(0.6*K)}"/>')
    for s in (1, -1):
        arm = [(s*x, y) for x, y in [F.sp] + drum.curve(F.sp, F.ua, -20, 24)[1:]]
        o.append(dashed_line([(s*(x - 6), y) for x, y in arm]))     # back armhole: 6 mm topstitch on the body
        o.append(dashed_line([(s*F.hps[0], F.hps[1] + 6), (s*F.sp[0], F.sp[1] + 6)]))
    rib = F.hem_rib(); o.append(f'<path d="{poly_path(rib)}" fill="{RIBC}" stroke="{INK}" stroke-width="{f(0.5*K)}"/>'); o.append(rib_lines(rib, 3.2))
    o.append(dashed_line([(-F.sweep2, F.hem_seam - 5), (F.sweep2, F.hem_seam - 5)]))
    col = F.collar_back(); o.append(f'<path d="{poly_path(col)}" fill="{CORD}" stroke="{INK}" stroke-width="{f(0.6*K)}"/>'); o.append(cord_lines(col, 90, 2.2))
    o.append(topstitch(col, 4, "1.4 0.9", 0.25, "#6A6A6A"))
    o.append(f'<line x1="0" y1="-30" x2="0" y2="{f(F.hem_edge + 10)}" stroke="#0A84D6" stroke-width="{f(0.3*K)}" stroke-dasharray="3 2"/>')
    for (x0, y0, x1, y1, lab) in emb_boxes:
        o.append(f'<rect x="{f(x0)}" y="{f(y0)}" width="{f(x1-x0)}" height="{f(y1-y0)}" fill="none" stroke="#C0392B" stroke-width="{f(0.5*K)}" stroke-dasharray="3 2"/>')
        o.append(f'<circle cx="{f(x0)}" cy="{f(y0)}" r="{f(LBL)}" fill="#C0392B"/><text x="{f(x0)}" y="{f(y0 + LBL*0.36)}" font-size="{f(LBL)}" font-weight="700" fill="#FFF" text-anchor="middle" font-family="Noto Sans CJK JP">{lab}</text>')
    return "".join(o)

def bounds_front(F):
    U = unary_union([F.body(False), F.sleeve(1), F.sleeve(-1), F.cuff_poly(1), F.cuff_poly(-1), F.hem_rib(), F.collar_front()])
    return U.bounds
