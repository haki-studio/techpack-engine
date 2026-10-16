"""Haki — back-pocket konpeito stars: direct embroidery on back pockets. Units = mm."""
import math, base64, io
import cairosvg
from PIL import Image
from shapely.geometry import Polygon, LineString, Point
from shapely import affinity
import wb, build as B
from build import f
from spec import t, dim_h, dim_v, leader, INK, MUTED, GUIDE

PAL = wb.PAL
STAR_W = 10.0           # tip-to-tip width
SW, SH = 297.0, 210.0
RED = "#C8162B"

def cdim_h(x1, x2, y, label, col, size=2.2, tick=1.2):
    return (f'<g stroke="{col}" stroke-width="0.22"><line x1="{f(x1)}" y1="{f(y)}" x2="{f(x2)}" y2="{f(y)}"/>'
            f'<line x1="{f(x1)}" y1="{f(y-tick)}" x2="{f(x1)}" y2="{f(y+tick)}"/><line x1="{f(x2)}" y1="{f(y-tick)}" x2="{f(x2)}" y2="{f(y+tick)}"/></g>'
            + t((x1 + x2) / 2, y - 1.1, label, size, 700, col, "middle"))
def cdim_v(y1, y2, x, label, col, size=2.2, tick=1.2):
    cy = (y1 + y2) / 2
    return (f'<g stroke="{col}" stroke-width="0.22"><line x1="{f(x)}" y1="{f(y1)}" x2="{f(x)}" y2="{f(y2)}"/>'
            f'<line x1="{f(x-tick)}" y1="{f(y1)}" x2="{f(x+tick)}" y2="{f(y1)}"/><line x1="{f(x-tick)}" y1="{f(y2)}" x2="{f(x+tick)}" y2="{f(y2)}"/></g>'
            + t(x + 1.6, cy + 0.8, label, size, 700, col))

def puffy_star(cx, cy, width=STAR_W, rot=0.0, inner=0.56, tip=1.2, valley=0.8):
    D = 10.0
    R = D / 2 * 1.12
    pts = [(R if i % 2 == 0 else R * inner) for i in range(10)]
    pts = [(r * math.cos(math.radians(-90 + 36 * i)), r * math.sin(math.radians(-90 + 36 * i))) for i, r in enumerate(pts)]
    g = Polygon(pts).buffer(valley, join_style="round").buffer(-valley, join_style="round")
    g = g.buffer(-tip, join_style="round").buffer(tip, join_style="round")
    b = g.bounds
    g = affinity.scale(g, width / (b[2] - b[0]), width / (b[2] - b[0]), origin=(0, 0))
    hi = affinity.translate(affinity.scale(g, 0.5, 0.5, origin=(0, 0)), -0.45, -0.55)   # highlight, up-left
    g = affinity.rotate(g, rot, origin=(0, 0)); hi = affinity.rotate(hi, rot, origin=(0, 0))
    return affinity.translate(g, cx, cy), affinity.translate(hi, cx, cy)

STARS = {  # id: (base, tint, rotation, pocket, label)
    "STAR_Y": ("yellow", "yellow_hi", -6, "L", "Yellow star — wearer's LEFT back pocket"),
    "STAR_P": ("pink", "pink_hi", 8, "R", "Pink star — wearer's RIGHT back pocket"),
}

def art_svg():
    """Both stars at 1:1, one group per star, one sub-group per thread colour."""
    W, H = 30.0, 14.0
    body = []
    for i, (sid, (base, tint, rot, _, _)) in enumerate(STARS.items()):
        g, hi = puffy_star(8.0 + i * 14.0, 7.0, rot=rot)
        body.append(f'<g id="{sid}"><g id="{sid}_1_{base.upper()}"><path d="{wb.geom_to_path(g)}" fill="{PAL[base]}"/></g>'
                    f'<g id="{sid}_2_{tint.upper()}"><path d="{wb.geom_to_path(hi)}" fill="{PAL[tint]}"/></g></g>')
    return B.svg_doc(W, H, "\n".join(body)), (W, H)

# ---------------------------------------------------------------- schematic back pocket
PW, PH_SIDE, PH_POINT = 150.0, 152.0, 26.0     # schematic, from mockup proportions
TAPER = 12.0                                     # each side tapers in by this much at the corners
HEM = 16.0

def pocket_outline(mirror=False):
    pts = [(0, 0), (PW, 0), (PW - TAPER, PH_SIDE), (PW / 2, PH_SIDE + PH_POINT), (TAPER, PH_SIDE)]
    return Polygon(pts)

