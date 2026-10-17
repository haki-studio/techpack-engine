"""Garment model for the Castle Falls jacket — Drum Island block (same silhouette + pattern), this mockup's welts.
Garment coords (mm): fronts x from CF (+ = wearer's LEFT = viewer's right on a front view), y down from the CF neck seam.
Keeps the API the engine expects from a project `front` module (pattern.py reads WELT_L; techflat reads COLLAR_*)."""
import numpy as np
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from shapely import affinity
import drum

BLK = drum.Block("M")
HEM = BLK.f_hem
PANEL_R = BLK.front_panel(-1)
PANEL_L = BLK.front_panel(+1)
_neck = [(-x, y) for x, y in drum.curve((0, 0), BLK.f_hps, 28, 16)]
COLLAR_R = Polygon(_neck + [(-176, -76), (-150, -30), (-72, 66), (-14, 22)]).buffer(0)    # collar lying flat (Drum Island)
COLLAR_L = affinity.scale(COLLAR_R, -1, 1, origin=(0, 0))

# Welt pockets: Drum Island welt size (1.4 x 13 cm, pattern.py WELT_L/WELT_W) at THIS mockup's position + angle, read from
# inputs/front.png (welt ends px (262, 438) -> (205, 535) and (582, 438) -> (628, 530); CF x 413, neck y 150,
# 1.28 mm/px across, 1.14 mm/px down): centre 230 mm from CF, 384 mm below the CF neck seam, 56 deg from horizontal,
# top end toward CF. Outer end clears the side seam by ~29 mm.  [PROPOSED]
WELT_C, WELT_ANG, WELT_LEN, WELT_W = (230.0, 384.0), 56.0, 130.0, 14.0
def _welt(side):
    ux, uy = np.cos(np.radians(WELT_ANG)), np.sin(np.radians(WELT_ANG))
    c = np.array([WELT_C[0]*side, WELT_C[1]]); u = np.array([ux*side, uy])
    a, b = c - u*WELT_LEN/2, c + u*WELT_LEN/2          # top-inner -> bottom-outer
    return LineString([a, b]).buffer(WELT_W/2, cap_style="flat", join_style="mitre")
WELT_R = _welt(-1)
WELT_L = _welt(+1)
