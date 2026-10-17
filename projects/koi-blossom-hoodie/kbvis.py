import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)
"""z-ordered knockout (higher z covers lower) — same rule as Grand Line art_size.visible."""
import shapely
from shapely.validation import make_valid
def fix(g):
    g = make_valid(g).buffer(0)
    if g.geom_type == "GeometryCollection":
        from shapely.geometry import MultiPolygon
        g = unary_union([q for q in g.geoms if q.geom_type in ("Polygon", "MultiPolygon")])
    return g
from shapely.ops import unary_union

def tidy(g):
    """drop degenerate spikes / self-touching slivers (they rotate into invalid rings in the hatchers)"""
    g = fix(g).buffer(0.03, join_style=2).buffer(-0.06, join_style=2).buffer(0.03, join_style=2)
    return fix(g.simplify(0.02))

def visible(items, clip=None, min_area=0.05):
    its = [r for r in items if clip is None or r["geom"].intersects(clip)]
    its = [dict(r, geom=fix(r["geom"])) for r in its]
    its.sort(key=lambda r: -r["z"])
    geoms = [r["geom"] for r in its]
    tree = shapely.STRtree(geoms)
    out = []
    for i, r in enumerate(its):
        g = r["geom"] if clip is None else r["geom"].intersection(clip)
        if g.is_empty: continue
        hits = [int(j) for j in tree.query(g) if int(j) < i and its[int(j)].get("ko", True)]
        if hits:
            try: g = g.difference(unary_union([geoms[j] for j in hits]))
            except Exception: g = fix(g).difference(fix(unary_union([geoms[j].buffer(0.001) for j in hits])))
        g = tidy(g)
        if not g.is_empty and g.area > min_area: out.append(dict(r, geom=g))
    out.reverse()
    return out
