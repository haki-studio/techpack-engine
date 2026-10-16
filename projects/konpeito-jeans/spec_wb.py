import cairosvg, re
import build as B
import wb
from spec import t, dim_h, dim_v, leader, FONT, INK, MUTED, GUIDE
from build import f

SW, SH = 297.0, 210.0
RED = "#C8162B"

def inner(svg_text):
    """strip outer <svg> wrapper so art can be nested"""
    return re.sub(r"^<svg[^>]*>|</svg>\s*$", "", svg_text.strip())

def zoom(body, w, h, rx0, ry0, rw, rh, zx, zy, zs, cid):
    return (f'<clipPath id="{cid}"><rect x="{zx}" y="{zy}" width="{rw*zs}" height="{rh*zs}"/></clipPath>'
            f'<g clip-path="url(#{cid})"><g transform="translate({zx - rx0*zs} {zy - ry0*zs}) scale({zs})">{body}</g></g>'
            f'<rect x="{zx}" y="{zy}" width="{rw*zs}" height="{rh*zs}" fill="none" stroke="{MUTED}" '
            f'stroke-width="0.2" stroke-dasharray="1 0.7"/>')

def sheet():
    L = wb.compose()
    wb_svg, wb_pitch = wb.art_svg(L, guides=True)
    wb_plain, _ = wb.art_svg(L)
    cp_plain, cp_pitch, _ = B.coin_pocket()
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(12, 17, "HAKI — Waistband patch (back)  ·  ちひろ 元気でね また会おうね 理砂", 5.0, 700))
    o.append(t(12, 23, "Embroidered sew-on patch  ·  Rev A  ·  16 Oct 2026  ·  all dimensions in mm, finished size  ·  "
               "art files are 1:1 scale  ·  pairs with coin pocket Rev A", 2.5, 400, MUTED))
    o.append(f'<line x1="12" y1="27" x2="{SW-12}" y2="27" stroke="{INK}" stroke-width="0.3"/>')

    # A — art
    s, ax, ay = 2.0, 26.0, 41.0
    o.append(t(ax, ay - 8.5, "A · PATCH (shown 2:1)", 2.7, 700))
    o.append(f'<g transform="translate({ax} {ay}) scale({s})">{inner(wb_svg)}</g>')
    o.append(dim_h(ax, ax + wb.W * s, ay - 3.2, f"{f(wb.W)}"))
    o.append(dim_v(ay, ay + wb.H * s, ax - 4.5, f"{f(wb.H)}"))
    o.append(dim_h(ax + (wb.W - B.BORDER) * s, ax + wb.W * s, ay + wb.H * s + 4.5, f"{B.BORDER}"))
    o.append(t(ax, ay + wb.H * s + 4.0, "No rivets — flower on all four corners. Stitch to waistband through the band "
               "just inside the satin edge (blue dashed).", 2.1, 400, MUTED))

    # E — stitch check table
    ty = 166.0
    o.append(t(ax, ty, "E · STITCH-CHECK AT REAL SIZE (measured on the art files)", 2.7, 700))
    hdr = ["Element", "Size", "Stitch / thread", "Min stroke", "Min counter", "Parts ≥ gap", "Result"]
    cx = [ax, ax + 34, ax + 52, ax + 88, ax + 108, ax + 129, ax + 150]
    for x, h in zip(cx, hdr):
        o.append(t(x, ty + 5, h, 2.0, 700, MUTED))
    rows = [
        ("元気でね / また会おうね", "6.7 tall", "satin, 60wt black", "≥0.6", "0.65", "≥0.35", "PASS"),
        ("ちひろ", "5.4 tall", "satin, 40wt red", "≥0.8", "—", "≥0.5", "PASS"),
        ("理砂 (hand-lettered)", "7.9 tall", "satin 0.95, 40wt blue", "0.95", "0.80", "≥0.5", "PASS"),
        ("Face line art", "0.7 lines", "triple-run (bean), 60wt", "0.7", "—", "≥0.35", "PASS"),
        ("Hearts / frame", "1.15 / 1.0", "satin, 40wt", "1.0", "2.1", "≥0.5", "PASS"),
    ]
    for i, r in enumerate(rows):
        yy = ty + 9.5 + i * 3.9
        for x, v in zip(cx, r):
            o.append(t(x, yy, v, 2.0, 700 if v == "PASS" else 400, "#1E8E3E" if v == "PASS" else INK))

    # B — border match
    zx, zy, zs = 204.0, 41.0, 2.9
    rw, rh = 13.0, 12.0
    o.append(t(zx, zy - 8.5, "B · BORDER MATCH (both shown 2.9:1)", 2.7, 700))
    o.append(t(zx, zy - 4.5, "Same component, same mm, same threads on both patches", 2.1, 500, RED))
    o.append(zoom(inner(wb_plain), wb.W, wb.H, 0, wb.H - rh, rw, rh, zx, zy, zs, "z1"))
    o.append(zoom(cp_plain, B.W, B.H, 0, B.H - rh, rw, rh, zx + rw * zs + 3, zy, zs, "z2"))
    by = zy + rh * zs
    for k, lab in ((0, "Waistband"), (1, "Coin pocket")):
        x0 = zx + k * (rw * zs + 3)
        o.append(dim_h(x0, x0 + B.BORDER * zs, by + 3.6, "6.5", 2.0, 1.0))
        o.append(t(x0, by + 8.6, lab, 2.2, 700))
    # numbers table
    ny = by + 15
    o.append(t(zx, ny, "Measured from art files", 2.0, 700, MUTED))
    o.append(t(zx + 48, ny, "Waistband", 2.0, 700, MUTED))
    o.append(t(zx + 68, ny, "Coin pocket", 2.0, 700, MUTED))
    tab = [("Satin edge", "2.0", "2.0"), ("Flower band", "4.5", "4.5"), ("Border total, L/R/T/B", "6.5 ×4", "6.5 ×4"),
           ("Flower Ø / dot Ø", "4.0 / 1.5", "4.0 / 1.5"),
           ("Pitch H / V (5.8 ±0.2)", f"{wb_pitch[0]:.2f} / {wb_pitch[1]:.2f}", f"{cp_pitch[0]:.2f} / {cp_pitch[1]:.2f}"),
           ("Corner radius", "R2.5", "R2.5"), ("Edge finish", "heat-cut", "heat-cut"),
           ("Corners", "4 flowers", "2 + 2 rivet")]
    for i, (a, b1, c1) in enumerate(tab):
        yy = ny + 4.2 + i * 3.6
        o.append(t(zx, yy, a, 2.0)); o.append(t(zx + 48, yy, b1, 2.0, 500)); o.append(t(zx + 68, yy, c1, 2.0, 500))

    # C — threads
    cy0 = 136.0
    o.append(t(zx, cy0, "C · THREADS (shared palette with coin pocket)", 2.7, 700))
    cols = [("red", "Red — edge, band, frame, ちひろ, dots", "40wt"), ("cream", "Cream — field", "40wt"),
            ("white", "White — border motifs, flower centres", "40wt"), ("black", "Black — lettering, face", "60wt"),
            ("pink", "Pink — hearts, flowers", "40wt"), ("rose", "Rose — cheeks", "40wt"),
            ("yellow", "Yellow — flower", "40wt"), ("blue", "Blue — flower, 理砂", "40wt")]
    for i, (k, lab, wt) in enumerate(cols):
        yy = cy0 + 4.4 + i * 3.7
        o.append(f'<rect x="{zx}" y="{f(yy-2.5)}" width="5" height="3.0" rx="0.4" fill="{wb.PAL[k]}" '
                 f'stroke="#BDBDBD" stroke-width="0.15"/>')
        o.append(t(zx + 7, yy, lab, 2.0)); o.append(t(zx + 60, yy, wb.PAL[k], 1.9, 400, MUTED))
        o.append(t(zx + 75, yy, wt, 1.9, 700 if wt == "60wt" else 400, RED if wt == "60wt" else MUTED))

    # D — notes
    ny2 = 172.0 + 4
    o.append(t(zx, ny2 + 0, "D · NOTES", 2.7, 700))
    notes = ["Black lettering in 60wt — at 6.7 mm, 40wt fills 気/会.",
             "Do not re-set the text from a font; digitize from these outlines.",
             "理砂 is hand-drawn so its counters stay open — keep spacing.",
             "Sew-out approval required before bulk.",
             "Blue dashed line = guide only, not stitched."]
    for i, n in enumerate(notes):
        o.append(t(zx, ny2 + 4.2 + i * 3.5, f"{i+1}. {n}", 1.95))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW}mm" height="{SH}mm" viewBox="0 0 {SW} {SH}">' \
           + "\n".join(o) + "</svg>"

if __name__ == "__main__":
    svg = sheet()
    cairosvg.svg2pdf(bytestring=svg.encode(), write_to="out/HAKI_waistband-patch_SPEC.pdf")
    cairosvg.svg2png(bytestring=svg.encode(), write_to="prev_spec_wb.png", output_width=2400)
    cairosvg.svg2png(url="out/HAKI_waistband-patch_ART.svg", write_to="out/HAKI_waistband-patch_ART.png",
                     output_width=int(wb.W * 50))
