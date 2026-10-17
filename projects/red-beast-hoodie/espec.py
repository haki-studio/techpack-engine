"""Element spec (5 pages) per element: 01 beast head (FR + FL), 02 sleeve streaks (SR + SL). Adapted from the
Grand Line espec. Every per-file / per-stop number is read from dst_current.json (DST read-back, LESSONS B20)."""
import rbcore
import os, json, pickle
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
import front as F

def _SRR(vis, bbox, ppm, **kw): return SR.render(vis, bbox, ppm, base=rbcore.FABRIC, **kw)

def width_check(vis):
    groups = {}
    for r in vis: groups.setdefault(tech.rule_for(r["grp"]), []).append(r)
    out = {}
    for code, rs in groups.items():
        A = L = 0.0
        for r in rs:
            for p in SR.polys(r["geom"]):
                if p.area < 0.05: continue
                res = qa.check_geom(p, 0.8, 0.5, 0.6)
                if res: A += res["area"]; L += res["long_area"]
        out[code] = 100*L/max(A, 1e-9)
    return out

SLV_DX = 300.0          # sleeve views: S01 drawn at x - 300, S02 at x + 300
def view_bbox(el): return (-325, -105, 325, 540) if el == "01" else (-570, -130, 570, 490)
def view_xy(P, geom):
    if P[0] == "F": return geom
    return affinity.translate(geom, -SLV_DX if P == "SR" else SLV_DX, 0)

def piece_view_png(el, vis_all, ppm, size="M"):
    """stitch render on the drawn pattern pieces (sew lines, keep-out boundary, zip, welts)"""
    bbox = view_bbox(el); x0, y0, x1, y1 = bbox
    pcs = rbcore.ELEMS[el][2]
    regs = [dict(r, geom=view_xy(P, r["geom"])) for P in pcs for r in vis_all[P]]
    img = _SRR(regs, bbox, ppm); W, H = img.size
    g, mt = F.pieces(size)
    T = lambda cs: [((x - x0)*ppm, (y - y0)*ppm) for x, y in cs]
    mask = Image.new("L", (W, H), 0); d = ImageDraw.Draw(mask)
    for P in pcs: d.polygon(T(view_xy(P, g[rbcore.PIECE_CODE[P]].sew_poly()).exterior.coords), fill=255)
    out = Image.new("RGB", (W, H), (255, 255, 255)); out.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(out)
    for P in pcs:
        d.line(T(view_xy(P, g[rbcore.PIECE_CODE[P]].sew_poly()).exterior.coords), fill=(90, 70, 50), width=3)
        cl = view_xy(P, F.piece_clip(size, P))
        for q in SR.polys(cl): d.line(T(q.exterior.coords), fill=(255, 150, 0), width=1)
    if el == "01":
        for w in (F.WELT_R, F.WELT_L): d.polygon(T(w.exterior.coords), outline=(150, 130, 100), fill=(30, 34, 40))
        d.rectangle([((-6 - x0)*ppm, (0 - y0)*ppm), ((6 - x0)*ppm, (F.HEM - y0)*ppm)], fill=(150, 118, 60))
    return out

