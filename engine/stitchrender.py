"""Stitch-out preview: every region drawn as thread rows at its own stitch angle.
satin  : rows across the shape at 0.42 mm, sheen highlight mid-row
tatami : rows at 0.42 mm, broken into 3.6 mm stitches with staggered penetrations
padded : satin with stronger sheen + inner edge shadow (raised)
bean/run: rope texture along the line
"""
import math, random
import numpy as np
import cairocffi as cairo
from PIL import Image, ImageFilter, ImageChops
from shapely.geometry import LineString, MultiLineString, Polygon, Point
from shapely import affinity
from motifs2 import HEX

SP = 0.42      # row spacing mm

def hexrgb(h): return tuple(int(h[i:i+2], 16)/255 for i in (1, 3, 5))
def shade(c, k):
    if k >= 0: return tuple(min(1, x + (1-x)*k) for x in c)
    return tuple(max(0, x*(1+k)) for x in c)

def polys(g):
    if g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def auto_angle(p):
    mrr = p.minimum_rotated_rectangle
    cs = list(mrr.exterior.coords)
    e1 = np.array(cs[1]) - np.array(cs[0]); e2 = np.array(cs[2]) - np.array(cs[1])
    long_e = e1 if np.linalg.norm(e1) >= np.linalg.norm(e2) else e2
    return math.degrees(math.atan2(long_e[1], long_e[0])) + 90   # stitches across the long axis

def hatch(p, ang, sp):
    c = p.centroid
    q = affinity.rotate(p, -ang, origin=c)
    x0, y0, x1, y1 = q.bounds
    lines = [LineString([(x0 - 1, y), (x1 + 1, y)]) for y in np.arange(y0 + sp/2, y1, sp)]
    if not lines: return []
    inter = q.intersection(MultiLineString(lines))
    segs = [inter] if inter.geom_type == "LineString" else [g for g in getattr(inter, "geoms", []) if g.geom_type == "LineString"]
    return [affinity.rotate(s, ang, origin=c) for s in segs]

def radial(p, cx, cy, sp):
    out = []
    minx, miny, maxx, maxy = p.bounds
    Rm = max(math.hypot(x - cx, y - cy) for x, y in [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)])
    rmid = max(1.0, (p.area / math.pi) ** 0.5)
    n = int(2*math.pi*max(rmid, Rm*0.55) / sp)
    rays = [LineString([(cx, cy), (cx + Rm*1.1*math.cos(2*math.pi*k/n), cy + Rm*1.1*math.sin(2*math.pi*k/n))]) for k in range(n)]
    inter = p.intersection(MultiLineString(rays))
    return [inter] if inter.geom_type == "LineString" else [g for g in getattr(inter, "geoms", []) if g.geom_type == "LineString"]

