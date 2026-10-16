"""01 Back scene v2 — 5-page digitizing spec + production files."""
import os, io, math, pickle, base64
import numpy as np
import cairosvg, cairocffi as cairo
from PIL import Image, ImageDraw
from shapely.geometry import box, Point, LineString
from shapely.ops import unary_union, transform as shp_transform
from shapely import affinity
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, dim_h, dim_v, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import geom_to_path, f
import motifs2 as M
from motifs2 import HEX, PAL
import back2 as B
import tech, stitchrender as SR

OUT = "out/01_back-scene"; os.makedirs(OUT, exist_ok=True)
D = pickle.load(open("back2_vis.pkl", "rb"))
VB, VS = D["back"], D["sleeve"]
STOPS_B, STOPS_S = tech.stops(VB), tech.stops(VS)
TOT_B, TOT_S = sum(s["st"] for s in STOPS_B), sum(s["st"] for s in STOPS_S)
TH = tech.thread_table(list(PAL))
UB = unary_union([r["geom"] for r in VB]); BB = UB.bounds
US = unary_union([r["geom"] for r in VS])
FOOT = "HAKI STUDIOS · Drum Island jacket · plum + pine · 01 back scene · Rev E · 16 Oct 2026"

def header(title, sub, page):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(12, 16, title, 4.6, 700), t(12, 21.8, sub, 2.2, 400, MUTED),
         f'<line x1="12" y1="25" x2="{SW-12}" y2="25" stroke="{INK}" stroke-width="0.3"/>', t(SW-12, 16, page, 2.4, 600, MUTED, "end"),
         t(SW-12, SH-6, FOOT, 1.9, 400, MUTED, "end")]
    return o

def img_tag(im, x, y, w_mm, q=90):
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=q)
    h = w_mm * im.height / im.width
    return f'<image x="{f(x)}" y="{f(y)}" width="{f(w_mm)}" height="{f(h)}" href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>', h

# ---------------------------------------------------------------- sleeve piece in seam coordinates
SEAM = B.ARM_R_LINE
def to_seam(x, y, z=None):
    xs = np.atleast_1d(x); ys = np.atleast_1d(y); ox, oy = [], []
    for a, b in zip(xs, ys):
        p = Point(a, b); s = SEAM.project(p); q = SEAM.interpolate(s)
        d = p.distance(q)
        ox.append(s); oy.append(d)
    return np.array(ox), np.array(oy)

def sleeve_seam_vis():
    out = []
    for r in VS:
        g = shp_transform(to_seam, r["geom"])
        out.append(dict(r, geom=g.buffer(0)))
    return out
VS_SEAM = sleeve_seam_vis()
US_SEAM = unary_union([r["geom"] for r in VS_SEAM])

def match_marks():
    """where plum limbs cross the armhole seam: arc length from shoulder point + limb width."""
    marks = []
    bark = unary_union([r["geom"] for r in B.items if r["layer"] == 5])
    inter = bark.intersection(SEAM)
    segs = [inter] if inter.geom_type == "LineString" else [g for g in getattr(inter, "geoms", []) if g.geom_type == "LineString"]
    for sgm in segs:
        a = SEAM.project(Point(sgm.coords[0])); b = SEAM.project(Point(sgm.coords[-1]))
        if abs(b - a) > 1.5: marks.append((min(a, b), max(a, b)))
    return sorted(marks)
MARKS = match_marks()

# ---------------------------------------------------------------- direction map renderer
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

