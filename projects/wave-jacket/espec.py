"""Element spec for 01 WAVE (five pieces: BK, FR, FL, SR, SL) — 6 pages, size M. Every count is read back from the
written DST files (dst_current.json, readback.dst); art = art_M.pkl.  usage: ./py.sh espec.py"""
import wavecore as WC
import os, json, pickle
import cairosvg
from PIL import Image
from shapely.ops import unary_union
from shapely import affinity
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import geom_to_path, f
from motifs2 import HEX, PAL
import tech, stitchrender as SR, qa
import specbase as SB
from specbase import img_tag, direction_map, header
import pieces as PC, views as VW, emb_place as EP, factory as FA
dst2 = WC.patch_dst2()

N = "01"; SLUG = "wave"
OUT = f"out/{N}_{SLUG}"; os.makedirs(OUT, exist_ok=True)
D = pickle.load(open("art_M.pkl", "rb")); V = {P: D[P] for P in WC.PIECES}
CUR = json.load(open("dst_current.json"))
PROF = FA.load()
def mh(r): return FA.machine_hours(r["stitches"], PROF, trims=r["trims"], colour_changes=r["stops"] - 1)
BB = {P: unary_union([r["geom"] for r in V[P]]).bounds for P in WC.PIECES}
ALLV = [r for P in WC.PIECES for r in V[P]]

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

def p1():
    o = header(f"{N} · {WC.ELEM_TITLE}", "Direct embroidery on 5 cut pieces (back, both fronts, both sleeves), flat, before any seam · mm, finished size · art files 1:1 · size M", "p1 / 6")
    bk, _, _ = VW.view_png("back", "M", 1.6); fr, _, _ = VW.view_png("front", "M", 1.6)
    tag, h = img_tag(bk, 12, 29, 92); o.append(tag); o.append(t(12, 29 + h + 3, "BACK (flat lay, size M stitch preview)", 1.9, 700))
    tag, h2 = img_tag(fr, 108, 29, 92); o.append(tag); o.append(t(108, 29 + h2 + 3, "FRONT (flat lay, size M stitch preview)", 1.9, 700))
    rx = 206; y = 31
    o.append(t(rx, y, "BY THE NUMBERS (size M, DST read-back)", 2.2, 700)); y += 4.5
    for c_, hh in zip((rx, rx + 13, rx + 33, rx + 46, rx + 56, rx + 68), ("Piece", "Stitches", "Trims", "Stops", "Hoops", "Run time")):
        o.append(t(c_, y, hh, 1.6, 700, MUTED))
    y += 3.6
    for P in WC.PIECES:
        r = CUR[P]
        o.append(t(rx, y, P, 1.75, 700)); o.append(t(rx + 13, y, f"{r['stitches']:,}", 1.7)); o.append(t(rx + 33, y, f"{r['trims']:,}", 1.7))
        o.append(t(rx + 46, y, f"{r['stops']}", 1.7)); o.append(t(rx + 56, y, f"{r['hoopings']}", 1.7)); o.append(t(rx + 68, y, f"{mh(r)*60:.0f} min", 1.7)); y += 3.5
    tot = sum(CUR[P]["stitches"] for P in WC.PIECES); tt = sum(CUR[P]["trims"] for P in WC.PIECES); th = sum(mh(CUR[P]) for P in WC.PIECES)
    o.append(t(rx, y, "All", 1.75, 700)); o.append(t(rx + 13, y, f"{tot:,}", 1.75, 700)); o.append(t(rx + 33, y, f"{tt:,}", 1.75, 700)); o.append(t(rx + 68, y, f"{th:.1f} h", 1.75, 700)); y += 4
    o.append(t(rx, y, f"Run time = {PROF['spm']} spm + 6 s/trim + 4 s/colour change, one head (factory.machine_hours).", 1.45, 400, MUTED)); y += 6
    o.append(t(rx, y, "KEEP-OUT CLEARANCES, SIZE M (mm, art outline → sew line)", 2.0, 700)); y += 4
    cl = EP.clearances("M")
    for P in WC.PIECES:
        items = ", ".join(f"{k} {v:.0f}" for k, v in cl[P].items())
        ok = all(v >= PC.MIN[P][k] - 0.3 for k, v in cl[P].items())
        o.append(t(rx, y, P, 1.6, 700, GREEN if ok else RED)); o.append(t(rx + 6, y, items[:70], 1.4)); y += 2.9
        if len(items) > 70: o.append(t(rx + 6, y, items[70:140], 1.4)); y += 2.9
    y += 2
    o.append(t(rx, y, "Min: side/CF/shoulder/armhole/underarm/cap 15 · hem 10 · cuff 10", 1.45, 400, MUTED)); y += 2.9
    o.append(t(rx, y, "welt 6 · collar lying flat 6 · neck 6. All sizes: T13.", 1.45, 400, MUTED)); y += 6
    for l_ in ["!Art traced from the low-res AI render (~1.4 mm/px): stripe", "!tones, every crest + curl and every spray drop are in the", "!render; curl detail is redrawn (foam close-up = style ref).",
               "Sleeves: the render's sleeves are long + narrow, so the", "wave is placed by its position on the hanging sleeve; the", "armhole is a normal 15 mm keep-out [proposed — confirm]."]:
        col = ORANGE if l_.startswith("!") else MUTED
        o.append(t(rx, y, l_.lstrip("!"), 1.6, 600 if col == ORANGE else 400, col)); y += 2.9
    return o

