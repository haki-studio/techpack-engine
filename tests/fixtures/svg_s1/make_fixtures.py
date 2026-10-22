"""Make the three UNSEEN S1 fixtures (ENGINE_PLAN S1 proof: a logo, lettering, a flat illustration). Drawn here from
code, so they are license-clean; the lettering uses the glyph outlines of DejaVu Sans Bold (Bitstream Vera / DejaVu
license: free to use, outlines in artwork are fine). Each file is written the way real drawing tools write SVGs, NOT the
way the founder's Konpeito files are written, so the drop-in meets what it will meet in PLM:

  logo_badge.svg        px units (400 x 400 viewBox), <style> class fills, the ring is a STROKE, arcs (A) in a path,
                        no groups, no ids
  lettering_haki.svg    "Haki Studios" as outlines (counters in a, d, o), one group, viewBox only (no width/height)
  illustration_wave.svg groups with meaningless ids, a gradient sky, a lobed cloud, wave bands, stroked crest lines and
                        birds (open paths), rounded-corner frame

  ~/.venvs/techpack/bin/python tests/fixtures/svg_s1/make_fixtures.py      (rewrites the three files next to this script)
No Anthropic API calls."""
import math, os
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))


def d_of(g, nd=2):
    out = []
    for p in ([g] if g.geom_type == "Polygon" else list(g.geoms)):
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords)[:-1]
            out.append("M" + " L".join(f"{x:.{nd}f} {y:.{nd}f}" for x, y in cs) + " Z")
    return " ".join(out)


def logo():
    # a mountain-and-sun badge: ring (stroke), sun (circle), crescent (arcs), two mountains (polygons), snow caps
    sun = '<circle class="sun" cx="200" cy="150" r="46"/>'
    crescent = '<path class="snow" d="M300 92 A34 34 0 1 0 300 160 A40 40 0 0 1 300 92 Z"/>'
    m1 = '<polygon class="rock" points="70,300 170,150 270,300"/>'
    m2 = '<polygon class="rock2" points="160,300 250,180 340,300"/>'
    cap1 = '<polygon class="snow" points="141.3,193 170,150 198.7,193 184,186 170,198 156,186"/>'
    cap2 = '<polygon class="snow" points="226,212 250,180 274,212 262,206 250,216 238,206"/>'
    ring = '<circle class="ring" cx="200" cy="200" r="170"/>'
    base = '<rect class="rock" x="60" y="300" width="280" height="22" rx="11"/>'
    css = ('<style>.ring{fill:none;stroke:#1B2A4A;stroke-width:14}.sun{fill:#F2A33A}.rock{fill:#1B2A4A}'
           '.rock2{fill:#3E5C8A}.snow{fill:#F4F1EA}</style>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="400px" height="400px" viewBox="0 0 400 400">{css}'
           f'{ring}{sun}{crescent}{m1}{m2}{cap1}{cap2}{base}</svg>')
    open(os.path.join(HERE, "logo_badge.svg"), "w").write(svg)


def lettering(text="Haki Studios"):
    from fontTools.ttLib import TTFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    font = TTFont("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    gs = font.getGlyphSet(); cmap = font.getBestCmap(); upm = font["head"].unitsPerEm
    x = 0.0; paths = []
    for ch in text:
        gname = cmap[ord(ch)]; g = gs[gname]
        pen = SVGPathPen(gs); tp = TransformPen(pen, (1, 0, 0, -1, x, upm * 0.8)); g.draw(tp)
        if pen.getCommands(): paths.append(pen.getCommands())
        x += g.width
    W = x; H = upm * 1.0
    body = "".join(f'<path d="{p}"/>' for p in paths)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
           f'<g id="Layer_1" fill="#111111">{body}</g></svg>')
    open(os.path.join(HERE, "lettering_haki.svg"), "w").write(svg)


def illustration():
    W, H = 240, 150
    frame = '<rect x="4" y="4" width="232" height="142" rx="18" fill="url(#sky)"/>'
    grad = ('<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8FC9E8"/>'
            '<stop offset="1" stop-color="#CDE8F3"/></linearGradient></defs>')
    sun = '<circle cx="182" cy="40" r="20" fill="#F7C548"/>'
    cloud = unary_union([Point(60, 46).buffer(13, quad_segs=24), Point(78, 38).buffer(16, quad_segs=24),
                         Point(98, 45).buffer(13, quad_segs=24), Point(80, 52).buffer(12, quad_segs=24)])
    cloud_p = f'<path d="{d_of(cloud)}" fill="#FFFFFF"/>'
    waves = []
    cols = ["#2D6FA3", "#1F5585", "#143D63"]
    for k, (y0, amp) in enumerate([(92, 6), (108, 7), (124, 6)]):
        top = [(x, y0 + amp * math.sin(2 * math.pi * (x / 60.0) + k)) for x in range(4, 237, 2)]
        band = Polygon(top + [(236, 146), (4, 146)])
        band = band.intersection(box(22, 22, 218, 128).buffer(18, quad_segs=16))        # the frame's rounded corners
        waves.append(f'<path d="{d_of(band)}" fill="{cols[k]}"/>')
    crest = []
    for k, (y0, amp) in enumerate([(92, 6), (108, 7)]):
        pts = [(x, y0 + amp * math.sin(2 * math.pi * (x / 60.0) + k) + 4) for x in range(30, 211, 3)]
        crest.append('<path d="M' + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + '" fill="none" stroke="#E9F4FA" '
                     'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
    birds = []
    for (bx, by, s) in [(120, 30, 1.0), (138, 22, 0.8), (150, 34, 0.7)]:
        birds.append(f'<path d="M{bx - 8 * s:.1f} {by:.1f} Q{bx - 4 * s:.1f} {by - 5 * s:.1f} {bx:.1f} {by:.1f} '
                     f'Q{bx + 4 * s:.1f} {by - 5 * s:.1f} {bx + 8 * s:.1f} {by:.1f}" fill="none" stroke="#2B2B2B" '
                     f'stroke-width="1.6" stroke-linecap="round"/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">{grad}<g id="g12">{frame}</g>'
           f'<g id="g7">{sun}{cloud_p}</g><g id="g3">{"".join(waves)}</g><g id="g9">{"".join(crest)}</g>'
           f'<g id="g4">{"".join(birds)}</g></svg>')
    open(os.path.join(HERE, "illustration_wave.svg"), "w").write(svg)


if __name__ == "__main__":
    logo(); lettering(); illustration()
    print("wrote", sorted(f for f in os.listdir(HERE) if f.endswith(".svg")))