# ---------------------------------------------------------------- PAGE 1 — stitch-out preview + placement
def page1():
    o = header("01 · BACK SCENE — stitch-out preview + placement",
               "Direct embroidery on the cut back panel + right sleeve, before assembly · mm, finished size · art files 1:1 · garment coords: x from CB, y down from CB collar seam", "p1 / 5")
    ppm = 3.2
    bx0, by0, bx1, by1 = -290, -20, 290, 665
    img = SR.render(VB, (bx0, by0, bx1, by1), ppm)
    mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).polygon([((x-bx0)*ppm, (y-by0)*ppm) for x, y in B.PANEL.exterior.coords], fill=255)
    bg = Image.new("RGB", img.size, (255, 255, 255)); bg.paste(img, (0, 0), mask)
    ImageDraw.Draw(bg).line([((x-bx0)*ppm, (y-by0)*ppm) for x, y in B.PANEL.exterior.coords], fill=(90, 70, 50), width=3)
    w_mm = 150; s = w_mm / (bx1 - bx0); ax, ay = 14, 31
    tag, h = img_tag(bg, ax, ay, w_mm); o.append(tag)
    X = lambda x: ax + (x - bx0)*s; Y = lambda y: ay + (y - by0)*s
    o.append(t(ax, ay + h + 4, "Stitch-out preview, back panel (shown 0.26:1). Each region is drawn with its own thread rows at its specified angle.", 1.9, 400, MUTED))
    # dims of art box
    o.append(f'<rect x="{f(X(BB[0]))}" y="{f(Y(BB[1]))}" width="{f((BB[2]-BB[0])*s)}" height="{f((BB[3]-BB[1])*s)}" fill="none" stroke="{GUIDE}" stroke-width="0.25" stroke-dasharray="1.2 0.8"/>')
    o.append(dim_h(X(BB[0]), X(BB[2]), Y(BB[1]) - 2.2, f"art {BB[2]-BB[0]:.0f}", 1.9, col=GUIDE))
    o.append(dim_v(Y(BB[1]), Y(BB[3]), X(BB[0]) - 3, f"{BB[3]-BB[1]:.0f}", 1.9, col=GUIDE))
    # right column: placement facts
    rx = 172
    o.append(t(rx, 33, "PLACEMENT", 2.6, 700))
    facts = [("Art box (back panel)", f"{BB[2]-BB[0]:.0f} × {BB[3]-BB[1]:.0f}"),
             ("Left edge → CB", f"{-BB[0]:.0f} left of CB"), ("Right edge → CB", f"{BB[2]:.0f} right of CB (runs to armhole)"),
             ("Top of art → CB collar seam", f"{BB[1]:.0f} down"), ("Bottom of art → hem seam", f"{B.HEM - BB[3]:.0f} above"),
             ("Side seams (both)", f"≥ {B.KEEP_SIDE:.0f} clear"), ("Right armhole seam", f"art stops {B.WRAP_BACK:.0f} short; continues on sleeve"),
             ("Embroidery field", f"≥ {BB[2]-BB[0]+14:.0f} × {BB[3]-BB[1]+14:.0f} border frame, or 4 × 360² splits")]
    for i, (a, b) in enumerate(facts):
        o.append(t(rx, 38 + i*3.7, a, 1.95, 400, MUTED)); o.append(t(rx + 46, 38 + i*3.7, b, 1.95, 600))
    o.append(t(rx, 72, "BY THE NUMBERS", 2.6, 700))
    import json as _j
    _r = _j.load(open("dst2_results.json")) if os.path.exists("dst2_results.json") else {}
    DB = _r.get("back", {}).get("stitches", TOT_B); DS = _r.get("sleeve", {}).get("stitches", TOT_S)
    nums = [("Stitches, back (DST v2)", f"{DB:,.0f}  · trims {_r.get('back', {}).get('trims_dst', _r.get('back', {}).get('trims_cmd', 0)):,}"), ("Stitches, sleeve (DST v2)", f"{DS:,.0f}"),
            ("Colour stops, back", f"{len(STOPS_B)}  (16 threads)"), ("Colour stops, sleeve", f"{len(STOPS_S)}"),
            ("Regions (digitizing objects)", f"{len(VB)} back + {len(VS)} sleeve"),
            ("Est. run time / head", f"≈ {DB/750/60:.1f} h at 750 spm + stops")]
    for i, (a, b) in enumerate(nums):
        o.append(t(rx, 77 + i*3.7, a, 1.95, 400, MUTED)); o.append(t(rx + 46, 77 + i*3.7, b, 1.95, 600))
    # sleeve wrap mini-map
    o.append(t(rx, 106, "SLEEVE WRAP (right sleeve, upper back of cap)", 2.6, 700))
    ms = 0.36; mx, my = rx + 4, 112
    seam_len = SEAM.length
    o.append(f'<rect x="{f(mx)}" y="{f(my)}" width="{f(seam_len*ms)}" height="{f(110*ms)}" fill="#EFE5D2" stroke="#999" stroke-width="0.2"/>')
    o.append(f'<line x1="{f(mx)}" y1="{f(my)}" x2="{f(mx + seam_len*ms)}" y2="{f(my)}" stroke="{GUIDE}" stroke-width="0.4" stroke-dasharray="1.2 0.8"/>')
    for r in VS_SEAM:
        d = geom_to_path(r["geom"])
        if d: o.append(f'<g transform="translate({f(mx)} {f(my)}) scale({ms})"><path d="{d}" fill="{HEX[r["col"]]}" fill-rule="evenodd"/></g>')
    for a, b in MARKS:
        xm = mx + (a + b)/2*ms
        o.append(f'<path d="M{f(xm-1)} {f(my-2.2)} L{f(xm+1)} {f(my-2.2)} L{f(xm)} {f(my-0.4)} Z" fill="{RED}"/>')
    o.append(t(mx, my - 3.5, "seam line (armhole), shoulder point = 0 →", 1.7, 600, GUIDE))
    o.append(t(mx, my + 110*ms + 3.5, f"x = along armhole seam from shoulder point; y = into sleeve. Red marks = limb crossings: "
               + ", ".join(f"{(a+b)/2:.0f}" for a, b in MARKS), 1.75, 400, MUTED))
    o.append(t(mx, my + 110*ms + 6.6, f"Back art stops {B.WRAP_BACK:.0f} before the seam line, sleeve art starts {B.WRAP_SLEEVE:.0f} after it → visible break ≈ {B.WRAP_BACK + B.WRAP_SLEEVE:.0f} mm.", 1.75, 400, MUTED))
    o.append(t(mx, my + 110*ms + 9.7, "Armhole topstitch must sit on the sleeve side (single needle, 2 mm) — it would otherwise cross the branches.", 1.75, 600, ORANGE))
    o.append(t(mx, my + 110*ms + 12.8, "Sleeve-cap ease: digitizer places sleeve art by these arc-length marks on the sleeve pattern, not by x/y.", 1.75, 400, MUTED))
    return o