def build(cfg, vis_all):
    el = cfg["id"]; pieces = list(rbcore.ELEMS[el][2]); slug = rbcore.ELEMS[el][0]
    SB.FOOT = f"HAKI STUDIOS · {rbcore.NAME} · {el} {cfg['short']} · {rbcore.REV_EMB} · {rbcore.DATE}"
    OUT = f"out/{el}_{slug}"; os.makedirs(OUT, exist_ok=True)
    V = {p: vis_all[p] for p in pieces}; ALL = [r for p in pieces for r in V[p]]
    import dst2; rbcore.patch_dst2()
    STOPS = {p: dst2.merge_stops(tech.stops(V[p])) for p in pieces}
    _r = json.load(open("dst_current.json"))
    BBs = {p: unary_union([r["geom"] for r in V[p]]).bounds for p in pieces}
    WC = width_check(ALL)

    # ---------------- p1 preview + placement
    o = header(f"{el} · {cfg['title']} — stitch-out preview + placement", cfg["sub"], "p1 / 5")
    bbox = view_bbox(el); ppm = 2.4
    fv = piece_view_png(el, vis_all, ppm)
    w_mm = 152; s = w_mm / (bbox[2] - bbox[0]); ax, ay = 12, 29
    tag, h = img_tag(fv, ax, ay, w_mm); o.append(tag)
    X = lambda x: ax + (x - bbox[0])*s; Y = lambda y: ay + (y - bbox[1])*s
    for p in pieces:
        b = view_xy(p, unary_union([r["geom"] for r in V[p]])).bounds
        o.append(f'<rect x="{f(X(b[0]))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{GUIDE}" stroke-width="0.25" stroke-dasharray="1.2 0.8"/>')
        o.append(t(X(b[0]) + 0.6, Y(b[1]) - 0.9, f"{p}: {b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.7, 700, GUIDE))
    o.append(t(ax, ay + h + 3.5, cfg["view_caption"], 1.75, 400, MUTED))
    rx = 172
    o.append(t(rx, 33, cfg["coords"], 2.0, 700)); yy = 38
    for a_, b_ in cfg["placement"]():
        o.append(t(rx, yy, a_, 1.85, 400, MUTED)); o.append(t(rx + 52, yy, b_, 1.85, 600)); yy += 3.4
    yy += 2.5
    o.append(t(rx, yy, "BY THE NUMBERS (DST read-back, size M)", 2.3, 700)); yy += 4.4
    for p in pieces:
        o.append(t(rx, yy, f"Piece {p}", 1.85, 400, MUTED)); o.append(t(rx + 52, yy, f"{_r[p]['stitches']:,} stitches · {_r[p]['trims']} trims · {_r[p]['stops']} stops", 1.85, 600)); yy += 3.4
    mh = sum(FA.machine_hours(_r[p]["stitches"], trims=_r[p]["trims"], colour_changes=_r[p]["stops"] - 1) for p in pieces)
    o.append(t(rx, yy, "Machine time / head", 1.85, 400, MUTED)); o.append(t(rx + 52, yy, f"{mh:.1f} h incl. trims + colour changes ({FA.load()['spm']} spm), + hooping", 1.85, 600)); yy += 5.5
    for line_ in cfg.get("p1_notes", []):
        col = ORANGE if line_.startswith("!") else MUTED
        o.append(t(rx, yy, line_.lstrip("!"), 1.75, 600 if col == ORANGE else 400, col)); yy += 3.2
    pages = [o]

    # ---------------- p2 direction map
    o = header(f"{el} · STITCH-DIRECTION MAP + REGION CODES", "Hatch = stitch direction (satin columns: stitches across the column, turning with it; tatami: rows along the traced stroke flow). Labels = region code → p3.", "p2 / 5")
    xcur = 12
    widths = [(BBs[p][2]-BBs[p][0]) for p in pieces]
    scale = min(160 / max(BBs[p][3]-BBs[p][1] for p in pieces), (172 - 6*(len(pieces)-1)) / sum(widths))
    for p in pieces:
        b = BBs[p]; bb = (b[0]-3, b[1]-3, b[2]+3, b[3]+3)
        dm = direction_map(V[p], bb, 4.0, label_min=120, label_mm=2.4)
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
    o = header(f"{el} · REGION STITCH TABLE — digitizing parameters per region code",
               "Both pieces share every parameter. Density = row spacing (mm). Pull comp = added width per side (mm). Width = share of the code's area narrower than 0.8 mm.", "p3 / 5")
    stats = {}
    for r in ALL:
        k = tech.rule_for(r["grp"]); st_ = stats.setdefault(k, dict(n=0, cols=set(), area=0.0))
        st_["n"] += 1; st_["cols"].add(r["col"]); st_["area"] += r["geom"].area
    hdr = ["Code", "Region", "Thread(s)", "Stitch", "Angle", "Dens.", "Len.", "Underlay", "Pull", "Notes", "Width", "Obj.", "Area mm²"]
    cx = [12, 27, 64, 84, 112, 150, 159, 168, 206, 214, 252, 263, 274]
    y0 = 31
    for x, hd in zip(cx, hdr): o.append(t(x, y0, hd, 1.75, 700, MUTED))
    order = [k for k in tech.RULES if k in stats]; rh = 3.8
    for i, k in enumerate(order):
        y = y0 + 3.8 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.6)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        name, st, ang, dens, ln, ul, pull, note = tech.RULES[k]; s_ = stats[k]
        o.append(t(cx[0], y, k, 1.7, 700)); o.append(t(cx[1], y, name, 1.6))
        xs = cx[2]
        for c in sorted(s_["cols"], key=lambda c: tech.COLOUR_ORDER.index(c)):
            o.append(swatch(xs, y, c, 3.2, 2.2)); xs += 4.2
        for j, v in enumerate((st, ang, dens, ln, ul, pull, note)):
            o.append(t(cx[3 + j], y, v if len(v) <= (30 if j == 6 else 24) else v[:(30 if j == 6 else 24)].rsplit(' ', 1)[0] + '…', 1.55))
        q = WC.get(k, 0.0); qc = GREEN if q < 1.0 else (ORANGE if q < 3.5 else RED)
        o.append(t(cx[10], y, f"{q:.1f}%", 1.6, 600, qc)); o.append(t(cx[11], y, f"{s_['n']}", 1.6, 400, MUTED)); o.append(t(cx[12], y, f"{s_['area']:,.0f}", 1.6, 400, MUTED))
    yb = y0 + 3.8 + len(order)*rh + 3
    for i, l in enumerate(["Globals: 40wt polyester, 75/11 sharp needle, 2.5 oz black cutaway backing, no topping. Satin > 7.0 wide → split satin. Tie-in/off every object; trims on jumps ≥ 2.5.",
                           "Thin strands + tapered tips are grown to ≥ 1.0 mm along their own skeleton before stitching (40wt satin minimum 0.8); 'Width' = what is still under 0.8 mm.",
                           "Stitch counts are not estimated per region: per-file and per-stop counts (p1, p4, G4, G5) are read back from the DST files.",
                           cfg.get("p3_note", "")]):
        o.append(t(12, yb + i*3.2, l, 1.7, 400, MUTED))
    pages.append(o)

    # ---------------- p4 colour stops (DST read-back per stop)
    o = header(f"{el} · COLOUR STOP SEQUENCE + THREADS (size M, read back from the DST)", "Stitches / trims / jumps per stop counted in the written .dst. 'Sews' = every region code in that stop; each fill object also carries its own underlay + edge run.", "p4 / 5")
    colx = [12, 154]
    for ci, p in enumerate(pieces):
        x0 = colx[ci]; ps = _r[p]["per_stop"]
        o.append(t(x0, 30.5, f"PIECE {p} — {os.path.basename(_r[p]['file'])}.dst", 2.0, 700))
        hc = [x0, x0 + 7, x0 + 30, x0 + 50, x0 + 70, x0 + 104, x0 + 118, x0 + 130]
        for x, hd in zip(hc, ["Stop", "Thread", "Isacord", "Polyneon", "Sews (codes)", "Stitches", "Trims", "Jumps"]): o.append(t(x, 34.5, hd, 1.55, 700, MUTED))
        rh = 4.6
        for i, s_ in enumerate(ps):
            y = 38.5 + i*rh; k = s_["col"]; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
            if i % 2 == 0: o.append(f'<rect x="{x0-1}" y="{f(y-2.4)}" width="138" height="{f(rh)}" fill="#F5F2EC"/>')
            o.append(t(hc[0], y, f"{s_['stop']:02d}", 1.55, 700)); o.append(swatch(hc[1], y, k, 2.8, 2.0)); o.append(t(hc[1] + 3.6, y, PAL[k][1], 1.45))
            o.append(t(hc[2], y, f"{iso[0]} {iso[1]}"[:15], 1.4)); o.append(t(hc[3], y, f"{pn[0]} {pn[1]}"[:15], 1.4))
            o.append(t(hc[4], y, ", ".join(s_["codes"])[:26], 1.35, 400, MUTED)); o.append(t(hc[5], y, f"{s_['stitches']:,}", 1.5, 600))
            o.append(t(hc[6], y, f"{s_['trims']}", 1.5)); o.append(t(hc[7], y, f"{s_['jumps']}", 1.5))
        y = 38.5 + len(ps)*rh + 1.5
        o.append(t(hc[4], y, "FILE TOTAL (sum)", 1.55, 700)); o.append(t(hc[5], y, f"{sum(q['stitches'] for q in ps):,}", 1.55, 700)); o.append(t(hc[6], y, f"{sum(q['trims'] for q in ps)}", 1.55, 700))
        o.append(t(hc[4], y + 3.2, f"= DST {_r[p]['stitches']:,} stitches / {_r[p]['trims']} trims, max stitch {_r[p]['max_stitch']:.2f} mm", 1.45, 400, MUTED))
    yb = 38.5 + max(len(_r[p]["per_stop"]) for p in pieces)*4.6 + 14
    o.append(t(12, yb, "WHY THIS ORDER", 2.2, 700))
    for i, l in enumerate(cfg["why"]):
        o.append(t(12, yb + 4.2 + i*3.2, l, 1.7))
    pages.append(o)

    # ---------------- p5 1:1 details + mockup + changes
    o = header(f"{el} · 1:1 DETAILS, WHAT CHANGED, PRODUCTION NOTES", "", "p5 / 5")
    o.append(t(14, 31, "1:1 STITCH-OUT DETAILS (print at 100% to check scale)", 2.6, 700))
    x = 14
    for (P, c, cap) in cfg["crops"]:
        im = _SRR(V[P], c, 12); tag, hh = img_tag(im, x, 35, c[2] - c[0]); o.append(tag)
        o.append(t(x, 35 + hh + 3, cap, 1.8, 600)); x += (c[2] - c[0]) + 4
    my = 98
    tag, hh = SHT.embed(cfg["mock_src"], cfg["mock_crop"], 56, 14, my + 3); o.append(tag)
    o.append(t(14, my, "MOCKUP", 2.4, 700))
    o.append(t(76, my, "WHAT CHANGED vs MOCKUP (and why)", 2.4, 700))
    for i, l in enumerate(cfg["reference"]): o.append(t(14, my + 66 + i*3.0, l, 1.65, 600, ORANGE))
    for i, c in enumerate(cfg["changes"]):
        col = ORANGE if c.startswith("!") else INK
        o.append(t(76, my + 4.5 + i*3.2, c.lstrip("!"), 1.8, 600 if col == ORANGE else 400, col))
    o.append(t(200, my, "PRODUCTION", 2.4, 700))
    for i, c in enumerate(cfg["production"]): o.append(t(200, my + 4.5 + i*3.2, c, 1.8))
    pages.append(o)

    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"e{el}_{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_{el}_p{i}.png", output_width=2400)
        w.append(PdfReader(f"e{el}_{i}.pdf"))
    spec = f"{OUT}/HAKI_{rbcore.SHORT}_{el}_{slug}_SPEC_{rbcore.REV_EMB.replace(' ', '')}.pdf"; w.write(spec)
    g, mt = F.pieces("M")
    for p in pieces:
        b = BBs[p]; ox, oy = b[0] - 5, b[1] - 5; Wd, Hd = b[2] - b[0] + 10, b[3] - b[1] + 10
        pc = g[rbcore.PIECE_CODE[p]].sew_poly(); clip = F.piece_clip("M", p)
        gd = (f'<path d="{geom_to_path(affinity.translate(pc, -ox, -oy))}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
              f'<path d="{geom_to_path(affinity.translate(clip, -ox, -oy))}" fill="none" stroke="#FF8C00" stroke-width="0.3" stroke-dasharray="1.5 1"/>')
        open(f"{OUT}/HAKI_{rbcore.SHORT}_{el}_{slug}_{p}_M_ART.svg", "w").write(SB.production_svg(V[p], STOPS[p], Wd, Hd, ox, oy))
        open(f"{OUT}/HAKI_{rbcore.SHORT}_{el}_{slug}_{p}_M_ART+guides.svg", "w").write(SB.production_svg(V[p], STOPS[p], Wd, Hd, ox, oy, gd))
    piece_view_png(el, vis_all, 5.0).save(f"{OUT}/HAKI_{rbcore.SHORT}_{el}_{slug}_M_STITCH-PREVIEW.png")
    json.dump(dict(stitches_dst={p: _r[p]["stitches"] for p in pieces}, stops_dst={p: _r[p]["stops"] for p in pieces}, objects={p: len(V[p]) for p in pieces},
                   bbox={p: BBs[p] for p in pieces}, width=WC, colours=sorted({r["col"] for r in ALL})),
              open(f"{OUT}/summary.json", "w"), default=float)
    print(el, "spec", spec, {k: round(v, 1) for k, v in WC.items()})
    return spec
