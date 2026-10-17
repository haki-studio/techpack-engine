"""Element spec (5 pages) for one element of the koi blossom hoodie: 01 front (FR + FL) or 02 sleeves (SR + SL).
Adapted from the Drum Island / Grand Line espec. Every per-file and per-stop number is read back from the size-M DST
(dst_current.json, made by make_current.py from readback.dst)."""
import kbcore
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

def R_(vis, bbox, ppm): return SR.render(vis, bbox, ppm, base=kbcore.FABRIC)

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

# ---------------------------------------------------------------- garment views
SL_DX = 530.0          # sleeves drawn side by side: SL shifted right by this (its coords are x < 0)
def layout(el, size="M"):
    if el == "01": return [("FR", 0.0), ("FL", 0.0)], (-325, -105, 325, 560)
    return [("SR", 0.0), ("SL", SL_DX)], (-270, -115, 790, 480)

def view_png(el, vis_all, ppm, size="M", highlight=None):
    """stitch render on a drawn garment view: fronts = both front panels + zip + welts; sleeves = both sleeve pieces
    (pattern shape, front half = embroidery side, back half shaded)."""
    pcs, bbox = layout(el, size); x0, y0, x1, y1 = bbox
    vis = [dict(r, geom=affinity.translate(r["geom"], dx, 0)) for P, dx in pcs for r in vis_all[P]]
    img = R_(vis, bbox, ppm); W, H = img.size
    T = lambda cs, dx=0.0: [((x + dx - x0)*ppm, (y - y0)*ppm) for x, y in cs]
    g, mt = F.pieces(size)
    mask = Image.new("L", (W, H), 0); d = ImageDraw.Draw(mask)
    for P, dx in pcs: d.polygon(T(g[F.CODE[P]].sew_poly().exterior.coords, dx), fill=255)
    out = Image.new("RGB", (W, H), (255, 255, 255)); out.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(out)
    if el == "01":
        for P in ("FR", "FL"):
            w = F.keep_geoms(size, P)["welt"]; d.polygon(T(w.exterior.coords), outline=(120, 110, 90), fill=(30, 36, 54))
        d.rectangle([((-6 - x0)*ppm, (0 - y0)*ppm), ((6 - x0)*ppm, (mt["hem_f"] - y0)*ppm)], fill=(150, 118, 60))
    else:
        for P, dx in pcs:
            back = g[F.CODE[P]].sew_poly().intersection(affinity.translate(g[F.CODE[P]].sew_poly(), 0, 0))
            from shapely.geometry import box
            bk = back.intersection(box(-400, -400, 0, 900) if P == "SR" else box(0, -400, 400, 900))
            for q in (bk.geoms if bk.geom_type == "MultiPolygon" else [bk]):
                if not q.is_empty: d.polygon(T(q.exterior.coords, dx), fill=(52, 60, 82))
            d.line(T([(0, -mt["cap_h"]), (0, mt["Lu"])], dx), fill=(170, 170, 190), width=1)
    for P, dx in pcs: d.line(T(g[F.CODE[P]].sew_poly().exterior.coords, dx), fill=(90, 80, 70), width=3)
    return out, pcs, bbox