# ---------------------------------------------------------------- PAGE 2 — stitch-direction map
def page2():
    o = header("01 · STITCH-DIRECTION MAP + REGION CODES",
               "Hatch = stitch direction of every fill/satin region (radial fans = turning fill). Dark solid = line work (bean / run). Labels = region code → stitch table p3.", "p2 / 5")
    bx0, by0, bx1, by1 = BB[0]-4, BB[1]-4, BB[2]+4, BB[3]+4
    dm = direction_map(VB, (bx0, by0, bx1, by1), 4.0)
    tag, h = img_tag(dm, 14, 29, 146, 88); o.append(tag)
    o.append(f'<rect x="14" y="29" width="146" height="{f(h)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
    # zoom crops
    zx = 168
    o.append(t(zx, 32, "DETAIL CROPS (shown 1.75:1)", 2.6, 700))
    crops = [((122, 160, 182, 190), "Blossom L + limb snow: radial satin petals, padded snow across the limb"),
             ((96, 462, 156, 492), "Red pine: turning tatami from hub, gold bean needles, padded snow cap"),
             ((-222, 590, -162, 620), "Bamboo: feather satin ±55° to the blade; snow caps vertical satin")]
    yy = 35
    for (cx0, cy0, cx1, cy1), cap in crops:
        im = direction_map(VB, (cx0, cy0, cx1, cy1), 14, label_min=12, label_mm=1.5)
        w = 98; tag, hh = img_tag(im, zx, yy, w, 90); o.append(tag)
        o.append(f'<rect x="{zx}" y="{f(yy)}" width="{w}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(zx, yy + hh + 3, cap, 1.8, 400, MUTED)); yy += hh + 6.5
    return o

# ---------------------------------------------------------------- PAGE 3 — region stitch table
def page3():
    o = header("01 · REGION STITCH TABLE — digitizing parameters per region code",
               "Density = row spacing (mm). Pull comp = added width per side (mm). Applies to back + sleeve. Codes ending in -shade / -outline / -crevice / -ridge apply to every motif that carries them.", "p3 / 5")
    stats = {}
    for r in VB + VS:
        k = tech.rule_for(r["grp"]); s = stats.setdefault(k, dict(area=0, st=0, n=0, cols=set()))
        s["area"] += r["geom"].area; s["st"] += tech.stitches(r); s["n"] += 1; s["cols"].add(r["col"])
    import json
    QA2 = json.load(open("qa2.json"))
    hdr = ["Code", "Region", "Thread(s)", "Stitch", "Angle", "Dens.", "Len.", "Underlay", "Pull", "Notes", "Width", "Obj.", "Top st."]
    cx = [12, 29, 66, 92, 124, 157, 166, 175, 214, 222, 251, 263, 272]
    y0 = 31
    for x, h in zip(cx, hdr): o.append(t(x, y0, h, 1.75, 700, MUTED))
    order = [k for k in tech.RULES if k in stats]
    rh = 3.62
    for i, k in enumerate(order):
        y = y0 + 3.6 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.5)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        name, st, ang, dens, ln, ul, pull, note = tech.RULES[k]; s = stats[k]
        o.append(t(cx[0], y, k, 1.7, 700))
        o.append(t(cx[1], y, name, 1.65))
        xs = cx[2]
        for c in sorted(s["cols"], key=lambda c: tech.COLOUR_ORDER.index(c))[:5]:
            o.append(swatch(xs, y, c, 3.2, 2.2)); xs += 4.2
        for j, v in enumerate((st, ang, dens, ln, ul, pull, note)):
            o.append(t(cx[3 + j], y, v if (j != 6 or len(v) <= 26) else v[:26].rsplit(' ', 1)[0] + '…', 1.6))
        q = QA2.get(k, {}).get("long_pct", 0.0); qc = GREEN if q < 1.0 else (ORANGE if q < 3.5 else RED)
        o.append(t(cx[10], y, f"{q:.1f}%", 1.6, 600, qc))
        o.append(t(cx[11], y, f"{s['n']}", 1.6, 400, MUTED)); o.append(t(cx[12], y, f"{s['st']:,.0f}", 1.6, 600))
    yb = y0 + 3.6 + len(order)*rh + 2
    o.append(t(cx[11] - 4, yb, "TOTAL", 1.8, 700)); o.append(t(cx[12], yb, f"{TOT_B + TOT_S:,.0f}", 1.8, 700))
    o.append(t(12, yb + 4.5, "Globals: 40wt polyester, 75/11 sharp needle, 2.5 oz cutaway backing, no topping. Satin > 7.0 wide → split satin (random). Tie-in/tie-off on every object; trims at jumps > 2.0.", 1.75, 400, MUTED))
    o.append(t(12, yb + 7.6, "Stitch counts are estimates from the art areas at these densities (±20%); the digitizer's file is the reference for the quote.", 1.75, 400, MUTED))
    o.append(t(12, yb + 10.7, "Width = share of the code's area narrower than its minimum (fill/satin 0.8, line 0.6) for > 2.5 mm, measured on the art. Green < 1%; amber = short snow/hub slivers the digitizer absorbs.", 1.75, 400, MUTED))
    return o

# ---------------------------------------------------------------- PAGE 4 — colour stops + threads
def page4():
    o = header("01 · COLOUR STOP SEQUENCE + THREADS",
               "Sewing order: back to front — mist → pine branches → red pine → white pine → plum bark → snow → leaves → blossoms → buds → bamboo. Fills before the lines that sit on them.", "p4 / 5")
    hdr = ["Stop", "Thread", "Isacord", "Madeira Polyneon", "Sews", "Top st.", "Cum."]
    cx = [12, 22, 48, 74, 102, 168, 182]
    o.append(t(12, 30.5, "BACK PANEL", 2.2, 700))
    for x, h in zip(cx, hdr): o.append(t(x, 34.5, h, 1.7, 700, MUTED))
    cum = 0; rh = 3.32
    for i, s in enumerate(STOPS_B):
        y = 38 + i*rh; cum += s["st"]
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.4)}" width="185" height="{f(rh)}" fill="#F5F2EC"/>')
        k = s["col"]; iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        o.append(t(cx[0], y, f"{i+1:02d}", 1.65, 700)); o.append(swatch(cx[1], y, k, 3.2, 2.2)); o.append(t(cx[1] + 4.2, y, PAL[k][1], 1.6))
        o.append(t(cx[2], y, f"{iso[0]} {iso[1]}", 1.55)); o.append(t(cx[3], y, f"{pn[0]} {pn[1]}", 1.55))
        sews = ", ".join(s["groups"])
        o.append(t(cx[4], y, (tech.LAYER_NAMES[s["layers"][0]] + ": " + sews)[:78], 1.5, 400, MUTED))
        o.append(t(cx[5], y, f"{s['st']:,.0f}", 1.6)); o.append(t(cx[6], y, f"{cum:,.0f}", 1.6, 400, MUTED))
    # sleeve stops (compact)
    sx = 202
    o.append(t(sx, 30.5, "SLEEVE PIECE", 2.2, 700))
    for i, s in enumerate(STOPS_S):
        y = 35 + i*3.2
        o.append(t(sx, y, f"{i+1:02d}", 1.6, 700)); o.append(swatch(sx + 5, y, s["col"], 3.2, 2.2))
        o.append(t(sx + 9.5, y, PAL[s["col"]][1], 1.6)); o.append(t(sx + 36, y, f"{s['st']:,.0f}", 1.6))
    # thread match table
    ty = 35 + len(STOPS_S)*3.2 + 6
    o.append(t(sx, ty, "THREAD MATCH (ΔE2000)", 2.2, 700))
    o.append(t(sx, ty + 3.6, "Target / Isacord / Polyneon", 1.6, 600, MUTED))
    for i, k in enumerate(PAL):
        y = ty + 7 + i*3.15
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        o.append(f'<rect x="{sx}" y="{f(y-2.3)}" width="3" height="2.4" fill="{HEX[k]}"/>')
        o.append(f'<rect x="{sx+3.3}" y="{f(y-2.3)}" width="3" height="2.4" fill="{iso[2]}"/>')
        o.append(f'<rect x="{sx+6.6}" y="{f(y-2.3)}" width="3" height="2.4" fill="{pn[2]}"/>')
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(t(sx + 11, y, f"{PAL[k][1][:13]}", 1.55))
        o.append(t(sx + 33, y, f"{iso[0]}", 1.55, 600, ci)); o.append(t(sx + 41, y, f"{iso[3]:.1f}", 1.45, 400, ci))
        o.append(t(sx + 48, y, f"{pn[0]}", 1.55, 600, cp)); o.append(t(sx + 56, y, f"{pn[3]:.1f}", 1.45, 400, cp))
    yb = ty + 7 + len(PAL)*3.15 + 2
    for i, line_ in enumerate(["ΔE < 3 green: close match. 3–5.5 amber, > 5.5 red:",
                               "pick from the physical card. Matches are from the",
                               "published chart RGB; screens and dye lots vary —",
                               "approve a thread board before sampling."]):
        o.append(t(sx, yb + i*3.2, line_, 1.6, 400, MUTED))
    return o

