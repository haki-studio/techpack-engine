"""01 Back scene — 5-page digitizing spec + production art files (size M, grade B)."""
import os, json, pickle
import fbcore
import cairosvg
from PIL import Image, ImageDraw
from shapely.ops import unary_union
from shapely import affinity
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, dim_h, dim_v, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import geom_to_path, f
from motifs2 import HEX, PAL
import back as B
import tech, stitchrender as SR
import specbase as SB
from specbase import img_tag, direction_map, production_svg

REV = fbcore.REV_EMB; DATE = fbcore.DATE
OUT = "out/01_back-scene"; os.makedirs(OUT, exist_ok=True)
VB = pickle.load(open("back_vis.pkl", "rb"))["back"]
STOPS = fbcore.stitch_stops(VB)
TOT = sum(s["st"] for s in STOPS)
UB = unary_union([r["geom"] for r in VB]); BB = UB.bounds
PH = B.PH_BOX.bounds
FOOT = f"HAKI STUDIOS · {fbcore.NAME} · 01 back scene · {REV} · {DATE}"
CUR = json.load(open("dst_current.json")) if os.path.exists("dst_current.json") else {}
SPL = json.load(open("dst_splits_B.json")) if os.path.exists("dst_splits_B.json") else {}
QA = json.load(open("qa_width.json"))["back"]
from shapely.ops import nearest_points as _np
def _ctr(x, y, w, h): return (x - w/2, y - h/2, x + w/2, y + h/2)
LIMB = B.P(270, 340)
_lr = unary_union([r["geom"] for r in VB if r["grp"] == "LR"]); _lf = unary_union([r["geom"] for r in VB if r["grp"] == "LF"])
RAYLEAF = _np(_lr, _lf)[1].coords[0]
ROCK = B.P(215, 650)
PHC = ((PH[0]+PH[2])/2, (PH[1]+PH[3])/2)
LIC = "LICENSED FIGURE — placeholder only. Nothing stitched inside; the factory digitizer adds it from the licensor-approved artwork."

def header(title, sub, page):
    SB.FOOT = FOOT; return SB.header(title, sub, page)