def p2():
    o = header(f"{N} · STITCH-DIRECTION MAP + REGION CODES (size M)", "Hatch = stitch direction. Dark solid = line work (bean / run). Labels = region code (stitch table p3). Each piece drawn at its own scale.", "p2 / 6")
    lay = [("BK", 12, 30, 92), ("FR", 108, 30, 44), ("FL", 156, 30, 44), ("SR", 204, 30, 42), ("SL", 250, 30, 42)]
    for P, x, y, w in lay:
        b = BB[P]; bb = (b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3)
        dm = direction_map(V[P], bb, 3.0, label_min=150, label_mm=3.0)
        tag, hh = img_tag(dm, x, y, w, 86); o.append(tag)
        o.append(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(x, y + hh + 3, f"{P} {PC.NAME[P]} ({w/(bb[2]-bb[0]):.2f}:1)", 1.6, 700))
    zy = 128; zx = 12
    o.append(t(zx, zy, "DETAIL CROPS (2:1)", 2.2, 700))
    b = BB["BK"]; crops = [((b[0] + 40, b[1] + 60, b[0] + 100, b[1] + 100), "Crest: padded foam, curl lines, loops, grey hollow"),
                           ((-40, 300, 20, 340), "Stripes: turning satin per tone + cream rope lines"),
                           ((b[2] - 100, b[3] - 70, b[2] - 40, b[3] - 30), "Drops + crests at the lower right")]
    for c, cap in crops:
        im = direction_map(V["BK"], c, 12, label_min=25, label_mm=1.4)
        tag, hh = img_tag(im, zx, zy + 3, 120 * 0.75 if False else (c[2] - c[0]) * 1.4); o.append(tag)
        o.append(t(zx, zy + 3 + hh + 3, cap, 1.6, 400, MUTED)); zx += (c[2] - c[0]) * 1.4 + 6
    return o

def p3():
    o = header(f"{N} · REGION STITCH TABLE — digitizing parameters per region code",
               "All five pieces share every parameter. Density = row spacing (mm). Pull comp = added width per side (mm). Width = share of the code's area below its minimum width.", "p3 / 6")
    WCK = width_check(ALLV)
    stats = {}
    for r in ALLV:
        k = tech.rule_for(r["grp"]); s_ = stats.setdefault(k, dict(n=0, cols=set())); s_["n"] += 1; s_["cols"].add(r["col"])
    hdr = ["Code", "Region", "Thread(s)", "Stitch", "Angle", "Dens.", "Len.", "Underlay", "Pull", "Notes", "Width", "Obj."]
    cx = [12, 26, 62, 92, 128, 152, 166, 174, 214, 222, 266, 278]
    for x, hd in zip(cx, hdr): o.append(t(x, 31, hd, 1.7, 700, MUTED))
    order = [k for k in tech.RULES if k in stats]; rh = 5.2
    for i, k in enumerate(order):
        y = 36 + i * rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.4)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        name, st, ang, dens, ln, ul, pull, note = tech.RULES[k]; s_ = stats[k]
        o.append(t(cx[0], y, k, 1.7, 700)); o.append(t(cx[1], y, name[:24], 1.55))
        xs = cx[2]
        for c in sorted(s_["cols"], key=lambda c: tech.COLOUR_ORDER.index(c))[:7]:
            o.append(swatch(xs, y, c, 3.2, 2.2)); xs += 4.0
        for j, v in enumerate((st, ang, dens, ln, ul, pull, note)):
            lim = [34, 24, 12, 6, 40, 6, 44][j]
            o.append(t(cx[3 + j], y, v if len(v) <= lim else v[:lim].rsplit(' ', 1)[0] + '…', 1.45))
        q = WCK.get(k, 0.0); qc = GREEN if q < 1.0 else (ORANGE if q < 3.5 else RED)
        o.append(t(cx[10], y, f"{q:.1f}%", 1.5, 600, qc)); o.append(t(cx[11], y, f"{s_['n']}", 1.5, 400, MUTED))
    yb = 36 + len(order) * rh + 3
    notes = ["Globals: 40wt polyester, 75/11 sharp needle, 2.5 oz cutaway backing (navy / charcoal), no topping. Satin > 7.0 wide → split satin. Tie-in/off every object; exposed moves > 2.0 trimmed.",
             "FOAM: the render's raised looped white curls look like chenille. Rev A digitizes them as padded tatami (1 padding layer) + a scalloped contour 'loop' spiral and curl lines in Foam shade on top,",
             "      sewn on any multi-needle head. If the factory has chenille / moss-stitch heads, FM + FM-loop can become chenille loops (same outlines) — [proposed — confirm, F1].",
             "Width = qa.check_geom share below the minimum (fill/satin 0.8, line 0.6). Amber/red codes are tapered ends + traced flecks: kept for fidelity, check on the sew-out.",
             "Stitch counts are never estimated per region: per-file and per-stop counts (p1, p4, p5, G4, G5) are read back from the DST files."]
    for i, n_ in enumerate(notes): o.append(t(12, yb + i * 3.3, n_, 1.55, 400, ORANGE if "FOAM" in n_ else MUTED))
    return o, WCK