# ---------------------------------------------------------------- PAGE 5 — 1:1 details, what changed, production
def page5():
    o = header("01 · 1:1 DETAILS, WHAT CHANGED, PRODUCTION NOTES", "", "p5 / 5")
    o.append(t(14, 31, "1:1 STITCH-OUT DETAILS (print at 100% to check scale)", 2.6, 700))
    crops = [((124, 160, 174, 210), "Blossom L + snow on limb"), ((101, 455, 151, 505), "Red pine fan + snow cap"),
             ((-219, 580, -169, 630), "Bamboo blades + snow, trunk base"), ((-204, 503, -154, 553), "Padded trunk snow, lump contours")]
    x = 14
    for (cx0, cy0, cx1, cy1), cap in crops:
        im = SR.render(VB, (cx0, cy0, cx1, cy1), 14)
        tag, hh = img_tag(im, x, 35, cx1 - cx0); o.append(tag)
        o.append(t(x, 35 + hh + 3, cap, 1.8, 600)); x += (cx1 - cx0) + 4
    # mockup + changes
    mx = 14; my = 98
    tag, hh = SHT.embed("flat.png", (900, 140, 1730, 1000), 52, mx, my + 3); o.append(tag)
    o.append(t(mx, my, "MOCKUP", 2.4, 700))
    o.append(t(70, my, "WHAT CHANGED vs MOCKUP (and why)", 2.4, 700))
    ch = ["Composition re-traced from the mockup: same trunk line, limbs, pine",
          "  groups and bamboo; blossom + bud positions taken from the mockup.",
          "Rev E: refit to the Drum Island block (size M, boxy + cropped) — art",
          "  re-scaled into the new panel; leaves grow from the bark; bamboo on a drift.",
          "Wood drawn crooked (kinked limbs, bulging trunk) with short spray twigs,",
          "  bud clusters and snow dabs, as in the mockup.",
          "Right side: branches wrap the armhole onto the sleeve as in the mockup —",
          f"  split into a back piece + sleeve piece with match marks ({len(MARKS)} crossings).",
          "Left side: mockup twigs run over the side seam. Pulled 15 inside it",
          "  (side seams can't carry wrapped embroidery cleanly).",
          "Bottom: mockup runs into the knit rib. Stops 10 above the hem seam.",
          "Snow: mockup reads as 3D foam. Specced as padded tatami (2 padding",
          "  layers) + cream shading + grey lump contours — lift without foam.",
          "Petals: 3 tones (red body, pink rim, deep base) + gold eye, stamens,",
          "  cream anthers — as the mockup. Bark: 3 tones + crevice lines.",
          "White-pine gold fade → gold inner zone blended 2 rows into the fan.",
          "Reference images: motif language only; nothing traced from them."]
    for i, c in enumerate(ch): o.append(t(70, my + 4.5 + i*3.3, c, 1.85))
    px = 190
    o.append(t(px, my, "PRODUCTION", 2.4, 700))
    pn = [f"Field ≥ {BB[2]-BB[0]+14:.0f} × {BB[3]-BB[1]+14:.0f}: border frame, single file. If",
          "  not: 4 hoopings (360 × 360) — split files S1–S4",
          "  supplied with basting registration crosses (G5).",
          "Embroider cut back panel + cut right sleeve flat,",
          "  BEFORE yoke, side and armhole seams.",
          "Canvas: 75/11 sharp, 2.5 oz cutaway, no topping.",
          "Padded snow: digitizer to cap padding at 2 layers",
          "  (panel stiffness). Pre-shrink canvas if garment-",
          "  washed; polyester thread; wash test (enzyme/stone",
          "  greys white + gold).",
          "Lining: cut after the embroidered panel is pressed",
          "  (dense back shrinks the panel ~1.5–2.5%).",
          "Sew-out on production canvas before bulk; approve",
          "  thread board first (p4)."]
    for i, c in enumerate(pn): o.append(t(px, my + 4.5 + i*3.3, c, 1.85))
    return o

