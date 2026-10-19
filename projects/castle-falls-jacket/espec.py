"""Element spec (5 pages) for one embroidery element of the Castle Falls jacket (01 back / 02 fronts / 03 sleeves).
Every per-file and per-stop number is read back from the size-M DST (dst_current.json, readback.dst — LESSONS B20)."""
import cfcore
import os, json, pickle
import numpy as np
import cairosvg
from PIL import Image, ImageDraw
from shapely.ops import unary_union
from shapely import affinity
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import geom_to_path, f
from motifs2 import HEX, PAL
import tech, stitchrender as SR, qa, factory as FA
import specbase as SB
from specbase import img_tag, direction_map, header
import keepout as KO, views as VW, mockmap as MM
dst2 = cfcore.patch_dst2()
PROF = FA.load()
def mh(r): return FA.machine_hours(r["stitches"], PROF, trims=r["trims"], colour_changes=r["stops"] - 1)

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
        out[code] = 100 * L / max(A, 1e-9)
    return out

def piece_view(P, vis, ppm=1.6, size="M"):
    """stitch render of the piece on its own pattern piece (white outside), keep-out line in red"""
    b = KO.panel(size, P).bounds; b = (b[0] - 4, b[1] - 4, b[2] + 4, b[3] + 4)
    st = SR.render(vis, b, ppm, base=cfcore.FABRIC)
    m = Image.new("L", st.size, 0); T = lambda cs: [((x - b[0]) * ppm, (y - b[1]) * ppm) for x, y in cs]
    ImageDraw.Draw(m).polygon(T(KO.panel(size, P).exterior.coords), fill=255)
    out = Image.composite(st, Image.new("RGB", st.size, (255, 255, 255)), m); d = ImageDraw.Draw(out)
    d.line(T(KO.panel(size, P).exterior.coords), fill=(60, 60, 60), width=2)
    d.line(T(KO.clip(size, P).exterior.coords), fill=(230, 80, 60), width=1)
    return out, b

