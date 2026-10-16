"""Generic element spec (5 pages) for front elements 02-04."""
import os, json, pickle
import numpy as np
import cairosvg
from PIL import Image, ImageDraw
from shapely.geometry import box, Point, LineString
from shapely.ops import unary_union
from shapely import affinity
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, dim_h, dim_v, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import geom_to_path, f
from motifs2 import HEX, PAL, FABRIC
import tech, stitchrender as SR, qa
import specbase as SB
from specbase import img_tag, direction_map, header

def width_check(vis):
    groups = {}
    for r in vis: groups.setdefault(tech.rule_for(r["grp"]), []).append(r)
    out = {}
    for code, rs in groups.items():
        line = rs[0]["st"] in ("bean", "run")
        u = unary_union([r["geom"] for r in rs]); parts = [u] if u.geom_type == "Polygon" else list(u.geoms)
        A = L = 0.0
        for p in parts:
            if p.area < 0.05: continue
            res = qa.check_geom(p, 0.6 if line else 0.8, 0.35 if line else 0.5, 0.45 if line else 0.6)
            if res: A += res["area"]; L += res["long_area"]
        out[code] = 100*L/max(A, 1e-9)
    return out

def front_view_png(F, vis_all, bbox, ppm, highlight):
    """stitch render on top of a drawn front view (panels, collar, zip, welts)."""
    x0, y0, x1, y1 = bbox
    img = SR.render([r for p in highlight for r in vis_all[p]], bbox, ppm)
    W, H = img.size
    mask = Image.new("L", (W, H), 0); d = ImageDraw.Draw(mask)
    T = lambda cs: [((x - x0)*ppm, (y - y0)*ppm) for x, y in cs]
    for pnl in (F.PANEL_R, F.PANEL_L): d.polygon(T(pnl.exterior.coords), fill=255)
    out = Image.new("RGB", (W, H), (255, 255, 255)); out.paste(img, (0, 0), mask)
    # faded non-highlighted pieces
    others = [p for p in vis_all if p not in highlight]
    if others:
        oimg = SR.render([r for p in others for r in vis_all[p]], bbox, ppm)
        fade = Image.blend(oimg, Image.new("RGB", (W, H), (235, 228, 214)), 0.72)
        om = Image.new("L", (W, H), 0); ImageDraw.Draw(om).bitmap((0, 0), Image.new("1", (W, H), 0))
        um = unary_union([r["geom"] for p in others for r in vis_all[p]]).buffer(1.0)
        md = ImageDraw.Draw(om)
        for pg in SR.polys(um): md.polygon(T(pg.exterior.coords), fill=255)
        out.paste(fade, (0, 0), om)
    d = ImageDraw.Draw(out)
    for c in (F.COLLAR_R, F.COLLAR_L): d.line(T(c.exterior.coords), fill=(110, 80, 60), width=2)
    for w in (F.WELT_R, F.WELT_L): d.polygon(T(w.exterior.coords), outline=(120, 100, 70), fill=(200, 180, 140))
    d.rectangle([((-6 - x0)*ppm, (0 - y0)*ppm), ((6 - x0)*ppm, (F.HEM - y0)*ppm)], fill=(150, 118, 60))
    for pnl in (F.PANEL_R, F.PANEL_L): d.line(T(pnl.exterior.coords), fill=(90, 70, 50), width=3)
    return out