def page1():
    o = header("01 · BACK SCENE — stitch-out preview + placement",
               "Direct embroidery on the cut back panel, before assembly · mm, finished size · art files 1:1 · garment coords: x from CB, y down from CB neck seam · size M (grade B)", "p1 / 5")
    ppm = 3.2; bx0, by0, bx1, by1 = -305, -30, 305, 590
    img = SR.render(VB, (bx0, by0, bx1, by1), ppm, base=fbcore.FABRIC)
    mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).polygon([((x-bx0)*ppm, (y-by0)*ppm) for x, y in B.PANEL.exterior.coords], fill=255)
    bg = Image.new("RGB", img.size, (255, 255, 255)); bg.paste(img, (0, 0), mask)
    ImageDraw.Draw(bg).line([((x-bx0)*ppm, (y-by0)*ppm) for x, y in B.PANEL.exterior.coords], fill=(60, 60, 60), width=3)
    w_mm = 150; s = w_mm / (bx1 - bx0); ax, ay = 14, 31
    tag, h = img_tag(bg, ax, ay, w_mm); o.append(tag)
    X = lambda x: ax + (x - bx0)*s; Y = lambda y: ay + (y - by0)*s
    o.append(f'<rect x="{f(X(BB[0]))}" y="{f(Y(BB[1]))}" width="{f((BB[2]-BB[0])*s)}" height="{f((BB[3]-BB[1])*s)}" fill="none" stroke="{GUIDE}" stroke-width="0.25" stroke-dasharray="1.2 0.8"/>')
    o.append(dim_h(X(BB[0]), X(BB[2]), Y(BB[1]) - 2.2, f"art {BB[2]-BB[0]:.0f}", 1.9, col=GUIDE))
    o.append(dim_v(Y(BB[1]), Y(BB[3]), X(BB[0]) - 3, f"{BB[3]-BB[1]:.0f}", 1.9, col=GUIDE))
    o.append(f'<rect x="{f(X(PH[0]))}" y="{f(Y(PH[1]))}" width="{f((PH[2]-PH[0])*s)}" height="{f((PH[3]-PH[1])*s)}" fill="#FFFFFF" fill-opacity="0.35" stroke="{RED}" stroke-width="0.35"/>')
    o.append(t(X(PH[2]) + 1.5, Y(PH[1]) + 2, "LICENSED", 1.6, 700, RED)); o.append(t(X(PH[2]) + 1.5, Y(PH[1]) + 4.2, "placeholder", 1.6, 600, RED))
    o.append(t(ax, ay + h + 4, "Stitch-out preview, back panel, size M (shown 0.25:1). Each region drawn with its own thread rows at its specified angle. Red box = licensed-figure placeholder.", 1.8, 400, MUTED))
    rx = 172
    o.append(t(rx, 33, "PLACEMENT", 2.6, 700))
    facts = [("Art box (back panel)", f"{BB[2]-BB[0]:.0f} × {BB[3]-BB[1]:.0f}"), ("Left edge → CB", f"{-BB[0]:.0f} left of CB"),
             ("Right edge → CB", f"{BB[2]:.0f} right of CB"), ("Top of art → CB neck seam", f"{BB[1]:.0f} down"),
             ("Bottom of art → hem-rib seam", f"{B.HEM - BB[3]:.0f} above"), ("Side seams + armholes", f"≥ {B.KEEP_SIDE:.0f} clear (nothing wraps)"),
             ("Shoulder seams / collar", f"≥ {B.KEEP_SH:.0f} / ≥ {B.KEEP_COLLAR:.0f} below the collar (fall {B.COLLAR_FALL:.0f}, proposed)"),
             ("Hoopings", "4 × 360² split files (S1–S4) or a border frame")]
    for i, (a, b) in enumerate(facts):
        o.append(t(rx, 38 + i*3.7, a, 1.9, 400, MUTED)); o.append(t(rx + 44, 38 + i*3.7, b, 1.9, 600))
    o.append(t(rx, 72, "BY THE NUMBERS (read from the DST)", 2.6, 700))
    d = CUR.get("back", {})
    nums = [("Stitches, single file", f"{d.get('stitches', 0):,}"), ("Trims (DST read-back)", f"{d.get('trims_dst', 0):,}"),
            ("Colour stops / threads", f"{d.get('stops', len(STOPS))} / {d.get('threads', '—')} (incl. placeholder basting)"),
            ("Max stitch", f"{d.get('max_stitch', 0)} mm"), ("Regions (digitizing objects)", f"{len(VB)}"),
            ("Est. run time / head", f"≈ {d.get('stitches', 0)/750/60:.1f} h at 750 spm + stops")]
    for i, (a, b) in enumerate(nums):
        o.append(t(rx, 77 + i*3.7, a, 1.9, 400, MUTED)); o.append(t(rx + 44, 77 + i*3.7, b, 1.9, 600))
    y = 104
    o.append(t(rx, y, "LICENSED FIGURE PLACEHOLDER (stream)", 2.6, 700, RED)); y += 5
    for a, b in [("Box", f"{PH[2]-PH[0]:.0f} × {PH[3]-PH[1]:.0f}  [proposed — confirm with the licensor art]"),
                 ("Box top-left", f"x {PH[0]:+.0f} (from CB), y {PH[1]:.0f} (from CB neck)"),
                 ("Box centre", f"x {(PH[0]+PH[2])/2:+.0f}, y {(PH[1]+PH[3])/2:.0f}")]:
        o.append(t(rx, y, a, 1.9, 400, MUTED)); o.append(t(rx + 20, y, b, 1.9, 600)); y += 3.7
    for l in ["Not drawn by Haki: no orb, star or lookalike is in these files.",
              "Stitch file: stop 1 = blue basting outline of the box (water-",
              "soluble / remove after); nothing is stitched inside it. Stream",
              "water runs around the box, 1 mm clear of its outline.",
              "Pattern: box drawn on B01 (DXF layer 8). The factory digitizer",
              "adds the figure from the licensor-approved artwork, sized to",
              "the box, sewn after the stream (sits on top of the water edge).",
              "Licence approval not verified by Haki tech — confirm before bulk."]:
        o.append(t(rx, y, l, 1.8, 600 if "Not drawn" in l or "verified" in l else 400, RED if "verified" in l else INK)); y += 3.3
    return o