def placement(pocket, side):
    """Return star centre in pocket coordinates (finished edges)."""
    if side == "L":                    # 17 in from left side, 20 above lower-left corner
        y = PH_SIDE - 20.0
        x_edge = TAPER * y / PH_SIDE
        return x_edge + 17.0, y
    else:                              # 17 in from right side, 28 below top edge
        y = 28.0
        x_edge = PW - TAPER * y / PH_SIDE
        return x_edge - 17.0, y

def pocket_drawing(ox, oy, s, side):
    P = pocket_outline()
    T = lambda g: affinity.translate(affinity.scale(g, s, s, origin=(0, 0)), ox, oy)
    o = [f'<path d="{wb.geom_to_path(T(P))}" fill="#4A4A4E" stroke="#1E1E1E" stroke-width="0.3"/>']
    for inset, dash in ((2.0, "0.9 0.6"), (8.0, "0.9 0.6")):        # double topstitch
        ring = T(P.buffer(-inset, join_style="mitre")).exterior
        o.append(f'<path d="M{" L".join(f"{f(x)} {f(y)}" for x, y in ring.coords)}" fill="none" '
                 f'stroke="#C9B48A" stroke-width="0.35" stroke-dasharray="{dash}"/>')
    for yy in (HEM - 6, HEM):                                           # hem stitching
        o.append(f'<line x1="{f(ox + 2.5*s)}" y1="{f(oy + yy*s)}" x2="{f(ox + (PW-2.5)*s)}" y2="{f(oy + yy*s)}" '
                 f'stroke="#C9B48A" stroke-width="0.35" stroke-dasharray="0.9 0.6"/>')
    for rx in (6.0, PW - 6.0):                                          # rivets
        o.append(f'<circle cx="{f(ox + rx*s)}" cy="{f(oy + 6*s)}" r="{f(4*s)}" fill="#B8826A" stroke="#7A4E3A" stroke-width="0.2"/>')
    sid = "STAR_Y" if side == "L" else "STAR_P"
    base, tint, rot, _, _ = STARS[sid]
    cx, cy = placement(P, side)
    g, hi = puffy_star(cx, cy, rot=rot)
    o.append(f'<path d="{wb.geom_to_path(T(g))}" fill="{PAL[base]}"/><path d="{wb.geom_to_path(T(hi))}" fill="{PAL[tint]}"/>')
    # keep-out band (topstitch + 3 mm) visualised
    ko = T(P.difference(P.buffer(-11.0, join_style="mitre")))
    o.append(f'<path d="{wb.geom_to_path(ko)}" fill="#FF8A30" fill-opacity="0.62" fill-rule="evenodd"/>')
    return "\n".join(o), (cx, cy), P

def embed_png(path, crop, w_mm):
    im = Image.open(path).convert("RGB").crop(crop)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=88)
    h_mm = w_mm * im.height / im.width
    return (f'<image width="{f(w_mm)}" height="{f(h_mm)}" href="data:image/jpeg;base64,'
            f'{base64.b64encode(buf.getvalue()).decode()}"/>'), h_mm