def build(cfg, vis_all):
    el = cfg["id"]; pieces = list(kbcore.ELEMS[el][2]); slug = kbcore.ELEMS[el][0]
    SB.FOOT = f"HAKI STUDIOS · {kbcore.NAME} · {el} {cfg['short']} · {kbcore.REV_EMB} · {kbcore.DATE}"
    OUT = f"out/{el}_{slug}"; os.makedirs(OUT, exist_ok=True)
    V = {p: vis_all[p] for p in pieces}; ALL = [r for p in pieces for r in V[p]]
    dst2 = kbcore.patch_dst2()
    STOPS = {p: dst2.merge_stops(tech.stops(V[p])) for p in pieces}
    _r = json.load(open("dst_current.json"))
    BBs = {p: unary_union([r["geom"] for r in V[p]]).bounds for p in pieces}
    WC = width_check(ALL)
    import emb_place as EP
    CL = EP.clearances("M")

    # ---------------- p1 preview + placement
    o = header(f"{el} · {cfg['title']} — stitch-out preview + placement", cfg["sub"], "p1 / 5")
    fv, pcs, bbox = view_png(el, vis_all, 2.4)
    w_mm = 152 if el == "01" else 156; s = w_mm / (bbox[2] - bbox[0]); ax, ay = 12, 29
    tag, h = img_tag(fv, ax, ay, w_mm); o.append(tag)
    X = lambda x: ax + (x - bbox[0])*s; Y = lambda y: ay + (y - bbox[1])*s
    for p, dx in pcs:
        b = BBs[p]
        o.append(f'<rect x="{f(X(b[0] + dx))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{GUIDE}" stroke-width="0.25" stroke-dasharray="1.2 0.8"/>')
        o.append(t(X(b[0] + dx) + 0.6, Y(b[1]) - 0.9, f"{p}: {b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.7, 700, GUIDE))
    o.append(t(ax, ay + h + 3.5, cfg["view_note"], 1.8, 400, MUTED))
    rx = 172 if el == "01" else 174
    o.append(t(rx, 33, cfg["coords"], 2.0, 700))
    yy = 38
    for p in pieces:
        b = BBs[p]
        o.append(t(rx, yy, f"Art box {p} ({kbcore.PIECE_NAME[p]})", 1.85, 400, MUTED)); o.append(t(rx + 52, yy, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}  (x {b[0]:+.0f} … {b[2]:+.0f}, y {b[1]:.0f} … {b[3]:.0f})", 1.85, 600)); yy += 3.5
        for k, v in CL[p].items():
            mn = F.MIN(p)[k]
            o.append(t(rx + 3, yy, f"→ {k}", 1.75, 400, MUTED)); o.append(t(rx + 52, yy, f"{v:.1f}  (min {mn:.0f})", 1.75, 600, GREEN if v >= mn - 0.3 else RED)); yy += 3.2
        yy += 1.2
    yy += 1.5
    o.append(t(rx, yy, "BY THE NUMBERS (size M, DST read-back)", 2.2, 700)); yy += 4.4
    for p in pieces:
        r = _r[p]; mh = FA.machine_hours(r["stitches"], trims=r["trims"], colour_changes=r["stops"] - 1)
        o.append(t(rx, yy, f"Piece {p}", 1.85, 400, MUTED)); o.append(t(rx + 22, yy, f"{r['stitches']:,} st · {r['trims']} trims · {r['stops']} stops · {len(set(r['colours']))} threads · {mh*60:.0f} min", 1.85, 600)); yy += 3.5
    o.append(t(rx, yy, f"Machine time = factory.machine_hours ({FA.load()['spm']} spm + 6 s/trim + 4 s/colour change), one head, + hooping.", 1.6, 400, MUTED)); yy += 5
    for line_ in cfg.get("p1_notes", []):
        col = ORANGE if line_.startswith("!") else MUTED
        o.append(t(rx, yy, line_.lstrip("!"), 1.8, 600 if col == ORANGE else 400, col)); yy += 3.2
    pages = [o]

    # ---------------- p2 direction map
    o = header(f"{el} · STITCH-DIRECTION MAP + REGION CODES", "Hatch = stitch direction (radial = from the flower / fin centre). Dark solid = line work (run). Labels = region code → stitch table p3.", "p2 / 5")
    xcur = 12
    widths = [(BBs[p][2]-BBs[p][0]) for p in pieces]
    scale = min(160 / max(BBs[p][3]-BBs[p][1] for p in pieces), (172 - 6*(len(pieces)-1)) / sum(widths))
    for p in pieces:
        b = BBs[p]; bb = (b[0]-3, b[1]-3, b[2]+3, b[3]+3)
        dm = direction_map(V[p], bb, 5.0, label_min=40, label_mm=2.4)
        wmm = (bb[2]-bb[0])*scale; tag, hh = img_tag(dm, xcur, 30, wmm, 88); o.append(tag)
        o.append(f'<rect x="{f(xcur)}" y="30" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(xcur, 30 + hh + 3.2, f"Piece {p} (shown {scale:.2f}:1)", 1.9, 700)); xcur += wmm + 6
    zx = 192; o.append(t(zx, 32, "DETAIL CROPS (shown 1.6:1)", 2.4, 700)); yy = 35
    for (P, c, cap) in cfg["dm_crops"]:
        im = direction_map(V[P], c, 14, label_min=30, label_mm=1.2)
        wmm = (c[2]-c[0])*1.6; tag, hh = img_tag(im, zx, yy, wmm, 90); o.append(tag)
        o.append(f'<rect x="{zx}" y="{f(yy)}" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(zx, yy + hh + 3, cap, 1.75, 400, MUTED)); yy += hh + 6.5
    pages.append(o)

    # ---------------- p3 region table
    o = header(f"{el} · REGION STITCH TABLE — digitizing parameters per region code",
               "Both pieces share every parameter. Density = row spacing (mm). Pull comp = added width per side (mm). Width = measured share below minimum.", "p3 / 5")
    stats = {}
    for r in ALL:
        k = tech.rule_for(r["grp"]); st_ = stats.setdefault(k, dict(n=0, cols=set()))
        st_["n"] += 1; st_["cols"].add(r["col"])
    hdr = ["Code", "Region", "Thread(s)", "Stitch", "Angle", "Dens.", "Len.", "Underlay", "Pull", "Notes", "Width", "Obj."]
    cx = [12, 29, 66, 98, 126, 159, 168, 177, 214, 222, 254, 266]
    y0 = 31
    for x, hd in zip(cx, hdr): o.append(t(x, y0, hd, 1.75, 700, MUTED))
    order = [k for k in tech.RULES if k in stats]; rh = min(3.62, 150 / max(1, len(order)))
    for i, k in enumerate(order):
        y = y0 + 3.6 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.5)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        name, st, ang, dens, ln, ul, pull, note = tech.RULES[k]; s_ = stats[k]
        o.append(t(cx[0], y, k, 1.7, 700)); o.append(t(cx[1], y, name, 1.65))
        xs = cx[2]
        for c in sorted(s_["cols"], key=lambda c: tech.COLOUR_ORDER.index(c))[:7]:
            o.append(swatch(xs, y, c, 3.2, 2.2)); xs += 4.2
        for j, v in enumerate((st, ang, dens, ln, ul, pull, note)):
            o.append(t(cx[3 + j], y, v if (j != 6 or len(v) <= 28) else v[:28].rsplit(' ', 1)[0] + '…', 1.6))
        q = WC.get(k, 0.0); qc = GREEN if q < 1.0 else (ORANGE if q < 3.5 else RED)
        o.append(t(cx[10], y, f"{q:.1f}%", 1.6, 600, qc)); o.append(t(cx[11], y, f"{s_['n']}", 1.6, 400, MUTED))
    yb = y0 + 3.6 + len(order)*rh + 2
    o.append(t(12, yb + 4.5, "Globals: 40wt polyester, 75/11 sharp needle, 2.5 oz cutaway backing (navy/black), no topping. Satin > 7.0 wide → split satin. Tie-in/off every object; trim jumps > 2.5.", 1.75, 400, MUTED))
    o.append(t(12, yb + 7.6, "Long-and-short shading is built as 2–4 tone bands with zig-zag boundaries (each band its own satin object, sewn dark → light). Counts per stop: p4 (DST read-back).", 1.75, 400, MUTED))
    pages.append(o)

    # ---------------- p4 colour stops (DST read-back)
    o = header(f"{el} · COLOUR STOP SEQUENCE + THREADS (size M, read back from the DST)", "Stitches / trims per stop counted in the written .dst. 'Sews' = every region code in that stop; each fill object also carries its own underlay.", "p4 / 5")
    colx = [12, 154]
    for ci, p in enumerate(pieces):
        x0 = colx[ci]; ps = _r[p]["per_stop"]
        o.append(t(x0, 30.5, f"PIECE {p} — {os.path.basename(_r[p]['file'])}.dst", 2.0, 700))
        hc = [x0, x0 + 7, x0 + 29, x0 + 47, x0 + 66, x0 + 113, x0 + 126]
        for x, hd in zip(hc, ["Stop", "Thread", "Isacord", "Polyneon", "Sews (region codes)", "Stitches", "Trims"]): o.append(t(x, 34.5, hd, 1.55, 700, MUTED))
        rh = min(4.6, 148 / max(1, len(ps)))
        fs = min(1.45, rh*0.4)
        for i, s_ in enumerate(ps):
            y = 38.5 + i*rh; k = s_["col"]; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
            if i % 2 == 0: o.append(f'<rect x="{x0-1}" y="{f(y-rh*0.62)}" width="138" height="{f(rh)}" fill="#F5F2EC"/>')
            o.append(t(hc[0], y, f"{s_['stop']:02d}", fs, 700)); o.append(swatch(hc[1], y, k, 2.8, min(2.0, rh*0.7))); o.append(t(hc[1] + 3.6, y, PAL[k][1], fs))
            o.append(t(hc[2], y, f"{iso[0]} {iso[1]}"[:15], fs)); o.append(t(hc[3], y, f"{pn[0]} {pn[1]}"[:15], fs))
            o.append(t(hc[4], y, ", ".join(s_.get("codes", []))[:40], fs*0.95, 400, MUTED)); o.append(t(hc[5], y, f"{s_['stitches']:,}", fs, 600)); o.append(t(hc[6], y, f"{s_['trims']}", fs))
        y = 38.5 + len(ps)*rh + 1.5
        o.append(t(hc[4], y, "FILE TOTAL (sum of stops)", 1.55, 700)); o.append(t(hc[5], y, f"{sum(q['stitches'] for q in ps):,}", 1.55, 700)); o.append(t(hc[6], y, f"{sum(q['trims'] for q in ps)}", 1.55, 700))
        o.append(t(hc[4], y + 3.2, f"= DST {_r[p]['stitches']:,} stitches / {_r[p]['trims']} trims", 1.45, 400, MUTED))
    pages.append(o)

    # ---------------- p5 1:1 details + mockup + changes
    o = header(f"{el} · 1:1 DETAILS, WHAT CHANGED, PRODUCTION NOTES", "", "p5 / 5")
    o.append(t(14, 31, "1:1 STITCH-OUT DETAILS (print at 100% to check scale)", 2.6, 700))
    x = 14
    for (P, c, cap) in cfg["crops"]:
        im = R_(V[P], c, 14); tag, hh = img_tag(im, x, 35, c[2] - c[0]); o.append(tag)
        o.append(t(x, 35 + hh + 3, cap, 1.8, 600)); x += (c[2] - c[0]) + 4
    my = 104
    tag, hh = SHT.embed(cfg["mock_file"], cfg["mock_crop"], cfg.get("mock_w", 56), 14, my + 3); o.append(tag)
    o.append(t(14, my, "MOCKUP", 2.4, 700))
    o.append(t(76, my, "WHAT CHANGED vs MOCKUP (and why)", 2.4, 700))
    for i, c in enumerate(cfg["changes"]): o.append(t(76, my + 4.5 + i*3.2, c, 1.8))
    o.append(t(196, my, "PRODUCTION", 2.4, 700))
    for i, c in enumerate(cfg["production"]): o.append(t(196, my + 4.5 + i*3.2, c, 1.8))
    o.append(t(14, SH - 12, cfg.get("reference", ""), 1.8, 600, ORANGE))
    pages.append(o)

    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"out/e{el}_{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"out/prev_{el}_p{i}.png", output_width=2400)
        w.append(PdfReader(f"out/e{el}_{i}.pdf"))
    spec = f"{OUT}/HAKI_{kbcore.SHORT}_{el}_{slug}_SPEC_{kbcore.REV_EMB.replace(' ', '')}.pdf"
    w.write(spec)
    for p in pieces:
        b = BBs[p]; ox, oy = b[0] - 5, b[1] - 5; Wd, Hd = b[2] - b[0] + 10, b[3] - b[1] + 10
        g, mt = F.pieces("M"); pc = g[F.CODE[p]].sew_poly()
        gd = (f'<path d="{geom_to_path(affinity.translate(pc, -ox, -oy))}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
              f'<path d="{geom_to_path(affinity.translate(F.clip_for("M", p), -ox, -oy))}" fill="none" stroke="#FF6A00" stroke-width="0.3" stroke-dasharray="1.5 1"/>')
        open(f"{OUT}/HAKI_{kbcore.SHORT}_{el}_{slug}_{p}_M_ART.svg", "w").write(SB.production_svg(V[p], STOPS[p], Wd, Hd, ox, oy))
        open(f"{OUT}/HAKI_{kbcore.SHORT}_{el}_{slug}_{p}_M_ART+guides.svg", "w").write(SB.production_svg(V[p], STOPS[p], Wd, Hd, ox, oy, gd))
        R_(V[p], (b[0]-6, b[1]-6, b[2]+6, b[3]+6), 7).save(f"{OUT}/HAKI_{kbcore.SHORT}_{el}_{slug}_{p}_M_STITCH-PREVIEW.png")
    json.dump(dict(stops={p: len(STOPS[p]) for p in pieces}, objects={p: len(V[p]) for p in pieces},
                   bbox={p: BBs[p] for p in pieces}, width=WC, colours=sorted({r["col"] for r in ALL})),
              open(f"{OUT}/summary.json", "w"), default=float)
    return spec