def build(cfg, F, vis_all):
    SB.FOOT = f"HAKI STUDIOS · Drum Island jacket · plum + pine · {cfg["id"]} {cfg["short"]} · Rev B · 16 Oct 2026"
    OUT = f"out/{cfg['id']}_{cfg['slug']}"; os.makedirs(OUT, exist_ok=True)
    pieces = cfg["pieces"]
    V = {p: vis_all[p] for p in pieces}
    ALL = [r for p in pieces for r in V[p]]
    STOPS = {p: tech.stops(V[p]) for p in pieces}
    TOT = {p: sum(s["st"] for s in STOPS[p]) for p in pieces}
    _r = json.load(open("dst2_results.json")) if os.path.exists("dst2_results.json") else {}
    DSTN = {p: _r[p]["stitches"] for p in pieces if p in _r}
    BBs = {p: unary_union([r["geom"] for r in V[p]]).bounds for p in pieces}
    UB = unary_union([r["geom"] for r in ALL]).bounds
    WC = width_check(ALL)
    n = cfg["id"]; P = "5"

    # ---------------- p1 preview + placement
    o = header(f"{n} · {cfg['title']} — stitch-out preview + placement", cfg["sub"], "p1 / 5")
    bbox = (-325, -25, 325, 625); ppm = 2.6
    fv = front_view_png(F, vis_all, bbox, ppm, pieces)
    w_mm = 152; s = w_mm / (bbox[2] - bbox[0]); ax, ay = 12, 29
    tag, h = img_tag(fv, ax, ay, w_mm); o.append(tag)
    X = lambda x: ax + (x - bbox[0])*s; Y = lambda y: ay + (y - bbox[1])*s
    for p in pieces:
        b = BBs[p]
        o.append(f'<rect x="{f(X(b[0]))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{GUIDE}" stroke-width="0.25" stroke-dasharray="1.2 0.8"/>')
        o.append(t(X(b[0]) + 0.6, Y(b[1]) - 0.9, f"{p}: {b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.7, 700, GUIDE))
    o.append(t(ax, ay + h + 3.5, "Front view, size M (shown 0.23:1). Highlighted = this element; faded = other front elements. Brown = collar outline, zip at CF.", 1.8, 400, MUTED))
    rx = 172
    o.append(t(rx, 33, "PLACEMENT (garment coords: x from CF, + = wearer's left; y down from CF neck seam)", 2.2, 700))
    yy = 38
    for a_, b_ in cfg["placement"](BBs):
        o.append(t(rx, yy, a_, 1.9, 400, MUTED)); o.append(t(rx + 50, yy, b_, 1.9, 600)); yy += 3.6
    yy += 3
    o.append(t(rx, yy, "BY THE NUMBERS", 2.4, 700)); yy += 4.6
    for p in pieces:
        o.append(t(rx, yy, f"Piece {p}", 1.9, 400, MUTED)); o.append(t(rx + 50, yy, f"{DSTN.get(p, TOT[p]):,.0f} stitches (DST v2) · {len(STOPS[p])} stops · {len(V[p])} objects", 1.9, 600)); yy += 3.6
    o.append(t(rx, yy, "Est. run time / head", 1.9, 400, MUTED)); o.append(t(rx + 50, yy, f"≈ {sum(DSTN.get(p, TOT[p]) for p in pieces)/750:.0f} min at 750 spm + stops", 1.9, 600)); yy += 6
    for line_ in cfg.get("p1_notes", []):
        col = ORANGE if line_.startswith("!") else MUTED
        o.append(t(rx, yy, line_.lstrip("!"), 1.8, 600 if col == ORANGE else 400, col)); yy += 3.3
    if cfg.get("marks"):
        yy += 2; o.append(t(rx, yy, "ZIP MATCH MARKS (main limb at the zip keep-out line)", 2.2, 700)); yy += 4.2
        for xx, a, b in cfg["marks"]:
            o.append(t(rx, yy, f"x = {xx:+.0f}", 1.9, 600)); o.append(t(rx + 18, yy, f"limb from y {a:.0f} to {b:.0f}  (centre {0.5*(a+b):.0f})", 1.9)); yy += 3.4
    pages = [o]

    # ---------------- p2 direction map
    o = header(f"{n} · STITCH-DIRECTION MAP + REGION CODES", "Hatch = stitch direction (radial = turning fill). Dark solid = line work (bean / run). Labels = region code → stitch table p3.", "p2 / 5")
    xcur = 12
    widths = [(BBs[p][2]-BBs[p][0]) for p in pieces]; scale = min(160 / max(BBs[p][3]-BBs[p][1] for p in pieces), (172 - 6*(len(pieces)-1)) / sum(widths))
    for p in pieces:
        b = BBs[p]; bb = (b[0]-3, b[1]-3, b[2]+3, b[3]+3)
        dm = direction_map(V[p], bb, 5.0, label_min=40, label_mm=2.4)
        wmm = (bb[2]-bb[0])*scale; tag, hh = img_tag(dm, xcur, 30, wmm, 88); o.append(tag)
        o.append(f'<rect x="{f(xcur)}" y="30" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(xcur, 30 + hh + 3.2, f"Piece {p} (shown {scale:.2f}:1)", 1.9, 700)); xcur += wmm + 6
    zx = 192; o.append(t(zx, 32, "DETAIL CROPS (shown 2:1)", 2.4, 700)); yy = 35
    for (c, cap) in cfg["dm_crops"]:
        im = direction_map(ALL, c, 14, label_min=30, label_mm=1.2)
        wmm = (c[2]-c[0])*2; tag, hh = img_tag(im, zx, yy, wmm, 90); o.append(tag)
        o.append(f'<rect x="{zx}" y="{f(yy)}" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(zx, yy + hh + 3, cap, 1.75, 400, MUTED)); yy += hh + 6.5
    pages.append(o)

    # ---------------- p3 region table
    o = header(f"{n} · REGION STITCH TABLE — digitizing parameters per region code",
               "Same parameters as element 01 (shared system). Density = row spacing (mm). Pull comp = added width per side (mm). Width = measured share below minimum.", "p3 / 5")
    stats = {}
    for r in ALL:
        k = tech.rule_for(r["grp"]); st_ = stats.setdefault(k, dict(st=0, n=0, cols=set()))
        st_["st"] += tech.stitches(r); st_["n"] += 1; st_["cols"].add(r["col"])
    hdr = ["Code", "Region", "Thread(s)", "Stitch", "Angle", "Dens.", "Len.", "Underlay", "Pull", "Notes", "Width", "Obj.", "Top st."]
    cx = [12, 29, 66, 92, 124, 157, 166, 175, 214, 222, 251, 263, 272]
    y0 = 31
    for x, hd in zip(cx, hdr): o.append(t(x, y0, hd, 1.75, 700, MUTED))
    order = [k for k in tech.RULES if k in stats]; rh = 3.62
    for i, k in enumerate(order):
        y = y0 + 3.6 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.5)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        name, st, ang, dens, ln, ul, pull, note = tech.RULES[k]; s_ = stats[k]
        o.append(t(cx[0], y, k, 1.7, 700)); o.append(t(cx[1], y, name, 1.65))
        xs = cx[2]
        for c in sorted(s_["cols"], key=lambda c: tech.COLOUR_ORDER.index(c))[:5]:
            o.append(swatch(xs, y, c, 3.2, 2.2)); xs += 4.2
        for j, v in enumerate((st, ang, dens, ln, ul, pull, note)):
            o.append(t(cx[3 + j], y, v if (j != 6 or len(v) <= 26) else v[:26].rsplit(' ', 1)[0] + '…', 1.6))
        q = WC.get(k, 0.0); qc = GREEN if q < 1.0 else (ORANGE if q < 3.5 else RED)
        o.append(t(cx[10], y, f"{q:.1f}%", 1.6, 600, qc))
        o.append(t(cx[11], y, f"{s_['n']}", 1.6, 400, MUTED)); o.append(t(cx[12], y, f"{s_['st']:,.0f}", 1.6, 600))
    yb = y0 + 3.6 + len(order)*rh + 2
    o.append(t(cx[11] - 4, yb, "TOTAL", 1.8, 700)); o.append(t(cx[12], yb, f"{sum(TOT.values()):,.0f}", 1.8, 700))
    o.append(t(12, yb + 4.5, "Globals: 40wt polyester, 75/11 sharp needle, 2.5 oz cutaway backing, no topping. Satin > 7.0 wide → split satin. Tie-in/off every object; trim jumps > 2.0.", 1.75, 400, MUTED))
    o.append(t(12, yb + 7.6, "Stitch counts are estimates from art areas at these densities (±20%); the digitizer's file is the reference for the quote.", 1.75, 400, MUTED))
    pages.append(o)

    # ---------------- p4 colour stops
    o = header(f"{n} · COLOUR STOP SEQUENCE + THREADS", "Back to front: mist → branches → pine → bark → snow → leaves → blossoms → buds → bamboo. Fills before the lines that sit on them. Thread codes = shared jacket palette.", "p4 / 5")
    colx = [12, 150] if len(pieces) == 2 else [12]
    for ci, p in enumerate(pieces):
        x0 = colx[ci]
        o.append(t(x0, 30.5, f"PIECE {p}", 2.2, 700))
        hc = [x0, x0 + 9, x0 + 34, x0 + 58, x0 + 84, x0 + 112]
        for x, hd in zip(hc, ["Stop", "Thread", "Isacord", "Polyneon", "Sews", "Stitches"]): o.append(t(x, 34.5, hd, 1.65, 700, MUTED))
        rh = min(3.3, 150 / max(1, len(STOPS[p])))
        for i, s_ in enumerate(STOPS[p]):
            y = 38 + i*rh; k = s_["col"]; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
            if i % 2 == 0: o.append(f'<rect x="{x0-1}" y="{f(y-2.4)}" width="134" height="{f(rh)}" fill="#F5F2EC"/>')
            o.append(t(hc[0], y, f"{i+1:02d}", 1.6, 700)); o.append(swatch(hc[1], y, k, 3.2, 2.2)); o.append(t(hc[1] + 4.2, y, PAL[k][1], 1.55))
            o.append(t(hc[2], y, f"{iso[0]} {iso[1]}"[:20], 1.5)); o.append(t(hc[3], y, f"{pn[0]} {pn[1]}"[:20], 1.5))
            o.append(t(hc[4], y, ", ".join(s_["groups"])[:22], 1.45, 400, MUTED)); o.append(t(hc[5], y, f"{s_['st']:,.0f}", 1.55))
    if len(pieces) == 1:
        sx = 160; used = sorted({r["col"] for r in ALL}, key=lambda c: tech.COLOUR_ORDER.index(c))
        o.append(t(sx, 30.5, "THREADS USED (ΔE2000 to target)", 2.2, 700))
        for i, k in enumerate(used):
            y = 36 + i*3.3; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
            o.append(swatch(sx, y, k, 3.2, 2.2)); o.append(t(sx + 5, y, PAL[k][1], 1.6))
            o.append(t(sx + 30, y, f"Isacord {iso[0]}  ΔE {iso[3]:.1f}", 1.55)); o.append(t(sx + 62, y, f"Polyneon {pn[0]}  ΔE {pn[3]:.1f}", 1.55))
    pages.append(o)

    # ---------------- p5 1:1 details + mockup + changes
    o = header(f"{n} · 1:1 DETAILS, WHAT CHANGED, PRODUCTION NOTES", "", "p5 / 5")
    o.append(t(14, 31, "1:1 STITCH-OUT DETAILS (print at 100% to check scale)", 2.6, 700))
    x = 14
    for (c, cap) in cfg["crops"]:
        im = SR.render(ALL, c, 14); tag, hh = img_tag(im, x, 35, c[2] - c[0]); o.append(tag)
        o.append(t(x, 35 + hh + 3, cap, 1.8, 600)); x += (c[2] - c[0]) + 4
    my = 98
    tag, hh = SHT.embed("flat.png", cfg["mock_crop"], 56, 14, my + 3); o.append(tag)
    o.append(t(14, my, "MOCKUP", 2.4, 700))
    o.append(t(76, my, "WHAT CHANGED vs MOCKUP (and why)", 2.4, 700))
    for i, c in enumerate(cfg["changes"]): o.append(t(76, my + 4.5 + i*3.3, c, 1.85))
    o.append(t(196, my, "PRODUCTION", 2.4, 700))
    for i, c in enumerate(cfg["production"]): o.append(t(196, my + 4.5 + i*3.3, c, 1.85))
    pages.append(o)

    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"e{n}_{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_{n}_p{i}.png", output_width=2400)
        w.append(PdfReader(f"e{n}_{i}.pdf"))
    w.write(f"{OUT}/HAKI_jacket_{n}_{cfg['slug']}_SPEC_RevB.pdf")
    for p in pieces:
        b = BBs[p]; ox, oy = b[0] - 5, b[1] - 5; Wd, Hd = b[2] - b[0] + 10, b[3] - b[1] + 10
        side = "R" if b[2] < 0 else "L"
        panel = F.PANEL_R if side == "R" else F.PANEL_L
        gd = (f'<path d="{geom_to_path(affinity.translate(panel, -ox, -oy))}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
              f'<line x1="{f(-ox)}" y1="{f(-oy)}" x2="{f(-ox)}" y2="{f(Hd)}" stroke="#00A3FF" stroke-width="0.3" stroke-dasharray="4 2"/>'
              f'<text x="{f(-ox + 1)}" y="{f(-oy + 4)}" font-size="3" fill="#00A3FF">CF</text>')
        open(f"{OUT}/HAKI_jacket_{n}_{cfg['slug']}_{p}_ART.svg", "w").write(SB.production_svg(V[p], STOPS[p], Wd, Hd, ox, oy))
        open(f"{OUT}/HAKI_jacket_{n}_{cfg['slug']}_{p}_ART+guides.svg", "w").write(SB.production_svg(V[p], STOPS[p], Wd, Hd, ox, oy, gd))
    full = SR.render(ALL, (UB[0]-6, UB[1]-6, UB[2]+6, UB[3]+6), 7)
    full.save(f"{OUT}/HAKI_jacket_{n}_{cfg['slug']}_STITCH-PREVIEW.png")
    json.dump(dict(stitches=TOT, stops={p: len(STOPS[p]) for p in pieces}, objects={p: len(V[p]) for p in pieces},
                   bbox={p: BBs[p] for p in pieces}, width=WC, colours=sorted({r["col"] for r in ALL})),
              open(f"{OUT}/summary.json", "w"), default=float)
    return dict(TOT=TOT, STOPS=STOPS, BBs=BBs, WC=WC)