def stops_page(Ps, page):
    o = header(f"{N} · COLOUR STOP SEQUENCE + THREADS (size M, read back from the DST)",
               "Stitches / trims per stop counted in the written .dst. 'Sews' = region codes in that stop; each fill object also carries its own underlay + edge run.", page)
    colw = (SW - 24) / len(Ps)
    for ci, P in enumerate(Ps):
        x0 = 12 + ci * colw; r = CUR[P]; ps = r["per_stop"]
        o.append(t(x0, 30.5, f"{P} — {os.path.basename(r['file'])}.dst", 1.8, 700))
        hc = [x0, x0 + 6, x0 + 26, x0 + 44, x0 + colw - 22, x0 + colw - 10]
        for x, hd in zip(hc, ["Stop", "Thread", "Isacord", "Polyneon", "Stitches", "Trims"]): o.append(t(x, 34.5, hd, 1.45, 700, MUTED))
        rh = min(4.4, 140 / max(1, len(ps)))
        for i, s_ in enumerate(ps):
            y = 38.5 + i * rh; k = s_.get("col") or "w1"; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
            if i % 2 == 0: o.append(f'<rect x="{f(x0-1)}" y="{f(y-2.4)}" width="{f(colw-3)}" height="{f(rh)}" fill="#F5F2EC"/>')
            o.append(t(hc[0], y, f"{s_['stop']:02d}", 1.45, 700)); o.append(swatch(hc[1], y, k, 2.6, 1.9)); o.append(t(hc[1] + 3.3, y, PAL[k][1][:13], 1.35))
            o.append(t(hc[2], y, f"{iso[0]}", 1.35)); o.append(t(hc[3], y, f"{pn[0]}", 1.35))
            o.append(t(hc[4], y, f"{s_['stitches']:,}", 1.4, 600)); o.append(t(hc[5], y, f"{s_['trims']}", 1.4))
            o.append(t(hc[2] + 9, y, ", ".join(s_.get("codes", []))[:22], 1.15, 400, MUTED))
        y = 38.5 + len(ps) * rh + 2
        o.append(t(hc[2], y, "FILE TOTAL (sum of stops)", 1.4, 700)); o.append(t(hc[4], y, f"{sum(q['stitches'] for q in ps):,}", 1.45, 700)); o.append(t(hc[5], y, f"{sum(q['trims'] for q in ps)}", 1.45, 700))
        o.append(t(hc[2], y + 3, f"= DST {r['stitches']:,} st / {r['trims']} trims · {len(set(r['colours']))} threads · max {r['max_stitch']:.2f}", 1.3, 400, MUTED))
    return o

