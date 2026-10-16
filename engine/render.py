"""Layer stack -> SVG / PNG.  A 'stack' is a list of (layer_id, colour_key, geometry) drawn in order."""
import cairosvg
from shapely.geometry import Polygon
from motifs import HEX, FABRIC

def f(x): return f"{x:.3f}".rstrip("0").rstrip(".")

def geom_to_path(g):
    polys = []
    if g is None or g.is_empty: return ""
    if g.geom_type == "Polygon": polys = [g]
    elif hasattr(g, "geoms"): polys = [p for p in g.geoms if p.geom_type == "Polygon"]
    d = []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            cs = list(ring.coords)
            d.append("M" + " L".join(f"{f(x)} {f(y)}" for x, y in cs[:-1]) + " Z")
    return " ".join(d)

def stack_svg(stack, W, H, bg=None, extra="", guides=""):
    body = []
    if bg: body.append(f'<rect x="-50" y="-50" width="{W+100}" height="{H+100}" fill="{bg}"/>')
    for lid, col, g in stack:
        d = geom_to_path(g)
        if d: body.append(f'<g id="{lid}"><path d="{d}" fill="{HEX[col]}" fill-rule="evenodd"/></g>')
    body.append(extra); body.append(guides)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(W)}mm" height="{f(H)}mm" viewBox="0 0 {f(W)} {f(H)}">\n'
            + "\n".join(body) + "\n</svg>\n")

def png(svg, out, width):
    cairosvg.svg2png(bytestring=svg.encode(), write_to=out, output_width=int(width))
