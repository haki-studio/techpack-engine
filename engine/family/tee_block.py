"""Tee flat (front + back) drawn from the POM chart — every line comes from a chart value or a named block constant.

Coords (mm): x from CF (front) / CB (back), + = viewer's right; y DOWN from the HPS line (y = 0 at the high point of
shoulder). CF neck seam at y = FND, CB neck seam at y = BND.

LESSONS C2: chest + bottom (+ bicep + sleeve opening) on the chart are HALF (flat) measures = the full width of the
flat. The half-flat width is divided by 2 for the CF-to-side distance and NEVER doubled: circumference = 2 x half.

Chart codes used (family.yaml pom_chart.poms): A body length HPS->hem, B chest (half), C shoulder, D bottom (half),
E sleeve length, F armhole straight, G bicep (half), H sleeve opening (half), J neck opening, K front neck drop,
L back neck drop, N neck band height. Block constants (family.yaml block:) are proposed: shoulder slope, hem heights.
"""
import math
import numpy as np
from shapely.geometry import Polygon, LineString, box
from .spec import val, SpecError

CODES = dict(length="A", chest="B", shoulder="C", bottom="D", sleeve="E", armhole="F", bicep="G", opening="H",
             neck="J", fnd="K", bnd="L", band="N")


def quad(p0, c, p1, n=24):
    p0, c, p1 = (np.array(v, float) for v in (p0, c, p1))
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t ** 2 * p1).tolist()


class TeeFlat:
    def __init__(self, spec, size):
        ch = spec.chart; self.size = size
        need = [c for c in CODES.values() if c not in ch.poms]
        if need: raise SpecError(f"pom_chart is missing POM code(s) {need} that the tee block needs ({CODES})")
        g = lambda k: ch.mm(CODES[k], size)
        for k, code in CODES.items():
            if k in ("chest", "bottom", "bicep", "opening") and not val(ch[code].half):
                raise SpecError(f"tee block expects {code} ({ch[code].name}) as a HALF (flat) measure (LESSONS C2)")
        blk = spec.tree.get("block", {})
        self.slope = float(val(blk.get("shoulder_slope_cm"), 3.5)) * 10
        self.hem_h = float(val(blk.get("body_hem_cm"), 2.5)) * 10
        self.sl_hem_h = float(val(blk.get("sleeve_hem_cm"), 2.5)) * 10
        self.L, self.fnd, self.bnd, self.band = g("length"), g("fnd"), g("bnd"), g("band")
        self.chest_flat, self.bottom_flat = g("chest"), g("bottom")          # half (flat) = full flat width
        self.chest2, self.bottom2 = self.chest_flat / 2, self.bottom_flat / 2   # CF -> side seam
        self.sh2, self.neck2 = g("shoulder") / 2, g("neck") / 2
        self.arm, self.slv, self.bicep_flat, self.open_flat = g("armhole"), g("sleeve"), g("bicep"), g("opening")
        self.hps = (self.neck2, 0.0)
        self.sp = (self.sh2, self.slope)
        dx = self.chest2 - self.sh2
        self.ua = (self.chest2, self.slope + math.sqrt(max(self.arm ** 2 - dx ** 2, 1.0)))
        self.hem = (self.bottom2, self.L)
        # sleeve angle: perpendicular distance from the underarm to the sleeve top line = bicep (half, flat)
        ux, uy = self.ua[0] - self.sp[0], self.ua[1] - self.sp[1]
        lo, hi = 0.0, math.radians(80)
        d = lambda th: math.cos(th) * uy - math.sin(th) * ux
        if d(lo) < self.bicep_flat: self.theta = 0.0
        else:
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if d(mid) > self.bicep_flat else (lo, mid)
            self.theta = (lo + hi) / 2
        u = np.array([math.cos(self.theta), math.sin(self.theta)]); n = np.array([-u[1], u[0]])   # n points down/in
        self.u, self.n = u, n
        self.cuff_out = tuple(np.array(self.sp) + self.slv * u)
        self.cuff_in = tuple(np.array(self.cuff_out) + self.open_flat * n)

    def neck_seam(self, back=False):
        """HPS line -> neck seam under the rib at CF / CB (mm): neck drop + band height"""
        return (self.bnd if back else self.fnd) + self.band

    # --- outlines (right half x >= 0, mirrored for the left)
    def neck_curve(self, back=False):
        drop = self.bnd if back else self.fnd
        return quad((0, drop), (self.neck2 * (0.96 if not back else 1.0), drop), self.hps, 20)

    def armhole_curve(self):
        mid = (np.array(self.sp) + np.array(self.ua)) / 2 + np.array([-8.0, 0])
        return quad(self.sp, mid, self.ua, 18)

    def body_half(self, back=False):
        return self.neck_curve(back) + [self.sp] + self.armhole_curve()[1:] + [self.hem, (0, self.L)]

    @staticmethod
    def mirror(pts): return [(-x, y) for x, y in pts]

    def body(self, back=False):
        r = self.body_half(back); l = self.mirror(r)[::-1]
        return Polygon(r[:-1] + l[1:]).buffer(0)

    def sleeve(self, side=1):
        pts = [self.sp, self.cuff_out, self.cuff_in, self.ua] + self.armhole_curve()[::-1][1:-1]
        return Polygon([(side * x, y) for x, y in pts]).buffer(0)

    def lines(self, back=False):
        """seam / keep-out lines for clearance checks (both halves)"""
        neck = self.neck_curve(back)
        neck = LineString(self.mirror(neck)[::-1] + neck[1:])
        arm = self.armhole_curve()
        out = dict(neck=neck,
                   armhole_r=LineString(arm), armhole_l=LineString(self.mirror(arm)),
                   side_r=LineString([self.ua, self.hem]), side_l=LineString(self.mirror([self.ua, self.hem])),
                   hem=LineString([(-self.bottom2, self.L), (self.bottom2, self.L)]),
                   shoulder_r=LineString([self.hps, self.sp]), shoulder_l=LineString(self.mirror([self.hps, self.sp])))
        return out

    def band_poly(self, back=False):
        """the visible neck rib (band height N) inside the body"""
        neck = self.neck_curve(back); ln = LineString(self.mirror(neck)[::-1] + neck[1:])
        return self.body(back).intersection(ln.buffer(self.band, cap_style=2))

    def bounds(self):
        b = self.sleeve(1).union(self.sleeve(-1)).union(self.body()).bounds
        return b

    def clearances(self, box_mm, back=False):
        """distance (mm) from an art box to each seam group (min over both sides); negative = art overlaps"""
        b = box(*box_mm); L = self.lines(back); body = self.body(back)
        def dist(line):
            return line.distance(b) if not line.intersects(b) else -1.0
        band = self.band_poly(back)
        out = {"neck rib": band.distance(b) if not band.intersects(b) else -1.0,
               "armhole": min(dist(L["armhole_r"]), dist(L["armhole_l"])),
               "side seam": min(dist(L["side_r"]), dist(L["side_l"])),
               "hem": dist(L["hem"]),
               "shoulder": min(dist(L["shoulder_r"]), dist(L["shoulder_l"]))}
        if not b.within(body): out["inside body"] = -1.0
        return out