def build(cfg, art):
    e = cfg["id"]; slug = cfcore.ELEMS[e][0]
    SB.FOOT = f"HAKI STUDIOS · {cfcore.NAME} · {e} {cfg['short']} · {cfcore.REV_EMB} · {cfcore.DATE}"
    OUT = f"out/{e}_{slug}"; os.makedirs(OUT, exist_ok=True)
    pieces = cfcore.ELEMS[e][2]
    PLAN = json.load(open("merge_plan.json"))
    V = {p: dst2.merge_colours(art[p], PLAN[p]) for p in pieces}
    ALL = [r for p in pieces for r in V[p]]
    STOPS = {p: dst2.merge_stops(tech.stops(V[p])) for p in pieces}
    _r = json.load(open("dst_current.json"))
    BBs = {p: dst2.bounds_of([r["geom"] for r in V[p]]) for p in pieces}
    WC = width_check(ALL)

    # ---------------- p1 preview + placement + numbers
    o = header(f"{e} · {cfg['title']} — stitch-out preview + placement", cfg["sub"], "p1 / 5")
    if e == "03":
        fv, _ = VW.front_view(art, 1.6, pieces); bv, _ = VW.back_view(art, 1.6, pieces)
        tag, h = img_tag(fv, 12, 29, 76); o.append(tag); tag, h2 = img_tag(bv, 90, 29, 76); o.append(tag)
        o.append(t(12, 29 + h + 3, "Front view (front halves) + back view (back halves), size M.", 1.7, 400, MUTED))
        y_img = 29 + h + 6
        x = 12
        for p in pieces:
            im, b = piece_view(p, V[p], 1.0); tag, hh = img_tag(im, x, y_img, 76); o.append(tag)
            o.append(t(x, y_img + hh + 3, f"{p} {cfcore.PIECE_CODE[p]} flat (cap at top; red = keep-out)", 1.6, 600)); x += 78
    else:
        v = VW.back_view(art, 2.0, pieces)[0] if e == "01" else VW.front_view(art, 2.0, pieces)[0]
        tag, h = img_tag(v, 12, 29, 150); o.append(tag)
        o.append(t(12, 29 + h + 3, ("Back" if e == "01" else "Front") + " view, size M stitch render on the technical flat (shown ~0.17:1).", 1.8, 400, MUTED))
    rx = 172
    o.append(t(rx, 33, "PLACEMENT (mm, pattern-piece coords — see G2 / T13)", 2.2, 700)); yy = 38
    for p in pieces:
        c = KO.clearances(unary_union([r["geom"] for r in V[p]]).buffer(0.3).buffer(-0.3), "M", p); mn = KO.minimums("M", p); b = BBs[p]
        o.append(t(rx, yy, f"{p} {cfcore.PIECE_NAME[p]} ({cfcore.PIECE_CODE[p]}): art {b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.85, 700)); yy += 3.4
        o.append(t(rx + 2, yy, f"x {b[0]:+.0f} … {b[2]:+.0f}, y {b[1]:.0f} … {b[3]:.0f}  ({cfg['coords']})", 1.6, 400, MUTED)); yy += 3.2
        items_ = [f"{k} {v:.1f}≥{mn[k]:.0f}" for k, v in c.items()]; chunks, cur = [], ""
        for it in items_:
            if len(cur) + len(it) > 84: chunks.append(cur); cur = it
            else: cur = (cur + "   " + it).strip()
        chunks.append(cur)
        for chunk in chunks:
            o.append(t(rx + 2, yy, chunk, 1.5, 400, GREEN if all(v >= mn[k] - 0.3 for k, v in c.items()) else RED)); yy += 3.0
        yy += 1
    yy += 2; o.append(t(rx, yy, "BY THE NUMBERS (size M, read back from the DST)", 2.2, 700)); yy += 4.4
    for p in pieces:
        r = _r[p]; ns = len(r["splits"]["sections"])
        o.append(t(rx, yy, f"{p}: {r['stitches']:,} stitches · {r['trims']} trims · {r['stops']} stops · {r['threads']} colours · max {r['max_stitch']:.2f} mm", 1.8, 600)); yy += 3.4
        o.append(t(rx + 2, yy, f"{mh(r):.1f} h per head ({PROF['spm']} spm + trims + colour changes) · {ns} hooping{'s' if ns > 1 else ''} on {FA.largest_frame(PROF)[0]:.0f} × {FA.largest_frame(PROF)[1]:.0f}", 1.6, 400, MUTED)); yy += 3.6
    yy += 2
    for line_ in cfg.get("p1_notes", []):
        col = ORANGE if line_.startswith("!") else MUTED
        o.append(t(rx, yy, line_.lstrip("!"), 1.75, 600 if col == ORANGE else 400, col)); yy += 3.2
    pages = [o]

    # ---------------- p2 direction map
    o = header(f"{e} · STITCH-DIRECTION MAP + REGION CODES", "Hatch = stitch direction (radial = turning satin). Dark solid = line work (bean). Labels = region code → stitch table p3.", "p2 / 5")
    xcur = 12; avail = 176 - 5 * (len(pieces) - 1)
    scale = min(165 / max(BBs[p][3] - BBs[p][1] for p in pieces), avail / sum(BBs[p][2] - BBs[p][0] + 6 for p in pieces))
    for p in pieces:
        b = BBs[p]; bb = (b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3)
        dm = direction_map(V[p], bb, 2.6, label_min=250, label_mm=3.0)
        wmm = (bb[2] - bb[0]) * scale; tag, hh = img_tag(dm, xcur, 30, wmm, 85); o.append(tag)
        o.append(f'<rect x="{f(xcur)}" y="30" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(xcur, 30 + hh + 3.2, f"{p} (shown {scale:.2f}:1)", 1.9, 700)); xcur += wmm + 5
    zx = 194; o.append(t(zx, 32, "DETAIL CROPS (shown 1.6:1)", 2.4, 700)); yy = 35
    cfg = dict(cfg, dm_crops=[(p, (c[0], c[1], c[2], c[1] + (c[3] - c[1]) * 0.75), cap) for p, c, cap in cfg["dm_crops"]])
    for (p, c, cap) in cfg["dm_crops"]:
        im = direction_map(V[p], c, 10, label_min=20, label_mm=1.3)
        wmm = (c[2] - c[0]) * 1.6; hh_ = wmm * (c[3] - c[1]) / (c[2] - c[0])
        if yy + hh_ + 4 > SH - 12: break
        tag, hh = img_tag(im, zx, yy, wmm, 90); o.append(tag)
        o.append(f'<rect x="{zx}" y="{f(yy)}" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(zx, yy + hh + 3, f"{p}: {cap}", 1.7, 400, MUTED)); yy += hh + 6.5
    pages.append(o)

    # ---------------- p3 region table
    o = header(f"{e} · REGION STITCH TABLE — digitizing parameters per region code",
               "Every piece of this element shares these parameters. Density = row spacing (mm). Pull comp = added width per side (mm). Width = share of the code's area below its minimum width.", "p3 / 5")
    stats = {}
    for r in ALL:
        k = tech.rule_for(r["grp"]); st_ = stats.setdefault(k, dict(n=0, cols=set(), area=0.0))
        st_["n"] += 1; st_["cols"].add(r["col"]); st_["area"] += r["geom"].area
    hdr = ["Code", "Region", "Thread(s)", "Stitch", "Angle", "Dens.", "Len.", "Underlay", "Pull", "Notes", "Width", "Obj.", "Area mm²"]
    cx = [12, 26, 62, 102, 128, 158, 167, 176, 212, 220, 250, 261, 270]
    y0 = 31
    for x, hd in zip(cx, hdr): o.append(t(x, y0, hd, 1.7, 700, MUTED))
    order = [k for k in tech.RULES if k in stats]; rh = min(4.4, 150 / max(1, len(order)))
    for i, k in enumerate(order):
        y = y0 + 3.8 + i * rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.6)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        name, st, ang, dens, ln, ul, pull, note = tech.RULES[k]; s_ = stats[k]
        o.append(t(cx[0], y, k, 1.65, 700)); o.append(t(cx[1], y, name, 1.6))
        xs = cx[2]
        for c in sorted(s_["cols"], key=lambda c: tech.COLOUR_ORDER.index(c))[:9]:
            o.append(swatch(xs, y, c, 3.4, 2.2)); xs += 4.3
        for j, v in enumerate((st, ang, dens, ln, ul, pull, note)):
            o.append(t(cx[3 + j], y, v if (j != 6 or len(v) <= 24) else v[:24].rsplit(' ', 1)[0] + '…', 1.55))
        q = WC.get(k, 0.0); qc = GREEN if q < 1.0 else (ORANGE if q < 3.5 else RED)
        o.append(t(cx[10], y, f"{q:.1f}%", 1.55, 600, qc)); o.append(t(cx[11], y, f"{s_['n']}", 1.55, 400, MUTED))
        o.append(t(cx[12], y, f"{s_['area']:,.0f}", 1.55, 400, MUTED))
    yb = y0 + 3.8 + len(order) * rh + 3
    for i, l in enumerate(["Globals: 40wt polyester, 75/11 sharp needle, 2.5 oz cutaway backing, no topping (12 oz duck). Satin > 7.0 wide → split satin. Tie-in/off every object; trim jumps > 2.5.",
                           "The traced regions (SKY, CL, RK, FOL, BLB, TRK, VIL, FALL) are the mockup's tones, each connected tone area one object with its class's stitch angle;",
                           "small / narrow parts (< 2 mm wide, < 70 mm²) sew as satin. Florets (BL), petals (PT) and the castle (ROOF/WALL/ORN/STONE) are drawn motifs on top.",
                           "Stitch counts are not estimated per region: per-file and per-stop counts (p1, p4, G4, G5) are read back from the DST files."]):
        o.append(t(12, yb + i * 3.2, l, 1.6, 400, MUTED))
    pages.append(o)

    # ---------------- p4 colour stops, read back from the size-M DST
    o = header(f"{e} · COLOUR STOP SEQUENCE + THREADS (size M, read back from the DST)",
               "Stitches / trims / jumps per stop counted in the written .dst. 'Sews' = region codes in that stop; each fill also carries its own underlay + edge run.", "p4 / 5")
    colx = [12, 154] if len(pieces) == 2 else [12]
    for ci, p in enumerate(pieces):
        x0 = colx[ci]; ps = _r[p]["per_stop"]
        o.append(t(x0, 30.5, f"{p} — {os.path.basename(_r[p]['file'])}.dst", 1.9, 700))
        hc = [x0, x0 + 7, x0 + 30, x0 + 49, x0 + 68, x0 + 112, x0 + 126]
        for x, hd in zip(hc, ["Stop", "Thread", "Isacord", "Polyneon", "Sews (region codes)", "Stitches", "Trims"]): o.append(t(x, 34.5, hd, 1.5, 700, MUTED))
        rh = min(4.6, 150 / max(1, len(ps)))
        for i, s_ in enumerate(ps):
            y = 38.5 + i * rh; k = s_["col"]; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
            if i % 2 == 0: o.append(f'<rect x="{x0-1}" y="{f(y-2.4)}" width="138" height="{f(rh)}" fill="#F5F2EC"/>')
            o.append(t(hc[0], y, f"{s_['stop']:02d}", 1.5, 700)); o.append(swatch(hc[1], y, k, 2.8, 2.0)); o.append(t(hc[1] + 3.6, y, PAL[k][1], 1.4))
            o.append(t(hc[2], y, f"{iso[0]} {iso[1]}"[:15], 1.35)); o.append(t(hc[3], y, f"{pn[0]} {pn[1]}"[:15], 1.35))
            o.append(t(hc[4], y, ", ".join(s_["codes"])[:40], 1.3, 400, MUTED)); o.append(t(hc[5], y, f"{s_['stitches']:,}", 1.45, 600)); o.append(t(hc[6], y, f"{s_['trims']}", 1.45))
        y = 38.5 + len(ps) * rh + 1.5
        o.append(t(hc[4], y, "FILE TOTAL (sum of stops)", 1.5, 700)); o.append(t(hc[5], y, f"{sum(q['stitches'] for q in ps):,}", 1.5, 700)); o.append(t(hc[6], y, f"{sum(q['trims'] for q in ps)}", 1.5, 700))
        o.append(t(hc[4], y + 3.2, f"= DST {_r[p]['stitches']:,} stitches / {_r[p]['trims']} trims", 1.4, 400, MUTED))
        mt = PLAN[p]
        if mt:
            o.append(t(x0, y + 7.5, "Tones sewn in a neighbouring thread (≤ 12 colours per file):", 1.45, 700, ORANGE))
            o.append(t(x0, y + 10.5, " · ".join(f"{PAL[a][1]} → {PAL[b][1]}" for a, b in mt.items()), 1.4, 400, ORANGE))
    pages.append(o)

    # ---------------- p5 1:1 details + mockup + changes + production
    o = header(f"{e} · 1:1 DETAILS, WHAT CHANGED, PRODUCTION NOTES", "", "p5 / 5")
    o.append(t(14, 31, "1:1 STITCH-OUT DETAILS (print at 100% to check scale)", 2.6, 700))
    x = 14
    for (p, c, cap) in cfg["crops"]:
        c = (c[0], c[1], c[2], min(c[3], c[1] + 52)); im = SR.render(V[p], c, 12, base=cfcore.FABRIC); tag, hh = img_tag(im, x, 35, c[2] - c[0]); o.append(tag)
        o.append(t(x, 35 + hh + 3, f"{p}: {cap}", 1.8, 600)); x += (c[2] - c[0]) + 4
    my = 98
    mk = Image.open("inputs/flat.png").convert("RGB").crop(cfg["mock_crop"])
    wm = min(56.0, 56.0 * mk.width / mk.height * (56.0 / 56.0)) if mk.height > mk.width else 56.0
    wm = min(56.0, 58.0 * mk.width / mk.height)
    tag, hh = img_tag(mk, 14, my + 3, wm); o.append(tag)
    o.append(t(14, my, "MOCKUP", 2.4, 700))
    o.append(t(76, my, "WHAT CHANGED vs MOCKUP (and why)", 2.4, 700))
    for i, c in enumerate(cfg["changes"]): o.append(t(76, my + 4.5 + i * 3.3, c, 1.8))
    o.append(t(196, my, "PRODUCTION", 2.4, 700))
    for i, c in enumerate(cfg["production"]): o.append(t(196, my + 4.5 + i * 3.3, c, 1.8))
    o.append(t(14, SH - 14, cfg["reference"], 1.75, 700, ORANGE))
    pages.append(o)

    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"e{e}_{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_{e}_p{i}.png", output_width=2400)
        w.append(PdfReader(f"e{e}_{i}.pdf"))
    spec = f"{OUT}/HAKI_{cfcore.SHORT}_{e}_{slug}_SPEC_{cfcore.REV_EMB.replace(' ', '')}.pdf"
    w.write(spec)
    for p in pieces:
        b = BBs[p]; ox, oy = b[0] - 5, b[1] - 5; Wd, Hd = b[2] - b[0] + 10, b[3] - b[1] + 10
        gd = (f'<path d="{geom_to_path(affinity.translate(KO.panel("M", p), -ox, -oy))}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
              f'<path d="{geom_to_path(affinity.translate(KO.clip("M", p), -ox, -oy))}" fill="none" stroke="#FF5A3C" stroke-width="0.3" stroke-dasharray="2 1.5"/>')
        open(f"{OUT}/HAKI_{cfcore.SHORT}_{e}_{slug}_{p}_M_ART.svg", "w").write(SB.production_svg(V[p], STOPS[p], Wd, Hd, ox, oy))
        open(f"{OUT}/HAKI_{cfcore.SHORT}_{e}_{slug}_{p}_M_ART+guides.svg", "w").write(SB.production_svg(V[p], STOPS[p], Wd, Hd, ox, oy, gd))
        im, _ = piece_view(p, V[p], 5.0); im.save(f"{OUT}/HAKI_{cfcore.SHORT}_{e}_{slug}_{p}_M_STITCH-PREVIEW.png")
    json.dump(dict(stops={p: len(STOPS[p]) for p in pieces}, objects={p: len(V[p]) for p in pieces},
                   bbox={p: BBs[p] for p in pieces}, width=WC, colours={p: sorted({r["col"] for r in V[p]}) for p in pieces}),
              open(f"{OUT}/summary.json", "w"), default=float)
    return dict(spec=spec, WC=WC, pages=len(pages))
