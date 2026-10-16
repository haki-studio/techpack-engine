"""Production art export: one group per thread colour, in first-stitch order; 1 mm = 1 user unit."""
from shapely.ops import unary_union
from render import geom_to_path, f
from motifs import HEX, PAL

def thread_order(vis):
    order = []
    for z, col, g, role in vis:
        if not g.is_empty and col not in order: order.append(col)
    return order

def production_svg(vis, W, H, guides=""):
    order = thread_order(vis)
    by = {}
    for z, col, g, role in vis:
        if not g.is_empty: by.setdefault(col, []).append(g)
    body = []
    for i, col in enumerate(order, 1):
        u = unary_union(by[col])
        name = PAL[col][1].upper().replace(" ", "_")
        body.append(f'<g id="{i:02d}_{name}_{HEX[col][1:]}"><path d="{geom_to_path(u)}" fill="{HEX[col]}" fill-rule="evenodd"/></g>')
    if guides: body.append(f'<g id="99_GUIDES_do_not_stitch">{guides}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(W)}mm" height="{f(H)}mm" viewBox="0 0 {f(W)} {f(H)}">\n'
            + "\n".join(body) + "\n</svg>\n"), order
