"""Technical flats (copied from projects/zip-hoodie-block/hflat.py, colours set per design by the caller) for the boxy zip hoodie block (line drawings, mm, size M). y from the HPS line (0) down.
Body + sleeve geometry = the Drum Island jacket block (drum.Block); hood + bands from hoodie.py."""
import math
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import drum, hoodie as HD
from render import f

INK = "#1A1A1A"; MUT = "#7A7A7A"; SHELL = "#D3D9E2"; SHELL_D = "#BCC4D0"; SHERPA = "#F2ECDF"; SHERPA_L = "#D9CFBC"; ZIP = "#A07C3C"

def path(cs, close=False):
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in cs) + (" Z" if close else "")
def poly_path(p):
    return " ".join(path(list(g.exterior.coords)[:-1], True) for g in ([p] if p.geom_type == "Polygon" else list(p.geoms)))
def fill(p, col, w=0.5): return f'<path d="{poly_path(p)}" fill="{col}" stroke="{INK}" stroke-width="{f(w)}" stroke-linejoin="round"/>'
def dash(cs, w=0.22, col=MUT, d="1.6 1.0"): return f'<path d="{path(cs)}" fill="none" stroke="{col}" stroke-width="{f(w)}" stroke-dasharray="{d}"/>'
def topstitch(p, inset, w=0.22):
    q = p.buffer(-inset, join_style="mitre")
    if q.is_empty: return ""
    return "".join(dash(list(g.exterior.coords), w) for g in ([q] if q.geom_type == "Polygon" else q.geoms))

class Flat:
    def __init__(self, size="M"):
        b = drum.Block(size); self.b = b; self.size = size
        self.band = HD.hcm("S", size); self.cuffh = HD.hcm("T", size)
        self.hps = (b.neck2, 0.0); self.sp = (b.sh2, b.drop); self.ua = (b.chest2, b.drop + b.arm_depth)
        self.hem_edge = b.L; self.hem_seam = b.L - self.band
        self.sweep2 = drum.m("D", size) / 2; self.fnd, self.bnd = b.fnd, b.bnd
        th = math.radians(62); self.sdir = np.array([math.cos(th), math.sin(th)]); self.sperp = np.array([math.sin(th), -math.cos(th)])
        G, H = drum.m("G", size), drum.m("H", size); sp = np.array(self.sp)
        self.cuff_out = sp + self.sdir * G; self.cuff_in = self.cuff_out - self.sperp * H
        self.cs_out = sp + self.sdir * (G - self.cuffh); self.cs_in = self.cs_out - self.sperp * (H * 1.12)
        self.Q, self.R = HD.hcm("Q", size), HD.hcm("R", size)
    def body_half(self, back=False):
        nd = self.bnd if back else self.fnd
        neck = drum.curve((0, nd), self.hps, 6 if back else 26, 14)
        arm = drum.curve(self.sp, self.ua, -20, 24)
        side = [(self.ua[0] - 4, self.hem_seam * 0.7), (self.sweep2 + 8, self.hem_seam)]
        return neck + [self.sp] + arm[1:] + side
    def body(self, back=False):
        r = self.body_half(back); return Polygon(r + [(0, self.hem_seam)] + [(-x, y) for x, y in r][::-1]).buffer(0)
    def _m(self, P, side): return P if side == 1 else affinity.scale(P, -1, 1, origin=(0, 0))
    def sleeve(self, side=1):
        cap = drum.curve(self.ua, self.sp, 20, 20)
        return self._m(Polygon([self.sp, tuple(self.cs_out), tuple(self.cs_in), self.ua] + cap[1:-1]).buffer(0), side)
    def cuff(self, side=1):
        return self._m(Polygon([tuple(self.cs_out), tuple(self.cuff_out), tuple(self.cuff_in), tuple(self.cs_in)]).buffer(0), side)
    def hem_band(self):
        w = self.sweep2 + 8
        return Polygon([(-w, self.hem_seam), (w, self.hem_seam), (w - 6, self.hem_edge), (-(w - 6), self.hem_edge)])
    def welt(self, side=1):
        import front as F_
        W = affinity.translate(F_.WELT_L, 0, self.fnd)            # this design's welt (engine welt override, front.WELT)
        return self._m(W, side)
    # hood standing up (front view: sits on the neckline, face edges run into the zip; back view: centre panel up the middle)
    def _dome(self, hw_top, top, y_side, n=2.3):
        """right half of the hood crown: from the side at y_side over the top to x=0 (superellipse quarter)."""
        b_ = y_side - top
        return [(hw_top * abs(math.cos(t_)) ** (2 / n), y_side - b_ * abs(math.sin(t_)) ** (2 / n)) for t_ in np.linspace(0, math.pi / 2, 40)]
    def hood_outer(self, back=False):
        n2 = self.b.neck2; top = -(self.Q - 70); hw = n2 + 70
        dome = self._dome(hw, top, -90)                        # side at y=-90 up to top centre
        side = [(n2 + 12, 4), (n2 + 40, -12), (hw + 2, -50)]   # from just outside HPS curving up to the dome
        if back:
            right = [(n2 + 30, 60)] + side + dome
        else:
            neck = drum.curve((0, self.fnd), self.hps, 26, 14)  # CF -> HPS along the body neckline
            right = [(10, self.fnd)] + neck[1:] + side + dome
        left = [(-x, y) for x, y in right][::-1]
        return Polygon(right + left[1:]).buffer(0)
    def hood_opening(self):
        n2 = self.b.neck2; top = -(self.Q - 100); hw = n2 + 40
        dome = self._dome(hw, top, -70, 2.2)
        right = [(3, self.fnd - 16), (n2 * 0.42, self.fnd * 0.4), (n2 * 0.8, -6), (hw - 4, -40)] + dome
        left = [(-x, y) for x, y in right][::-1]
        return Polygon(right + left[1:]).buffer(0)

