"""Front garment geometry (Drum Island block, size M) — cheap to import (pattern.py + techflat read the welts/collar).
Garment coords (mm): x from CF (+ = wearer's LEFT = viewer's right on a front view), y down from the CF neck seam.
Mockup (inputs/front.png, 720 x 870 px) -> mm: x = (px - 375) * SX, y = (py - 175) * SY.
Welts + collar are the Drum Island pattern's (same pattern; brief: 'welts as mockup' — the mockup welts sit within
~30 mm of these, PROPOSED)."""
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import drum

SX, SY = 1.09, 1.05
CFX, NECKY = 375, 175
def P(px, py): return ((px - CFX) * SX, (py - NECKY) * SY)

BLK = drum.Block("M")
HEM = BLK.f_hem
PANEL_R = BLK.front_panel(-1)                                # wearer's right front (x < 0)
PANEL_L = BLK.front_panel(+1)                                # wearer's left front
ARM_R = unary_union([BLK.front_shoulder_line(-1), BLK.front_arm_line(-1)])
SIDE_R = BLK.front_side_line(-1)
_neck = [(-x, y) for x, y in drum.curve((0, 0), BLK.f_hps, 28, 16)]
COLLAR_R = Polygon(_neck + [(-131, -79), (-128, -30), (-112, 22), (-14, 8)]).buffer(0)   # collar lying flat, outline traced from the
# Forestball mockup (collar pattern unchanged: M 10 cm at CB, N 8.5 cm point; the lying-flat outline is a drawing aid, PROPOSED)
COLLAR_L = affinity.scale(COLLAR_R, -1, 1, origin=(0, 0))
def _welt(a, b, half=6.16): return LineString([a, b]).buffer(half, cap_style="flat", join_style="mitre")
WELT_R = _welt((-230.4, 408.48), (-118.4, 320.16))           # Drum Island welt 1.4 x 13 (pattern.WELT_L/W)
WELT_L = _welt((121.6, 323.84), (217.6, 412.16))
KEEP_CF, KEEP_SEAM, KEEP_HEM, KEEP_WELT, KEEP_COLLAR = 15.0, 15.0, 10.0, 6.0, 6.0
CLIP_MARGIN = 1.0     # clip 0.6 inside the seam keep-outs so the pattern check reads >= 15.0 (Rev B)
# shoulder + armhole keep-outs from the PATTERN (its shoulder seam sits 10 mm forward of the block's: chart P)
import pattern as _PT
_g, _mt = _PT.draft("M")
_e = lambda nm: [(-x, y) for x, y in next(e.pts for e in _g["F01"].edges if e.name == nm)]
ARM_R = unary_union([LineString(_e("shoulder")), LineString(_e("armhole"))])
SIDE_R = LineString(_e("side"))

def mirror(g): return affinity.scale(g, -1, 1, origin=(0, 0))

def clip_for(side):
    panel = PANEL_R if side == "R" else PANEL_L
    arm = ARM_R if side == "R" else mirror(ARM_R)
    sidel = SIDE_R if side == "R" else mirror(SIDE_R)
    collar = COLLAR_R if side == "R" else COLLAR_L
    weltg = WELT_R if side == "R" else WELT_L
    g = panel.difference(arm.buffer(KEEP_SEAM + CLIP_MARGIN)).difference(sidel.buffer(KEEP_SEAM + CLIP_MARGIN))
    g = g.difference(box(-KEEP_CF - 0.3, -150, KEEP_CF + 0.3, 900)).intersection(box(-400, -150, 400, HEM - KEEP_HEM - CLIP_MARGIN))
    g = g.difference(collar.buffer(KEEP_COLLAR + CLIP_MARGIN)).difference(weltg.buffer(KEEP_WELT + CLIP_MARGIN))
    return g
