import cairosvg
import build as B
from build import f, C

SW, SH = 297.0, 210.0
FONT = "Noto Sans CJK JP"
INK, MUTED, GUIDE, RIV = "#1A1A1A", "#6B6B6B", "#00A3FF", "#FF6A00"

def t(x, y, s, size=2.6, w=400, fill=INK, anchor="start"):
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{FONT}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}" text-anchor="{anchor}">{s}</text>')

def dim_h(x1, x2, y, label, size=2.4, tick=1.4):
    return (f'<g stroke="{INK}" stroke-width="0.18"><line x1="{f(x1)}" y1="{f(y)}" x2="{f(x2)}" y2="{f(y)}"/>'
            f'<line x1="{f(x1)}" y1="{f(y-tick)}" x2="{f(x1)}" y2="{f(y+tick)}"/>'
            f'<line x1="{f(x2)}" y1="{f(y-tick)}" x2="{f(x2)}" y2="{f(y+tick)}"/></g>'
            + t((x1 + x2) / 2, y - 1.2, label, size, 500, anchor="middle"))

def dim_v(y1, y2, x, label, size=2.4, tick=1.4):
    cy = (y1 + y2) / 2
    return (f'<g stroke="{INK}" stroke-width="0.18"><line x1="{f(x)}" y1="{f(y1)}" x2="{f(x)}" y2="{f(y2)}"/>'
            f'<line x1="{f(x-tick)}" y1="{f(y1)}" x2="{f(x+tick)}" y2="{f(y1)}"/>'
            f'<line x1="{f(x-tick)}" y1="{f(y2)}" x2="{f(x+tick)}" y2="{f(y2)}"/></g>'
            f'<text x="{f(x-1.4)}" y="{f(cy)}" font-family="{FONT}" font-size="{size}" font-weight="500" '
            f'fill="{INK}" text-anchor="middle" transform="rotate(-90 {f(x-1.4)} {f(cy)})">{label}</text>')

def leader(x1, y1, x2, y2, label, anchor="start", size=2.3):
    dx = 1.0 if anchor == "start" else -1.0
    return (f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{INK}" stroke-width="0.15"/>'
            f'<circle cx="{f(x1)}" cy="{f(y1)}" r="0.45" fill="{INK}"/>'
            + t(x2 + dx, y2 + 0.8, label, size, 400, anchor=anchor))