def sheet():
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(12, 17, "HAKI — Back-pocket stars (direct embroidery)  ·  konpeito ×2", 5.0, 700))
    o.append(t(12, 23, "Embroidered directly on the two back-pocket pieces  ·  Rev A  ·  16 Oct 2026  ·  "
               "mm, finished edges  ·  art file is 1:1  ·  pairs with coin pocket + waistband Rev A", 2.5, 400, MUTED))
    o.append(f'<line x1="12" y1="27" x2="{SW-12}" y2="27" stroke="{INK}" stroke-width="0.3"/>')

    # A — star art 5:1
    ax, ay, s = 20.0, 40.0, 3.6
    o.append(t(ax, ay - 8, "A · STARS (shown 3.6:1)", 2.7, 700))
    for i, (sid, (base, tint, rot, side, label)) in enumerate(STARS.items()):
        x0 = ax + i * 58
        g, hi = puffy_star(0, 0, rot=rot)
        b = g.bounds
        T = lambda gg: affinity.translate(affinity.scale(gg, s, s, origin=(0, 0)), x0 - b[0] * s, ay - b[1] * s + 2)
        o.append(f'<path d="{wb.geom_to_path(T(g))}" fill="{PAL[base]}"/><path d="{wb.geom_to_path(T(hi))}" fill="{PAL[tint]}"/>')
        gb = T(g).bounds
        o.append(dim_h(gb[0], gb[2], gb[3] + 5, f"{f(round(b[2]-b[0],1))}", 2.2))
        o.append(dim_v(gb[1], gb[3], gb[0] - 3.5, f"{round(b[3]-b[1],1)}", 2.2))
        o.append(t(x0, gb[3] + 12, label.split(" — ")[0], 2.3, 700))
        o.append(t(x0, gb[3] + 15.5, label.split(" — ")[1], 2.1, 400, MUTED))
        o.append(t(x0, gb[3] + 19, f"rotation {rot:+d}°  ·  2 colours: {base} + {tint.replace('_hi',' tint')}", 2.0, 400, MUTED))

    # B — placement, back view
    bx, by, ps = 158.0, 39.0, 0.30
    o.append(t(bx - 6, by - 6, "B · PLACEMENT — back view (schematic pockets, 0.3:1)", 2.7, 700))
    for k, side in enumerate(("L", "R")):
        ox = bx + k * (PW * ps + 22)
        d, (cx, cy), P = pocket_drawing(ox, by, ps, side)
        o.append(d)
        o.append(t(ox + PW * ps / 2, by + (PH_SIDE + PH_POINT) * ps + 6, "wearer's LEFT pocket" if side == "L" else
                   "wearer's RIGHT pocket", 2.3, 700, anchor="middle"))
    # dimension call-outs on enlarged corner details
    o.append(t(bx - 6, by + 72, "Corner details (shown 1.5:1)", 2.3, 700))
    def corner(ox, oy, side):
        cs = 1.5
        P = pocket_outline()
        cx, cy = placement(P, side)
        if side == "L":
            rx0, ry0 = 0.0, PH_SIDE - 40.0
        else:
            rx0, ry0 = PW - 40.0, 0.0
        d, _, _ = pocket_drawing(0, 0, 1.0, side)
        out = (f'<clipPath id="c{side}"><rect x="{ox}" y="{oy}" width="{40*cs}" height="{40*cs}"/></clipPath>'
               f'<g clip-path="url(#c{side})"><rect x="{ox}" y="{oy}" width="{40*cs}" height="{40*cs}" fill="#F4F4F4"/>'
               f'<g transform="translate({ox - rx0*cs} {oy - ry0*cs}) scale({cs})">{d}</g></g>'
               f'<rect x="{ox}" y="{oy}" width="{40*cs}" height="{40*cs}" fill="none" stroke="{MUTED}" stroke-width="0.2" stroke-dasharray="1 0.7"/>')
        X = lambda x: ox + (x - rx0) * cs
        Y = lambda y: oy + (y - ry0) * cs
        if side == "L":
            xe = TAPER * cy / PH_SIDE
            out += cdim_h(X(xe), X(cx), Y(cy) - 9, "17", "#FFFFFF")
            out += cdim_v(Y(cy), Y(PH_SIDE), X(cx) + 12, "20", "#FFFFFF")
            out += f'<line x1="{f(X(cx))}" y1="{f(Y(cy))}" x2="{f(X(cx)+13)}" y2="{f(Y(cy))}" stroke="#FFFFFF" stroke-width="0.15" stroke-dasharray="0.6 0.4"/>'
            out += f'<line x1="{f(X(TAPER))}" y1="{f(Y(PH_SIDE))}" x2="{f(X(cx)+13)}" y2="{f(Y(PH_SIDE))}" stroke="#FFFFFF" stroke-width="0.15" stroke-dasharray="0.6 0.4"/>'
            out += t(ox, oy + 40 * cs + 4.5, "centre: 17 in from side edge, 20 above lower corner", 2.0)
        else:
            xe = PW - TAPER * cy / PH_SIDE
            out += cdim_h(X(cx), X(xe), Y(cy) + 10, "17", "#FFFFFF")
            out += cdim_v(Y(0), Y(cy), X(cx) - 13, "28", "#FFFFFF")
            out += f'<line x1="{f(X(cx)-13.5)}" y1="{f(Y(cy))}" x2="{f(X(cx))}" y2="{f(Y(cy))}" stroke="#FFFFFF" stroke-width="0.15" stroke-dasharray="0.6 0.4"/>'
            out += t(ox, oy + 40 * cs + 4.5, "centre: 17 in from side edge, 28 below top edge", 2.0)
        return out
    o.append(corner(bx - 6, by + 76, "L"))
    o.append(corner(bx - 6 + 40 * 1.5 + 8, by + 76, "R"))
    o.append(t(bx - 6, by + 76 + 60 + 11, "Orange = topstitch + 3 mm clearance: no embroidery. Tolerance ±2 mm, ±5°.",
               2.0, 500, "#C25000"))

    # C — mockup reference + moves
    cx0, cy0 = 16.0, 104.0
    o.append(t(cx0, cy0, "C · MOCKUP REFERENCE + WHAT CHANGED", 2.7, 700))
    img, ih = embed_png("/root/.claude/uploads/612add95-330d-55da-ab2e-88d1b06bc1d2/04af4da9-image.png",
                        (150, 380, 1420, 1030), 62)
    o.append(f'<g transform="translate({cx0} {cy0 + 3})">{img}</g>')
    notes_c = ["Mockup: yellow star sits on the double topstitch;",
               "pink star overlaps the topstitch below the rivet.",
               "Both moved ~8–10 mm inward so the pocket can be",
               "sewn without stitching through the stars.",
               "Size 10 mm (mockup reads ~10–11 mm)."]
    for i, n in enumerate(notes_c):
        o.append(t(cx0 + 65, cy0 + 7 + i * 3.6, n, 2.0))

    # D — threads + E — process
    dx, dy = 16.0, 147.0
    o.append(t(dx, dy, "D · THREADS (same codes as coin pocket / waistband)", 2.7, 700))
    for i, (k, lab) in enumerate([("yellow", "Yellow — star body"), ("yellow_hi", "Yellow tint — highlight"),
                                  ("pink", "Pink — star body"), ("pink_hi", "Pink tint — highlight")]):
        yy = dy + 4.4 + i * 3.7
        o.append(f'<rect x="{dx}" y="{f(yy-2.5)}" width="5" height="3" rx="0.4" fill="{PAL[k]}" stroke="#BDBDBD" stroke-width="0.15"/>')
        o.append(t(dx + 7, yy, lab, 2.0)); o.append(t(dx + 48, yy, PAL[k], 1.9, 400, MUTED))
        o.append(t(dx + 63, yy, "40wt polyester", 1.9, 400, MUTED))
    ex, ey = 16.0, 169.0
    o.append(t(ex, ey, "E · PROCESS NOTES", 2.7, 700))
    notes = ["Embroider flat on cut pocket pieces BEFORE hemming/attaching. Convert positions to cut-piece coordinates",
             "  using your pocket pattern (finished edge + seam/hem allowance).",
             "Satin stitch, radial per arm; tint satin on top of body. Centre-run + edge-run underlay for denim.",
             "Backing: tearaway (the pocket's inside faces the garment). Remove fully.",
             "If jeans are garment-washed after embroidery: polyester thread only (bleach-fast), and run a wash test —",
             "  enzyme/stone washing can grey yellow and pink.",
             "Sew-out on the production denim before bulk."]
    for i, n in enumerate(notes):
        o.append(t(ex, ey + 4.2 + i * 3.4, n, 1.95))
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{SW}mm" height="{SH}mm" viewBox="0 0 {SW} {SH}">' \
           + "\n".join(o) + "</svg>"

