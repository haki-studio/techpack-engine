"""Drum Island jacket block — geometry from the POM chart (cm in, mm out).
Back coords: x from CB (+ = wearer's right on a back view = viewer's right), y down from CB neck seam.
Front coords: x from CF (+ = wearer's left = viewer's right on a front view), y down from CF neck seam.
Values not on the chart are PROPOSED and flagged."""
import math
import numpy as np
from shapely.geometry import Polygon, LineString
from shapely import affinity

SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
POM_CM = {   # code: (name, how measured, values XS..3XL, tolerance cm)
 "A": ("Body length", "HPS to bottom hem edge", [62, 64, 66, 68.1, 70.1, 71.9, 73], 1.0),
 "B": ("Chest", "1/2, armpit to armpit, flat", [55.1, 57.4, 59.9, 62.5, 65, 67.6, 70.1], 1.0),
 "C": ("Shoulder", "seam to seam, flat", [49.5, 50.8, 52.1, 53.1, 54.4, 55.6, 57.1], 0.75),
 "D": ("Bottom sweep", "1/2, along hem edge, relaxed", [52, 55, 58, 61, 64, 67, 70], 1.0),
 "E": ("Armhole", "straight, shoulder point to underarm", [25, 26, 27, 28, 29, 30, 31], 0.5),
 "F": ("Bicep", "1/2, 2.5 below underarm, perpendicular", [23, 24, 25, 26, 27, 28, 29], 0.5),
 "G": ("Sleeve length", "shoulder seam to cuff edge", [61, 62.5, 64, 65.5, 67, 68.5, 70], 1.0),
 "H": ("Sleeve opening", "1/2, cuff edge, relaxed", [14, 14.5, 15, 15.5, 16, 16.5, 17], 0.5),
 "J": ("Neck opening", "seam to seam at HPS", [20]*7, 0.5),
 "K": ("Front neck drop", "HPS line to CF neck seam", [9.5]*7, 0.3),
 "L": ("Back neck drop", "HPS line to CB neck seam", [2]*7, 0.3),
 "M": ("Collar height at CB", "neck seam to collar edge", [10]*7, 0.3),
 "N": ("Collar point", "neck point to collar tip", [8.5]*7, 0.3),
 "P": ("Shoulder forward", "shoulder seam forward of HPS", [1]*7, 0.2),
}
PROPOSED = {"hem_rib": 55, "cuff_rib": 75, "shoulder_drop": 45, "zip_tape": 12}

def m(code, size="M"): return POM_CM[code][2][SIZES.index(size)] * 10.0

def curve(p0, p1, bulge, n=24):
    """quadratic curve from p0 to p1 bowing by `bulge` mm to the right of the travel direction"""
    p0, p1 = np.array(p0, float), np.array(p1, float); mid = (p0 + p1) / 2
    d = p1 - p0; nrm = np.array([d[1], -d[0]]) / (np.linalg.norm(d) or 1)
    c = mid + nrm * bulge
    t = np.linspace(0, 1, n)[:, None]
    return ((1-t)**2 * p0 + 2*(1-t)*t*c + t**2 * p1).tolist()

class Block:
    def __init__(self, size="M"):
        self.size = size
        self.chest2 = m("B", size) / 2          # half body width (CB/CF to side seam)
        self.sh2 = m("C", size) / 2
        self.neck2 = m("J", size) / 2
        self.arm = m("E", size)
        self.L = m("A", size)
        self.fnd, self.bnd = m("K", size), m("L", size)
        self.drop = PROPOSED["shoulder_drop"]; self.rib = PROPOSED["hem_rib"]
        dx = self.chest2 - self.sh2
        self.arm_depth = math.sqrt(max(self.arm**2 - dx**2, 1))
        # ---- back (y from CB neck)
        hps_b = -self.bnd
        self.b_hps = (self.neck2, hps_b); self.b_sp = (self.sh2, hps_b + self.drop)
        self.b_ua = (self.chest2, self.b_sp[1] + self.arm_depth)
        self.b_hem_edge = hps_b + self.L; self.b_hem = self.b_hem_edge - self.rib
        # ---- front (y from CF neck)
        hps_f = -self.fnd
        self.f_hps = (self.neck2, hps_f); self.f_sp = (self.sh2, hps_f + self.drop)
        self.f_ua = (self.chest2, self.f_sp[1] + self.arm_depth)
        self.f_hem_edge = hps_f + self.L; self.f_hem = self.f_hem_edge - self.rib

    # right half outlines (x >= 0), then mirrored
    def back_half(self):
        neck = curve((0, 0), self.b_hps, -6, 12)
        arm = curve(self.b_sp, self.b_ua, -18, 28)
        return neck + [self.b_sp] + arm[1:] + [(self.chest2, self.b_hem), (0, self.b_hem)]
    def back_panel(self):
        r = self.back_half(); l = [(-x, y) for x, y in r][::-1]
        return Polygon(r[:-1] + l[1:]).buffer(0)
    def back_arm_line(self, side=1):
        pts = [self.b_sp] + curve(self.b_sp, self.b_ua, -18, 28)[1:]
        return LineString([(side*x, y) for x, y in pts])
    def back_side_line(self, side=1):
        return LineString([(side*self.chest2, self.b_ua[1]), (side*self.chest2, self.b_hem)])
    def front_half(self):
        neck = curve((0, 0), self.f_hps, 28, 16)
        arm = curve(self.f_sp, self.f_ua, -22, 28)
        return neck + [self.f_sp] + arm[1:] + [(self.chest2, self.f_hem), (0, self.f_hem)]
    def front_panel(self, side):      # side +1 = wearer's left (x>0), -1 = wearer's right
        pts = self.front_half()
        if side < 0: pts = [(-x, y) for x, y in pts]
        return Polygon(pts).buffer(0)
    def front_arm_line(self, side):
        pts = [self.f_sp] + curve(self.f_sp, self.f_ua, -22, 28)[1:]
        return LineString([(side*x, y) for x, y in pts])
    def front_shoulder_line(self, side):
        return LineString([(side*self.f_hps[0], self.f_hps[1]), (side*self.f_sp[0], self.f_sp[1])])
    def front_side_line(self, side):
        return LineString([(side*self.chest2, self.f_ua[1]), (side*self.chest2, self.f_hem)])

if __name__ == "__main__":
    b = Block("M")
    print("back: hps", b.b_hps, "sp", b.b_sp, "ua", [round(v, 1) for v in b.b_ua], "hem seam", b.b_hem, "edge", b.b_hem_edge)
    print("front: hps", b.f_hps, "sp", b.f_sp, "ua", [round(v, 1) for v in b.f_ua], "hem seam", b.f_hem)
    print("back panel bounds", [round(v) for v in b.back_panel().bounds], "front L bounds", [round(v) for v in b.front_panel(1).bounds])