def page2():
    o = header("01 · STITCH-DIRECTION MAP + REGION CODES",
               "Hatch = stitch direction of every fill/satin region. Dark solid = line work (run). Labels = region code → stitch table p3.", "p2 / 5")
    dm = direction_map(VB, (BB[0]-4, BB[1]-4, BB[2]+4, BB[3]+4), 4.0)
    tag, h = img_tag(dm, 14, 29, 146, 88); o.append(tag)
    o.append(f'<rect x="14" y="29" width="146" height="{f(h)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
    zx = 168; o.append(t(zx, 32, "DETAIL CROPS (shown 1.6:1)", 2.6, 700))
    c1 = _ctr(*LIMB, 60, 35); c2 = _ctr(*PHC, 80, 47); c3 = _ctr(*RAYLEAF, 60, 35)
    yy = 35
    for c, cap in [(c1, "Main limb: tatami along the limb, padded moss across it, navy lump runs"),
                   (c2, "Stream around the licensed placeholder: horizontal tatami, ripple satins"),
                   (c3, "Leaf sprays (feather satin ±45°) over the sheer light rays (serpentine run)")]:
        im = direction_map(VB, c, 14, label_min=12, label_mm=1.5)
        w = 98; tag, hh = img_tag(im, zx, yy, w, 90); o.append(tag)
        o.append(f'<rect x="{zx}" y="{f(yy)}" width="{w}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(zx, yy + hh + 3, cap, 1.8, 400, MUTED)); yy += hh + 6.5
    return o

def region_table(o, vis, qa_, y0=31):
    stats = {}
    for r in vis:
        k = tech.rule_for(r["grp"]); s = stats.setdefault(k, dict(st=0, n=0, cols=set()))
        s["st"] += tech.stitches(r); s["n"] += 1; s["cols"].add(r["col"])
    hdr = ["Code", "Region", "Thread(s)", "Stitch", "Angle", "Dens.", "Len.", "Underlay", "Pull", "Notes", "Width", "Obj.", "Est. st."]
    cx = [12, 29, 66, 92, 124, 157, 166, 175, 214, 222, 251, 263, 272]
    for x, h in zip(cx, hdr): o.append(t(x, y0, h, 1.75, 700, MUTED))
    order = [k for k in tech.RULES if k in stats]; rh = min(3.62, 130 / max(1, len(order)))
    for i, k in enumerate(order):
        y = y0 + 3.6 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.5)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        name, st, ang, dens, ln, ul, pull, note = tech.RULES[k]; s = stats[k]
        o.append(t(cx[0], y, k, 1.7, 700)); o.append(t(cx[1], y, name, 1.6))
        xs = cx[2]
        for c in sorted(s["cols"], key=lambda c: tech.COLOUR_ORDER.index(c))[:5]:
            o.append(swatch(xs, y, c, 3.2, 2.2)); xs += 4.2
        for j, v in enumerate((st, ang, dens, ln, ul, pull, note)):
            o.append(t(cx[3 + j], y, v if (j != 6 or len(v) <= 26) else v[:26].rsplit(' ', 1)[0] + '…', 1.55))
        q = qa_.get(k, {}).get("long_pct", 0.0); qc = GREEN if q < 1.0 else (ORANGE if q < 3.5 else RED)
        o.append(t(cx[10], y, "—" if k == "PH" else f"{q:.1f}%", 1.6, 600, qc))
        o.append(t(cx[11], y, f"{s['n']}", 1.6, 400, MUTED)); o.append(t(cx[12], y, f"{s['st']:,.0f}", 1.6, 600))
    return y0 + 3.6 + len(order)*rh + 2, sum(s["st"] for s in stats.values())

def page3():
    o = header("01 · REGION STITCH TABLE — digitizing parameters per region code",
               "Density = row spacing (mm). Pull comp = added width per side (mm). Est. st. = area estimate (the DST count on p1 is the real number). Width = share of the code's area below its minimum.", "p3 / 5")
    yb, tot = region_table(o, VB, QA)
    o.append(t(12, yb + 2, "Globals: 40wt polyester, 75/11 sharp needle, 2.5 oz cutaway, no topping. Satin > 7.0 wide → split satin. Tie-in/off every object; trims at exposed moves > 2.5.", 1.75, 400, MUTED))
    o.append(t(12, yb + 5.2, "Width = share of area narrower than its minimum (fill/satin 0.8, line 0.6) for > 2.5 mm, on the art. Green < 1%; amber = tapered tips (grass, twig ends) the digitizer absorbs.", 1.75, 400, MUTED))
    o.append(t(12, yb + 8.4, "Light rays (LR): serpentine single run, rows 1.9 apart — a sheer veil, not a fill. Each tone is one continuous object so the ray has no trims inside it.", 1.75, 600, INK))
    return o

def stops_table(o, stops, x0, y0, title, width=185, sews=True):
    o.append(t(x0, y0, title, 2.2, 700))
    hdr = ["Stop", "Thread", "Isacord", "Madeira Polyneon", "Sews", "Est. st."]; cx = [x0, x0 + 10, x0 + 36, x0 + 62, x0 + 92, x0 + width - 16]
    for x, h in zip(cx, hdr): o.append(t(x, y0 + 4, h, 1.7, 700, MUTED))
    rh = min(3.3, 140 / max(1, len(stops)))
    for i, s in enumerate(stops):
        y = y0 + 7.5 + i*rh; k = s["col"]; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
        if i % 2 == 0: o.append(f'<rect x="{x0-1}" y="{f(y-2.4)}" width="{width}" height="{f(rh)}" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, f"{i+1:02d}", 1.6, 700)); o.append(swatch(cx[1], y, k, 3.2, 2.2)); o.append(t(cx[1] + 4.2, y, PAL[k][1][:16], 1.5))
        if k == "basting":
            o.append(t(cx[2], y, "water-soluble basting, contrast blue — REMOVE", 1.5, 600, RED))
        else:
            o.append(t(cx[2], y, f"{iso[0]} {iso[1]}"[:18], 1.5)); o.append(t(cx[3], y, f"{pn[0]} {pn[1]}"[:20], 1.5))
        lay = tech.LAYER_NAMES.get(s["layers"][0], "")
        o.append(t(cx[4], y, (lay + ": " + ", ".join(s["groups"]))[:48], 1.45, 400, MUTED)); o.append(t(cx[5], y, f"{s['st']:,.0f}", 1.55))

def thread_match(o, sx, ty, keys):
    o.append(t(sx, ty, "THREAD MATCH (ΔE2000)", 2.2, 700)); o.append(t(sx, ty + 3.6, "Target / Isacord / Polyneon", 1.6, 600, MUTED))
    for i, k in enumerate(keys):
        y = ty + 7 + i*3.15; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
        o.append(f'<rect x="{sx}" y="{f(y-2.3)}" width="3" height="2.4" fill="{HEX[k]}"/>')
        if k == "basting":
            o.append(t(sx + 11, y, "Placement basting — any water-soluble thread", 1.5, 600, RED)); continue
        o.append(f'<rect x="{sx+3.3}" y="{f(y-2.3)}" width="3" height="2.4" fill="{iso[2]}"/>')
        o.append(f'<rect x="{sx+6.6}" y="{f(y-2.3)}" width="3" height="2.4" fill="{pn[2]}"/>')
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(t(sx + 11, y, f"{PAL[k][1][:15]}", 1.5))
        o.append(t(sx + 35, y, f"{iso[0]}", 1.5, 600, ci)); o.append(t(sx + 43, y, f"{iso[3]:.1f}", 1.45, 400, ci))
        o.append(t(sx + 50, y, f"{pn[0]}", 1.5, 600, cp)); o.append(t(sx + 58, y, f"{pn[3]:.1f}", 1.45, 400, cp))
    return ty + 7 + len(keys)*3.15

def page4():
    o = header("01 · COLOUR STOP SEQUENCE + THREADS",
               "Sewing order, back to front: placeholder basting → light rays → stream → grass behind → rocks → leaves → bark + twigs → moss → bark line work → grass in front (leaves before twigs: their travel hides under the twig). Fills before the lines on them.", "p4 / 5")
    stops_table(o, STOPS, 12, 30.5, "BACK PANEL (single file, size M)")
    sx = 204; yb = thread_match(o, sx, 33, [k for k in PAL])
    for i, l in enumerate(["ΔE < 3 green: close match. 3–5.5 amber,", "> 5.5 red: pick from the physical card.",
                           "Chart RGB; screens + dye lots vary —", "approve a thread board before sampling."]):
        o.append(t(sx, yb + 2 + i*3.2, l, 1.6, 400, MUTED))
    return o

def page5():
    o = header("01 · 1:1 DETAILS, WHAT CHANGED, PRODUCTION NOTES", "", "p5 / 5")
    o.append(t(14, 31, "1:1 STITCH-OUT DETAILS (print at 100% to check scale)", 2.6, 700))
    crops = [(_ctr(*LIMB, 50, 50), "Mossy main limb"), (_ctr(*PHC, 66, 56), "Placeholder box in the stream (empty)"),
             (_ctr(*RAYLEAF, 50, 50), "Leaf sprays over light rays"), (_ctr(*ROCK, 50, 50), "Grass + mossy rock")]
    x = 14
    for c, cap in crops:
        im = SR.render(VB, c, 14, base=fbcore.FABRIC); tag, hh = img_tag(im, x, 35, c[2] - c[0]); o.append(tag)
        o.append(t(x, 35 + hh + 3, cap, 1.8, 600)); x += (c[2] - c[0]) + 4
    my = 98
    tag, hh = SHT.embed("inputs/back.png", (60, 60, 670, 720), 52, 14, my + 3); o.append(tag)
    o.append(t(14, my, "MOCKUP", 2.4, 700))
    o.append(t(70, my, "WHAT CHANGED vs MOCKUP (and why)", 2.4, 700))
    ch = ["Composition re-traced from the mockup: mossy limb from the left,",
          "  trunk down the right, upper twigs + ~35 leaf sprays, 4 light rays,",
          "  stream, 9 mossy rocks, grass in front and behind.",
          "ORB in the stream: LICENSED — not drawn. Marked placeholder box",
          f"  {PH[2]-PH[0]:.0f} × {PH[3]-PH[1]:.0f} at the mockup position; water continues round it.",
          "Sides + armholes: mockup art runs into the seams. Pulled 15 inside",
          "  (outer art compressed inward); nothing wraps onto the sleeves.",
          "Bottom: mockup runs into the rib. Stops 10 above the hem seam.",
          "Light rays: mockup reads as painted bands. Sheer serpentine run",
          "  (sage edges, cream core) so the fabric shows through (brief).",
          "Moss: mockup chain-stitch texture → raised padded lumps + dark",
          "  underside + lit top + navy/olive lump runs (mottled).",
          "Leaves: two-tone feather satin; grass blades blunt-tipped (≥ 1.1).",
          "Clip check: leaf sprays cut off from their twig by a keep-out are",
          "  removed (nothing floats, LESSONS A1)."]
    for i, c in enumerate(ch): o.append(t(70, my + 4.5 + i*3.3, c, 1.8, 600 if "LICENSED" in c else 400, RED if "LICENSED" in c else INK))
    px = 190
    o.append(t(px, my, "PRODUCTION", 2.4, 700))
    pn = ["Hoop: 4 × 360² split files S1–S4 with basting",
          "  registration crosses (G5), or a border frame",
          f"  ≥ {BB[2]-BB[0]+14:.0f} × {BB[3]-BB[1]+14:.0f} for the single file.",
          "Embroider the cut back panel flat, BEFORE side,",
          "  shoulder and armhole seams.",
          "Canvas: 75/11 sharp, 2.5 oz cutaway, no topping.",
          "Padded moss: one padding layer only (stiffness).",
          "Stop 1 basting box: remove after the licensed",
          "  figure is sewn (factory, licensor art).",
          "Washed shell: confirm dye route; wash-test the",
          "  sew-out (cream + leaf greens shift first).",
          "Lining: cut after the embroidered panel is pressed",
          "  (dense back shrinks the panel ~1.5–2.5 %).",
          "Sew-out on production canvas before bulk."]
    for i, c in enumerate(pn): o.append(t(px, my + 4.5 + i*3.3, c, 1.8))
    return o

def build():
    pages = [page1(), page2(), page3(), page4(), page5()]
    w = PdfWriter()
    for i, p in enumerate(pages, 1):
        svg = doc(p)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"q{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev2_p{i}.png", output_width=2400)
        w.append(PdfReader(f"q{i}.pdf"))
    w.write(f"{OUT}/HAKI_FB_01_back-scene_SPEC_{REV.replace(' ', '')}.pdf")
    ox, oy = BB[0] - 5, BB[1] - 5; W, H = BB[2] - BB[0] + 10, BB[3] - BB[1] + 10
    pan = affinity.translate(B.PANEL, -ox, -oy); phb = affinity.translate(B.PH_BOX, -ox, -oy).bounds
    gd = (f'<path d="{geom_to_path(pan)}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
          f'<line x1="{f(-ox)}" y1="0" x2="{f(-ox)}" y2="{f(H)}" stroke="#00A3FF" stroke-width="0.3" stroke-dasharray="4 2"/>'
          f'<g id="LICENSED_FIGURE_placeholder"><rect x="{f(phb[0])}" y="{f(phb[1])}" width="{f(phb[2]-phb[0])}" height="{f(phb[3]-phb[1])}" fill="none" stroke="#FF3B30" stroke-width="0.4"/>'
          f'<text x="{f(phb[0]+1)}" y="{f(phb[1]+4)}" font-size="2.6" fill="#FF3B30">LICENSED FIGURE</text>'
          f'<text x="{f(phb[0]+1)}" y="{f(phb[1]+7.5)}" font-size="2.2" fill="#FF3B30">placeholder — licensor art</text></g>')
    open(f"{OUT}/HAKI_FB_01_back-scene_ART.svg", "w").write(production_svg(VB, STOPS, W, H, ox, oy))
    open(f"{OUT}/HAKI_FB_01_back-scene_ART+guides.svg", "w").write(production_svg(VB, STOPS, W, H, ox, oy, gd))
    SR.render(VB, (BB[0]-6, BB[1]-6, BB[2]+6, BB[3]+6), 6, base=fbcore.FABRIC).save(f"{OUT}/HAKI_FB_01_back-scene_STITCH-PREVIEW.png")
    direction_map(VB, (BB[0]-4, BB[1]-4, BB[2]+4, BB[3]+4), 6).save(f"{OUT}/HAKI_FB_01_back-scene_DIRECTION-MAP.png")
    print("stops", len(STOPS), "est stitches", round(TOT), "regions", len(VB))

if __name__ == "__main__":
    build()
