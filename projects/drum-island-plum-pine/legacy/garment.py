"""Schematic jacket panels (size M assumption). Garment coords: x from CB/CF (mm), y down from CB collar seam."""
from shapely.geometry import Polygon, LineString
import numpy as np
from motifs import catmull

PIT = 600.0            # pit-to-pit, flat (assumed size M)
BACK_LEN = 657.0       # CB collar seam -> hem seam
RIB = 40.0
HEM_HALF = 285.0
KEEP_SEAM = 20.0       # embroidery clearance from construction seams (allowance + topstitch + 3 mm)
KEEP_HEM = 10.0

def back_panel():
    neck = catmull([(-90, -20), (-45, -4), (0, 0), (45, -4), (90, -20)], 8)
    right = catmull([(90, -20), (255, 10)], 4) + catmull([(255, 10), (272, 90), (290, 170), (300, 230)], 8)[1:] + \
            catmull([(300, 230), (285, BACK_LEN)], 4)[1:]
    left = [(-x, y) for x, y in right][::-1]
    pts = [tuple(p) for p in neck] + [tuple(p) for p in right] + [(-HEM_HALF, BACK_LEN)][:0] + [tuple(p) for p in left]
    return Polygon(pts)

def armhole_right():
    return catmull([(255, 10), (272, 90), (290, 170), (300, 230)], 8)

def svg_back(ox, oy, s, design_boxes=(), keepout=True, stroke="#333"):
    from render import f
    P = back_panel()
    T = lambda cs: " L".join(f"{f(ox + x*s)} {f(oy + y*s)}" for x, y in cs)
    o = []
    # sleeves hint
    for sx in (1, -1):
        sl = [(255*sx, 10), (315*sx, 30), (345*sx, 200), (355*sx, 330), (305*sx, 330), (300*sx, 230)]
        o.append(f'<path d="M{T(sl)} Z" fill="#F3ECE0" stroke="#BBB" stroke-width="0.2" stroke-dasharray="0.8 0.5"/>')
    o.append(f'<path d="M{T(list(P.exterior.coords))} Z" fill="#E9DCC4" stroke="{stroke}" stroke-width="0.3"/>')
    # rib
    rib = [(-HEM_HALF+12, BACK_LEN), (HEM_HALF-12, BACK_LEN), (HEM_HALF-18, BACK_LEN+RIB), (-HEM_HALF+18, BACK_LEN+RIB)]
    o.append(f'<path d="M{T(rib)} Z" fill="#E2D3B6" stroke="{stroke}" stroke-width="0.25"/>')
    for k in range(-26, 27):
        x = k*10
        o.append(f'<line x1="{f(ox+x*s)}" y1="{f(oy+(BACK_LEN+2)*s)}" x2="{f(ox+x*s)}" y2="{f(oy+(BACK_LEN+RIB-2)*s)}" stroke="#CDBB98" stroke-width="0.12"/>')
    # collar
    col = catmull([(-95, -20), (-45, -38), (0, -42), (45, -38), (95, -20)], 8)
    o.append(f'<path d="M{T(col)} L{T([(90,-20),(45,-4),(0,0),(-45,-4),(-90,-20)])} Z" fill="#5A3B2A" stroke="{stroke}" stroke-width="0.25"/>')
    if keepout:
        from shapely.geometry import box as _box
        from shapely import affinity as _aff
        inner = P.buffer(-KEEP_SEAM, join_style="mitre")
        inner = inner.union(_aff.translate(inner, 0, KEEP_SEAM - KEEP_HEM).intersection(_box(-400, 0, 400, BACK_LEN - KEEP_HEM)))
        ko = P.difference(inner)
        from render import geom_to_path
        from shapely import affinity
        g = affinity.translate(affinity.scale(ko, s, s, origin=(0, 0)), ox, oy)
        o.append(f'<path d="{geom_to_path(g)}" fill="#FF8A30" fill-opacity="0.45" fill-rule="evenodd"/>')
    o.append(f'<line x1="{f(ox)}" y1="{f(oy - 46*s)}" x2="{f(ox)}" y2="{f(oy + (BACK_LEN+RIB+10)*s)}" stroke="#0A84D6" stroke-width="0.2" stroke-dasharray="1.2 0.8"/>')
    return o