class Renderer:
    def __init__(self, x0, y0, x1, y1, ppm):
        self.x0, self.y0, self.ppm = x0, y0, ppm
        self.W, self.H = int((x1 - x0)*ppm), int((y1 - y0)*ppm)
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.W, self.H)
        self.ctx = cairo.Context(self.surf)
        self.ctx.scale(ppm, ppm); self.ctx.translate(-x0, -y0)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.rng = random.Random(3)

    def _row(self, seg, col, w, sheen=0.22, sep=0.18, tatami=False, phase=0.0):
        ctx = self.ctx; cs = list(seg.coords)
        if len(cs) < 2: return
        (ax, ay), (bx, by) = cs[0], cs[-1]
        L = math.hypot(bx - ax, by - ay)
        if L < 0.05: return
        j = self.rng.uniform(-0.05, 0.05)
        base = shade(col, j)
        ctx.set_line_width(w)
        ctx.set_source_rgb(*shade(base, -sep)); ctx.move_to(ax, ay); ctx.line_to(bx, by); ctx.stroke()
        ctx.set_line_width(w*0.72)
        ctx.set_source_rgb(*base); ctx.move_to(ax, ay); ctx.line_to(bx, by); ctx.stroke()
        if tatami:
            # stitches 3.6 long, penetrations staggered row to row
            ux, uy = (bx - ax)/L, (by - ay)/L
            t = (phase % 3.6)
            ctx.set_line_width(w*0.3); ctx.set_source_rgb(*shade(base, sheen*0.9))
            while t < L:
                t2 = min(L, t + 3.6) - 0.35
                s0 = max(0, t + 0.35)
                if t2 > s0:
                    ctx.move_to(ax + ux*(s0 + (t2-s0)*0.3), ay + uy*(s0 + (t2-s0)*0.3))
                    ctx.line_to(ax + ux*(s0 + (t2-s0)*0.7), ay + uy*(s0 + (t2-s0)*0.7)); ctx.stroke()
                t += 3.6
        else:
            ctx.set_line_width(w*0.28); ctx.set_source_rgb(*shade(base, sheen))
            ctx.move_to(ax + (bx-ax)*0.28, ay + (by-ay)*0.28); ctx.line_to(ax + (bx-ax)*0.62, ay + (by-ay)*0.62); ctx.stroke()

    def region(self, r):
        col = hexrgb(HEX[r["col"]]); st = r["st"]
        for p in polys(r["geom"]):
            if p.area < 0.03: continue
            if st in ("bean", "run"):
                self._rope(p, col, heavy=(st == "bean")); continue
            ang = r["ang"]
            if isinstance(ang, tuple) and ang[0] == "radial":
                segs = radial(p, ang[1], ang[2], SP)
            else:
                a = auto_angle(p) if (ang == "auto" or ang is None) else ang
                segs = hatch(p, a, SP)
            tat = st == "tatami"
            sheen = 0.32 if st == "padded" else (0.12 if tat else 0.24)
            for k, s in enumerate(segs):
                self._row(s, col, SP*1.12, sheen=sheen, tatami=tat, phase=(k % 3)*1.2)
            if st == "padded":
                self._edge_shadow(p, col)

    def _rope(self, p, col, heavy=True):
        ctx = self.ctx
        self._fill(p, shade(col, -0.12))
        for s in hatch(p, 35, 0.32):
            ctx.set_line_width(0.2); ctx.set_source_rgb(*shade(col, 0.12 if heavy else 0.05))
            cs = list(s.coords)
            if len(cs) < 2: continue
            ctx.move_to(*cs[0]); ctx.line_to(*cs[-1]); ctx.stroke()

    def _fill(self, p, rgb):
        ctx = self.ctx
        for ring in [p.exterior, *p.interiors]:
            cs = list(ring.coords); ctx.move_to(*cs[0])
            for c in cs[1:]: ctx.line_to(*c)
            ctx.close_path()
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); ctx.set_source_rgb(*rgb); ctx.fill()

    def _edge_shadow(self, p, col):
        ring = p.difference(p.buffer(-0.7))
        if not ring.is_empty:
            self.ctx.save(); self.ctx.push_group()
            for q in polys(ring): self._fill(q, shade(col, -0.16))
            self.ctx.pop_group_to_source(); self.ctx.paint_with_alpha(0.55); self.ctx.restore()

    def image(self):
        buf = self.surf.get_data()
        im = Image.frombuffer("RGBA", (self.W, self.H), bytes(buf), "raw", "BGRA", 0, 1)
        return im.copy()

def fabric(W, H, ppm, base="#D7C29C", seed=1):
    rng = np.random.default_rng(seed)
    b = np.array([int(base[i:i+2], 16) for i in (1, 3, 5)], float)
    n = rng.normal(0, 5.0, (H, W, 1))
    yy, xx = np.mgrid[0:H, 0:W]
    weave = (np.sin(xx * 2*np.pi / max(2, ppm*0.7)) * np.sin(yy * 2*np.pi / max(2, ppm*0.7)))[..., None] * 3.5
    arr = np.clip(b + n + weave, 0, 255).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, 1, axis=2) if arr.shape[2] == 3 else arr)

def composite(emb, ppm, base="#D7C29C"):
    W, H = emb.size
    bg = fabric(W, H, ppm, base).convert("RGBA")
    a = emb.split()[3]
    sh = Image.new("RGBA", (W, H), (40, 28, 18, 0))
    sh.putalpha(a.point(lambda v: int(v * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(max(1, ppm*0.45)))
    off = Image.new("RGBA", (W, H), (0, 0, 0, 0)); off.paste(sh, (int(ppm*0.35), int(ppm*0.5)))
    out = Image.alpha_composite(bg, off)
    return Image.alpha_composite(out, emb).convert("RGB")

def render(vis, bbox, ppm, base="#D7C29C", clip=None):
    x0, y0, x1, y1 = bbox
    rr = Renderer(x0, y0, x1, y1, ppm)
    from shapely.geometry import box as _b
    B = _b(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
    for r in vis:
        if not r["geom"].intersects(B): continue
        rr.region(dict(r, geom=r["geom"].intersection(B)))
    return composite(rr.image(), ppm, base)