def gathers(p, step=7.0, y0=None, y1=None, skip=None, col=MUT):
    """short wavy gather marks across an elasticated band"""
    x0, by0, x1, by1 = p.bounds; out = []
    for x in np.arange(x0 + step / 2, x1, step):
        if skip and skip[0] <= x <= skip[1]: continue
        seg = p.intersection(LineString([(x, by0 - 1), (x, by1 + 1)]))
        if seg.is_empty or seg.geom_type != "LineString": continue
        (ax, ay), (bx, by) = seg.coords[0], seg.coords[-1]
        ys = np.linspace(ay + 2, by - 2, 7); out.append(path([(x + (1.0 if i % 2 else -1.0), y) for i, y in enumerate(ys)]))
    return f'<path d="{" ".join(out)}" fill="none" stroke="{col}" stroke-width="0.2"/>'

def sherpa_texture(p, step=5.0):
    x0, y0, x1, y1 = p.bounds; out = []
    for j, y in enumerate(np.arange(y0 + 3, y1, step * 0.8)):
        for x in np.arange(x0 + 3 + (j % 2) * step / 2, x1, step):
            if p.buffer(-1.5).contains(box(x - 1, y - 1, x + 1, y + 1)):
                out.append(f'M{f(x-1.4)} {f(y)} a1.4 1.2 0 1 1 2.8 0')
    return f'<path d="{" ".join(out)}" fill="none" stroke="{SHERPA_L}" stroke-width="0.25"/>'

def zip_tape(F, y0, y1, two_way=True):
    o = [f'<rect x="-5" y="{f(y0)}" width="10" height="{f(y1 - y0)}" fill="#3A3A3A" stroke="{INK}" stroke-width="0.3"/>',
         f'<line x1="0" y1="{f(y0)}" x2="0" y2="{f(y1)}" stroke="#D2B062" stroke-width="2.0" stroke-dasharray="0.7 0.5"/>']
    def slider(y, down):
        o.append(f'<rect x="-4" y="{f(y)}" width="8" height="12" rx="1.5" fill="{ZIP}" stroke="{INK}" stroke-width="0.3"/>')
        py = y + 12 if down else y - 11
        o.append(f'<rect x="-1.6" y="{f(py)}" width="3.2" height="11" rx="1" fill="{ZIP}" stroke="{INK}" stroke-width="0.3"/>')
    slider(y0 + 2, True)
    if two_way: slider(y1 - 26, True)
    return "".join(o)

