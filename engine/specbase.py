"""Shared spec-page helpers for element spec sheets."""
import io, math, base64, json
import numpy as np
import cairocffi as cairo
from PIL import Image
from shapely import affinity
from sheet import t, dim_h, dim_v, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import geom_to_path, f
from motifs2 import HEX, PAL
import tech, stitchrender as SR
TH = tech.thread_table(list(PAL))
FOOT = ""
def header(title, sub, page):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(12, 16, title, 4.6, 700), t(12, 21.8, sub, 2.2, 400, MUTED),
         f'<line x1="12" y1="25" x2="{SW-12}" y2="25" stroke="{INK}" stroke-width="0.3"/>', t(SW-12, 16, page, 2.4, 600, MUTED, "end"),
         t(SW-12, SH-6, FOOT, 1.9, 400, MUTED, "end")]
    return o


def img_tag(im, x, y, w_mm, q=90):
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=q)
    h = w_mm * im.height / im.width
    return f'<image x="{f(x)}" y="{f(y)}" width="{f(w_mm)}" height="{f(h)}" href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>', h


def direction_map(vis, bbox, ppm, label_min=160, label_mm=4.2):
    x0, y0, x1, y1 = bbox
    Wp, Hp = int((x1-x0)*ppm), int((y1-y0)*ppm)
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, Wp, Hp); c = cairo.Context(surf)
    c.set_source_rgb(1, 1, 1); c.paint(); c.scale(ppm, ppm); c.translate(-x0, -y0)
    def fill(p, rgb):
        for ring in [p.exterior, *p.interiors]:
            cs = list(ring.coords); c.move_to(*cs[0])
            for q in cs[1:]: c.line_to(*q)
            c.close_path()
        c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); c.set_source_rgb(*rgb); c.fill()
    labels = []
    for r in vis:
        col = SR.hexrgb(HEX[r["col"]]); pale = tuple(0.55 + 0.45*v for v in col)
        for p in SR.polys(r["geom"]):
            if p.area < 0.05: continue
            if r["st"] in ("bean", "run"):
                fill(p, SR.shade(col, -0.35)); continue
            fill(p, pale)
            ang = r["ang"]
            if isinstance(ang, tuple): segs = SR.radial(p, ang[1], ang[2], 2.4)
            else: segs = SR.hatch(p, SR.auto_angle(p) if ang in ("auto", None) else ang, 2.2 if r["st"] != "padded" else 1.6)
            c.set_line_width(0.22 if r["st"] != "padded" else 0.32); c.set_source_rgb(*SR.shade(col, -0.45))
            for s in segs:
                cs = list(s.coords)
                if len(cs) < 2: continue
                c.move_to(*cs[0]); c.line_to(*cs[-1]); c.stroke()
            c.set_line_width(0.18); c.set_source_rgb(0.25, 0.25, 0.25)
            for ring in [p.exterior]:
                cs = list(ring.coords); c.move_to(*cs[0])
                for q in cs[1:]: c.line_to(*q)
                c.close_path(); c.stroke()
            if p.area > label_min:
                rp = p.representative_point(); labels.append((rp.x, rp.y, tech.rule_for(r["grp"])))
    # labels
    c.select_font_face("Noto Sans CJK JP", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(label_mm)
    for x, y, code in labels:
        xb, yb, ew, eh, _, _ = c.text_extents(code)
        c.set_source_rgba(1, 1, 1, 0.85); c.rectangle(x - ew/2 - 0.8, y - eh/2 - 0.8, ew + 1.6, eh + 1.6); c.fill()
        c.set_source_rgb(0.1, 0.1, 0.1); c.move_to(x - ew/2 - xb, y + eh/2); c.show_text(code)
    buf = surf.get_data()
    return Image.frombuffer("RGBA", (Wp, Hp), bytes(buf), "raw", "BGRA", 0, 1).convert("RGB")


def production_svg(vis, stops_, W, H, ox, oy, guides=""):
    idx = {id(r): i for i, r in enumerate(vis, 1)}
    body = []
    for n, s in enumerate(stops_, 1):
        k = s["col"]; iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        body.append(f'<g id="STOP{n:02d}_{PAL[k][1].replace(" ", "-")}_Isacord-{iso[0]}_Polyneon-{pn[0]}" data-hex="{HEX[k]}">')
        for r in s["regions"]:
            g = affinity.translate(r["geom"].simplify(0.03), -ox, -oy); d = geom_to_path(g)
            if not d: continue
            ang = r["ang"]
            angs = (f"radial {ang[1]-ox:.1f},{ang[2]-oy:.1f}" if isinstance(ang, tuple) else ("auto" if ang in ("auto", None) else f"{ang:.0f}"))
            body.append(f'<path id="R{idx[id(r)]:04d}" data-code="{tech.rule_for(r["grp"])}" data-stitch="{r["st"]}" data-angle="{angs}" d="{d}" fill="{HEX[k]}" fill-rule="evenodd"/>')
        body.append("</g>")
    if guides: body.append(f'<g id="99_GUIDES_do_not_stitch">{guides}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(W)}mm" height="{f(H)}mm" viewBox="0 0 {f(W)} {f(H)}">\n' + "\n".join(body) + "\n</svg>\n")

