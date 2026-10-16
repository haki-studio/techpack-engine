"""Moon jacket — front garment model (size M). Same Drum Island pattern as plum + pine, so the welt pockets and collar
are the reference values (pattern.draft reads WELT_L from this module). No art here: see scene.py.
Garment coords (mm): x from CF (+ = wearer's LEFT = viewer's right on a front view), y down from CF neck seam."""
import numpy as np
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from shapely import affinity
import drum

BLK = drum.Block("M")
HEM = BLK.f_hem
PANEL_R = BLK.front_panel(-1)
PANEL_L = BLK.front_panel(+1)
ARM_R = unary_union([BLK.front_shoulder_line(-1), BLK.front_arm_line(-1)])
SIDE_R = BLK.front_side_line(-1)
_neck = [(-x, y) for x, y in drum.curve((0, 0), BLK.f_hps, 28, 16)]
COLLAR_R = Polygon(_neck + [(-176, -76), (-150, -30), (-72, 66), (-14, 22)]).buffer(0)   # collar lying flat
COLLAR_L = affinity.scale(COLLAR_R, -1, 1, origin=(0, 0))

# welt pockets: identical to the Drum Island pattern (plum + pine front.py, mockup px -> mm there)
_S, _SX, _SY, _CFX, _NECKY = 0.77, 0.80, 0.736, 448, 190
def _P(px, py): return ((px - _CFX) * _SX, (py - _NECKY) * _SY)
def welt(p0, p1, w=16):
    a = np.array(_P(*p0)); b = np.array(_P(*p1)); return LineString([a, b]).buffer(w * _S / 2, cap_style="flat", join_style="mitre")
WELT_R = welt((160, 745), (300, 625))
WELT_L = welt((600, 630), (720, 750))
KEEP_CF, KEEP_SEAM, KEEP_HEM, KEEP_WELT, KEEP_COLLAR = 15.0, 15.0, 10.0, 6.0, 6.0
WRAP = 3.0            # wires stop 3 mm short of the side seam on both pieces