def draw_front(F):
    o = []
    for s in (1, -1):
        sl = F.sleeve(s); o.append(fill(sl, SHELL, 0.5)); o.append(topstitch(sl, 5))
        c = F.cuff(s); o.append(fill(c, SHELL_D, 0.5)); o.append(gathers(c, 5.0))
    body = F.body(False); o.append(fill(body, SHELL, 0.6))
    for s in (1, -1):
        arm = [(s * x, y) for x, y in [F.sp] + drum.curve(F.sp, F.ua, -20, 24)[1:]]
        o.append(dash([(s * (x - 6), y) for x, y in arm]))
        o.append(dash([(s * F.hps[0], F.hps[1] + 6), (s * F.sp[0], F.sp[1] + 6)]))
        w = F.welt(s); o.append(fill(w, SHELL_D, 0.45)); o.append(topstitch(w, 2.0))
    band = F.hem_band(); o.append(fill(band, SHELL_D, 0.5)); o.append(gathers(band, 6.0, skip=(-HD.FLAT, HD.FLAT)))
    o.append(dash([(-F.sweep2, F.hem_seam - 5), (F.sweep2, F.hem_seam - 5)]))
    hood = F.hood_outer(); o.append(fill(hood, SHELL, 0.55))
    op = F.hood_opening(); o.append(fill(op, SHERPA, 0.45)); o.append(sherpa_texture(op))
    o.append(zip_tape(F, F.fnd - 2, F.hem_edge))
    for s in (1, -1): o.append(dash([(s * 10, F.fnd + 4), (s * 10, F.hem_seam - 2)]))
    return "".join(o)

def draw_back(F):
    o = []
    hood = F.hood_outer(True); o.append(fill(hood, SHELL, 0.6))
    ctr = hood.intersection(box(-HD.CW * 0.42, -1000, HD.CW * 0.42, 1000)); o.append(fill(ctr, SHELL, 0.4))
    for s in (1, -1):
        e = LineString([(s * HD.CW * 0.42 + s * 3, -1000), (s * HD.CW * 0.42 + s * 3, 1000)]).intersection(hood.buffer(-3))
        if not e.is_empty: o.append(dash(list(e.coords) if e.geom_type == "LineString" else list(max(e.geoms, key=lambda g: g.length).coords)))
    for s in (1, -1):
        sl = F.sleeve(s); o.append(fill(sl, SHELL, 0.5)); o.append(topstitch(sl, 5))
        c = F.cuff(s); o.append(fill(c, SHELL_D, 0.5)); o.append(gathers(c, 5.0))
    body = F.body(True); o.append(fill(body, SHELL, 0.6))
    for s in (1, -1):
        arm = [(s * x, y) for x, y in [F.sp] + drum.curve(F.sp, F.ua, -20, 24)[1:]]
        o.append(dash([(s * (x + 6), y) for x, y in arm]))
    band = F.hem_band(); o.append(fill(band, SHELL_D, 0.5)); o.append(gathers(band, 6.0))
    o.append(dash([(-F.sweep2, F.hem_seam - 5), (F.sweep2, F.hem_seam - 5)]))
    o.append(f'<line x1="0" y1="{f(-F.Q)}" x2="0" y2="{f(F.hem_edge + 10)}" stroke="#0A84D6" stroke-width="0.3" stroke-dasharray="3 2"/>')
    return "".join(o)

def bounds(F, back=False):
    U = unary_union([F.body(back), F.sleeve(1), F.sleeve(-1), F.cuff(1), F.cuff(-1), F.hem_band(), F.hood_outer(back)])
    return U.bounds