def p6():
    o = header(f"{N} · 1:1 DETAILS, REFERENCE, WHAT CHANGED, PRODUCTION NOTES", "", "p6 / 6")
    o.append(t(14, 31, "1:1 STITCH-OUT DETAILS (print at 100 % to check scale)", 2.4, 700))
    b = BB["BK"]; crops = [((b[0] + 45, b[1] + 55, b[0] + 105, b[1] + 100), "Crest + curls (BK)"), ((-30, 295, 30, 340), "Stripes + rope lines (BK)"),
                           ((b[2] - 95, b[3] - 70, b[2] - 35, b[3] - 25), "Crest + drops (BK)")]
    x = 14
    for c, cap in crops:
        im = SR.render(V["BK"], c, 12, base=WC.FABRIC); tag, hh = img_tag(im, x, 35, c[2] - c[0]); o.append(tag)
        o.append(t(x, 35 + hh + 3, cap, 1.7, 600)); x += (c[2] - c[0]) + 5
    my = 92
    o.append(t(14, my, "REFERENCES", 2.3, 700))
    tag, hh = SHT.embed("inputs/back.png", (0, 230, 620, 740), 46, 14, my + 3); o.append(tag)
    tag2, hh2 = SHT.embed("inputs/closeup_mockup_foam.png", None, 22, 62, my + 3); o.append(tag2)
    o.append(t(14, my + 3 + max(hh, hh2) + 3, "Render (back) · foam close-up (style reference only)", 1.5, 400, MUTED))
    o.append(t(14, my + 3 + max(hh, hh2) + 6.5, "Art TRACED from a low-res AI render (~1.4 mm/px), not from originals:", 1.55, 700, ORANGE))
    o.append(t(14, my + 3 + max(hh, hh2) + 9.5, "positions + tones from the render, curl detail redrawn at stitch scale.", 1.55, 700, ORANGE))
    cx = 92
    o.append(t(cx, my, "WHAT CHANGED vs THE RENDER (and why)", 2.3, 700))
    ch = ["Layout: render mapped onto the Drum Island pattern, x 1.45 mm/px,",
          "  y from neck → hem seam (back 1.14, front 1.24 mm/px).",
          "Curls + drops keep their render shape (mean scale) — no oval curls.",
          "Crests cut into curls (watershed): each curl is one raised motif with",
          "  its curl line, grey hollow + shade; loop spiral = chenille look.",
          "Stripes: 6 blues traced, smoothed over ~2 render px; cream rope lines.",
          "Keep-outs (15 seams/CF/armhole, 10 hem/cuff, 6 welt/collar) clip",
          "  the render's art where it ran over seams, rib and pockets.",
          "Sleeves: placed from the fold + shoulder of the hanging sleeve (the",
          "  render's sleeve is ~1/2 the pattern width: widened up to 1.45 so",
          "  its inner edge meets the underarm keep-out) [proposed — confirm].",
          "No seam-true wrap across the armhole (can't be mapped from the",
          "  render) — art ends 15 short of the armhole on both pieces.",
          "Threads: 9 (12 allowed): 2 creams + grey for the foam, 6 blues."]
    for i, c in enumerate(ch): o.append(t(cx, my + 4.5 + i * 3.3, c, 1.7))
    px = 206
    o.append(t(px, my, "PRODUCTION", 2.3, 700))
    pr = ["Embroider the 5 cut pieces flat, BEFORE any", "  seam, welt or zip. Pre-wash the shell first.",
          f"9 threads, 40wt polyester (G3); ≤ {FA.max_threads(PROF)} per file.", "Navy 12 oz duck: 75/11 sharp, 2.5 oz", "  cutaway, no topping.",
          "Foam: padded (raised) — check loft + loop", "  look on the strike-off; chenille heads?",
          "Mark CF, welt box (drills), split lines +", "  needle starts (DXF layer 13) before hooping.",
          f"Frame {FA.largest_frame(PROF)[0]:.0f} × {FA.largest_frame(PROF)[1]:.0f} (factory.json): split files,", "  registration crosses open stop 1 (G6).",
          "Sew-out size M on production shell first (F1)."]
    for i, c in enumerate(pr): o.append(t(px, my + 4.5 + i * 3.3, c, 1.7))
    return o

def build():
    SB.FOOT = f"HAKI STUDIOS · {WC.NAME} · {N} {SLUG} · {WC.REV_EMB} · {WC.DATE}"
    o3, WCK = p3()
    pages = [p1(), p2(), o3, stops_page(["BK", "FR", "FL"], "p4 / 6"), stops_page(["SR", "SL"], "p5 / 6"), p6()]
    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"e{N}_{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_{N}_p{i}.png", output_width=2400)
        w.append(PdfReader(f"e{N}_{i}.pdf"))
    w.write(f"{OUT}/HAKI_WAVE_{N}_{SLUG}_SPEC_{WC.REV_EMB.replace(' ', '')}.pdf")
    for P in WC.PIECES:
        stops = dst2.merge_stops(tech.stops(V[P]))
        b = BB[P]; ox, oy = b[0] - 5, b[1] - 5; Wd, Hd = b[2] - b[0] + 10, b[3] - b[1] + 10
        pan = PC.panel("M", P)
        gd = f'<path d="{geom_to_path(affinity.translate(pan, -ox, -oy))}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
        open(f"{OUT}/HAKI_WAVE_{N}_{SLUG}_{P}_M_ART.svg", "w").write(SB.production_svg(V[P], stops, Wd, Hd, ox, oy))
        open(f"{OUT}/HAKI_WAVE_{N}_{SLUG}_{P}_M_ART+guides.svg", "w").write(SB.production_svg(V[P], stops, Wd, Hd, ox, oy, gd))
    json.dump(dict(width=WCK, bbox=BB, colours=sorted({r["col"] for r in ALLV})), open(f"{OUT}/summary.json", "w"), default=float)
    print("spec pages", len(pages))

if __name__ == "__main__":
    build()