# ---------------------------------------------------------------- production SVG (regions with digitizing attributes)
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

def build():
    pages = [page1(), page2(), page3(), page4(), page5()]
    w = PdfWriter()
    for i, p in enumerate(pages, 1):
        svg = doc(p)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"q{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev2_p{i}.png", output_width=2400)
        w.append(PdfReader(f"q{i}.pdf"))
    w.write(f"{OUT}/HAKI_jacket_01_back-scene_SPEC_RevE.pdf")
    # back art: origin = art box top-left, guides = CB line + panel outline
    ox, oy = BB[0] - 5, BB[1] - 5; W, H = BB[2] - BB[0] + 10, BB[3] - BB[1] + 10
    pan = affinity.translate(B.PANEL, -ox, -oy)
    gd = (f'<path d="{geom_to_path(pan)}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
          f'<line x1="{f(-ox)}" y1="0" x2="{f(-ox)}" y2="{f(H)}" stroke="#00A3FF" stroke-width="0.3" stroke-dasharray="4 2"/>')
    open(f"{OUT}/HAKI_jacket_01_back-scene_BACK_ART.svg", "w").write(production_svg(VB, STOPS_B, W, H, ox, oy))
    open(f"{OUT}/HAKI_jacket_01_back-scene_BACK_ART+guides.svg", "w").write(production_svg(VB, STOPS_B, W, H, ox, oy, gd))
    # sleeve art in seam coordinates
    sb = US_SEAM.bounds
    vs_stops = tech.stops(VS_SEAM)
    Ws, Hs = SEAM.length + 10, sb[3] + 10
    gds = (f'<line x1="5" y1="5" x2="{f(SEAM.length + 5)}" y2="5" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>' +
           "".join(f'<path d="M{f(5 + (a+b)/2 - 2)} 0 L{f(5 + (a+b)/2 + 2)} 0 L{f(5 + (a+b)/2)} 4 Z" fill="#FF3B30"/>' for a, b in MARKS))
    open(f"{OUT}/HAKI_jacket_01_back-scene_SLEEVE_ART+guides.svg", "w").write(production_svg(VS_SEAM, vs_stops, Ws, Hs, -5, -5, gds))
    # previews
    full = SR.render(VB, (BB[0]-6, BB[1]-6, BB[2]+6, BB[3]+6), 6)
    full.save(f"{OUT}/HAKI_jacket_01_back-scene_STITCH-PREVIEW.png")
    dm = direction_map(VB, (BB[0]-4, BB[1]-4, BB[2]+4, BB[3]+4), 6)
    dm.save(f"{OUT}/HAKI_jacket_01_back-scene_DIRECTION-MAP.png")
    print("stops", len(STOPS_B), len(STOPS_S), "stitches", round(TOT_B), round(TOT_S), "marks", MARKS)

if __name__ == "__main__":
    build()