if __name__ == "__main__":
    svg, (W, H) = art_svg()
    open("out/HAKI_back-pocket-stars_ART.svg", "w").write(svg)
    cairosvg.svg2png(url="out/HAKI_back-pocket-stars_ART.svg", write_to="out/HAKI_back-pocket-stars_ART.png", output_width=int(W * 50))
    sh = sheet()
    cairosvg.svg2pdf(bytestring=sh.encode(), write_to="out/HAKI_back-pocket-stars_SPEC.pdf")
    cairosvg.svg2png(bytestring=sh.encode(), write_to="prev_spec_bs.png", output_width=2400)
    # QA
    import qa_wb as Q
    for sid, (base, tint, rot, side, _) in STARS.items():
        g, hi = puffy_star(0, 0, rot=rot)
        print(sid, "w x h", [round(v, 2) for v in (g.bounds[2]-g.bounds[0], g.bounds[3]-g.bounds[1])])
        Q.qa(sid + " body", g); Q.qa(sid + " tint", hi)
        P = pocket_outline(); cx, cy = placement(P, side)
        gg, _ = puffy_star(cx, cy, rot=rot)
        print("   clearance star→finished edge %.1f mm, → inner topstitch (8 mm) %.1f mm" %
              (P.exterior.distance(gg), P.exterior.distance(gg) - 8.0))
        if side == "R":
            print("   clearance star→rivet cap %.1f mm" % gg.distance(Point(PW - 6, 6).buffer(4)))