def sheet():
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    # header
    o.append(t(12, 17, "HAKI — Coin pocket front  ·  こんぺいとう (konpeito)", 5.2, 700))
    o.append(t(12, 23, "Embroidered sew-on patch used as coin pocket  ·  Rev A  ·  16 Oct 2026  ·  "
               "all dimensions in mm, finished size  ·  art files are 1:1 scale", 2.5, 400, MUTED))
    o.append(f'<line x1="12" y1="27" x2="{SW-12}" y2="27" stroke="{INK}" stroke-width="0.3"/>')

    # main art, scale 2.15
    s, ax, ay = 2.0, 26.0, 40.0
    art, _, _ = B.coin_pocket(guides=True)
    o.append(f'<g transform="translate({ax} {ay}) scale({s})">{art}</g>')
    o.append(t(ax, ay - 9.5, "A · POCKET FRONT (shown 2:1)", 2.7, 700))
    o.append(dim_h(ax, ax + B.W * s, ay - 3.5, f"{f(B.W)}"))
    o.append(dim_v(ay, ay + B.H * s, ax - 4.5, f"{f(B.H)}"))
    o.append(dim_h(ax + (B.W - B.BORDER) * s, ax + B.W * s, ay + B.H * s + 4.5, f"{B.BORDER}"))
    c = B.EDGE + B.BAND / 2
    o.append(t(ax, ay + B.H * s + 10.0, "Orange = rivets at both top corners: cap Ø8, centred 4.25 / 4.25 from edges "
               "— no motifs in rivet zone.", 2.2, 500, RIV))
    o.append(t(ax, ay + B.H * s + 13.8, "Pocket opening = top edge. Stitch to garment on sides + bottom, "
               "through the band just inside the satin edge (blue dashed).", 2.2, 400, MUTED))

    # facing
    fs, fx, fy = 1.75, 26.0, 178.0
    o.append(t(fx, fy - 7, "B · KONPEITO ON FRONT-POCKET FACING (66 wide, shown 1.75:1)  —  embroider direct on facing "
               "before coin pocket is attached", 2.7, 700))
    o.append(f'<g transform="translate({fx} {fy}) scale({fs})">{B.facing()}{B.facing_guides()}</g>')
    o.append(t(fx + B.FW * fs + 6, fy + B.POCKET_LINE * fs + 0.8,
               "coin pocket top edge lands here", 2.2, 500, GUIDE))
    o.append(t(fx + B.FW * fs + 6, fy + B.POCKET_LINE * fs + 4.4,
               "pink back row stitched first", 2.2, 400, MUTED))

    # border detail — bottom-left corner zoom
    zx, zy, zs = 206.0, 40.0, 3.6
    rx0, ry0, rw, rh = 0.0, B.H - 13.4, 18.0, 13.4
    o.append(t(zx, zy - 7.5, "C · SHARED BORDER SPEC (shown 3.6:1)", 2.7, 700))
    o.append(t(zx, zy - 3.0, "Identical on waistband patch — fixed mm, never % of patch", 2.2, 500, "#C8162B"))
    art_plain, _, _ = B.coin_pocket(guides=False)
    o.append(f'<clipPath id="zc"><rect x="{zx}" y="{zy}" width="{rw*zs}" height="{rh*zs}"/></clipPath>'
             f'<g clip-path="url(#zc)"><g transform="translate({zx - rx0*zs} {zy - ry0*zs}) scale({zs})">'
             f'{art_plain}</g></g>'
             f'<rect x="{zx}" y="{zy}" width="{rw*zs}" height="{rh*zs}" fill="none" stroke="{MUTED}" '
             f'stroke-width="0.2" stroke-dasharray="1 0.7"/>')
    by = zy + rh * zs          # outer bottom edge on sheet
    # edge/band dims along bottom
    o.append(dim_h(zx, zx + B.EDGE * zs, by + 4.0, "2.0", 2.2))
    o.append(dim_h(zx + B.EDGE * zs, zx + B.BORDER * zs, by + 4.0, "4.5", 2.2))
    o.append(dim_h(zx, zx + B.BORDER * zs, by + 10.0, "6.5 total", 2.2))
    o.append(t(zx + B.BORDER * zs + 3, by + 4.6, "satin edge  |  tatami band", 2.0, 400, MUTED))
    # flower & dot callouts (left side motifs)
    fy_corner = B.H - c
    fl_y = zy + (fy_corner - ry0) * zs
    fl_x = zx + c * zs
    dot_y = zy + (fy_corner - 5.94 - ry0) * zs
    lx = zx + (B.BORDER + 1.6) * zs
    fl_top = zy + 1.0
    o.append(t(lx, zy + 5.0, "flower → dot pitch 5.8 ±0.2", 2.1, 500))
    o.append(t(lx, zy + 8.2, "(this piece: 5.62 H / 5.94 V)", 1.9, 400, MUTED))
    o.append(leader(fl_x, dot_y, lx, zy + 15.0, "dot Ø1.5", "start", 2.1))
    o.append(leader(fl_x + 1.4, fl_y - 1.6, lx, zy + 22.0, "flower Ø4.0, 5 satin petals", "start", 2.1))
    o.append(dim_v(dot_y, fl_y, zx - 3.0, "pitch", 1.9, 1.0))

    # colours
    cy0 = 112.0
    o.append(t(zx, cy0, "D · THREAD COLOURS (match to approved swatch)", 2.7, 700))
    rows = [("red", "Red — edge, band, lettering, accent dots", True),
            ("cream", "Cream — field", True),
            ("white", "White — border motifs, sparkles", True),
            ("pink", "Pink", False), ("pink_hi", "Pink tint", False),
            ("yellow", "Yellow", False), ("yellow_hi", "Yellow tint", False),
            ("blue", "Blue", False), ("blue_hi", "Blue tint", False)]
    for i, (k, label, shared) in enumerate(rows):
        yy = cy0 + 4.5 + i * 4.1
        o.append(f'<rect x="{zx}" y="{f(yy-2.6)}" width="5" height="3.2" rx="0.4" fill="{C[k]}" '
                 f'stroke="#BDBDBD" stroke-width="0.15"/>')
        o.append(t(zx + 7, yy, label, 2.2))
        o.append(t(zx + 58, yy, C[k], 2.1, 400, MUTED))
        if shared:
            o.append(t(zx + 71, yy, "= WB", 2.0, 700, "#C8162B"))
    o.append(t(zx, cy0 + 42, "= WB: same thread code + density as the waistband patch", 2.0, 400, MUTED))

    # notes
    ny = 165.0
    notes = [
        "Edge: heat/laser-cut, 2.0 satin, R2.5 corners. Sew-on, no adhesive backing.",
        "Field coverage: same as waistband patch (both full-fill, or both on cream twill).",
        "Lettering supplied as outlines — keep the small ring on ぺ open, not filled.",
        "Min detail: sparkle dots Ø1.1, lettering 10.5 high. Do not shrink.",
        "Every corner gets a flower, except rivet corners (plain red).",
        "Blue/orange lines on art = guides only, not stitched.",
    ]
    o.append(t(zx, ny, "E · NOTES", 2.7, 700))
    for i, n in enumerate(notes):
        o.append(t(zx, ny + 4.3 + i * 3.6, f"{i+1}. {n}", 2.0))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW}mm" height="{SH}mm" viewBox="0 0 {SW} {SH}">' \
           + "\n".join(o) + "</svg>"

if __name__ == "__main__":
    svg = sheet()
    open("out/HAKI_coin-pocket_konpeito_SPEC.svg", "w").write(svg)
    cairosvg.svg2pdf(bytestring=svg.encode(), write_to="out/HAKI_coin-pocket_konpeito_SPEC.pdf")
    cairosvg.svg2png(bytestring=svg.encode(), write_to="prev_spec.png", output_width=2400)
    # production rasters, 50 px/mm (1270 dpi), transparent bg
    cairosvg.svg2png(url="out/HAKI_coin-pocket_konpeito_ART.svg",
                     write_to="out/HAKI_coin-pocket_konpeito_ART.png", output_width=int(B.W * 50))
    cairosvg.svg2png(url="out/HAKI_facing_konpeito_ART.svg",
                     write_to="out/HAKI_facing_konpeito_ART.png", output_width=int(B.FW * 50))
