"""02 Chest mossy branch (02R + 02L, split at the zip) — 5-page spec + production art files."""
import os, json, pickle
import fbcore
import cairosvg
from PIL import Image, ImageDraw
from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely import affinity
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import geom_to_path, f
from motifs2 import HEX, PAL
import front as F
import tech, stitchrender as SR
import specbase as SB
from specbase import img_tag, direction_map, production_svg
import spec_back as SPB

REV = fbcore.REV_EMB; DATE = fbcore.DATE
OUT = "out/02_chest-branch"; os.makedirs(OUT, exist_ok=True)
VIS = pickle.load(open("front_vis.pkl", "rb"))
PIECES = ["02R", "02L"]
ALL = [r for p in PIECES for r in VIS[p]]
STOPS = {p: fbcore.stitch_stops(VIS[p]) for p in PIECES}
BBs = {p: unary_union([r["geom"] for r in VIS[p]]).bounds for p in PIECES}
CUR = json.load(open("dst_current.json")) if os.path.exists("dst_current.json") else {}
QA = json.load(open("qa_width.json"))
QA02 = {k: max([QA[p].get(k, {"long_pct": 0}) for p in PIECES], key=lambda d: d["long_pct"]) for p in PIECES for k in QA[p]}
FOOT = f"HAKI STUDIOS · {fbcore.NAME} · 02 chest branch · {REV} · {DATE}"
import front_scene as FS
MARKS = FS.zip_marks()

def header(title, sub, page):
    SB.FOOT = FOOT; return SB.header(title, sub, page)

def front_view_png(vis_all, bbox, ppm, highlight=None):
    x0, y0, x1, y1 = bbox; highlight = highlight or list(vis_all)
    img = SR.render([r for p in highlight for r in vis_all[p]], bbox, ppm, base=fbcore.FABRIC)
    W, H = img.size
    T = lambda cs: [((x - x0)*ppm, (y - y0)*ppm) for x, y in cs]
    mask = Image.new("L", (W, H), 0); d = ImageDraw.Draw(mask)
    for pnl in (F.PANEL_R, F.PANEL_L): d.polygon(T(pnl.exterior.coords), fill=255)
    out = Image.new("RGB", (W, H), (255, 255, 255)); out.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(out)
    for c in (F.COLLAR_R, F.COLLAR_L): d.polygon(T(c.exterior.coords), fill=(24, 24, 24), outline=(0, 0, 0))
    for w in (F.WELT_R, F.WELT_L): d.polygon(T(w.exterior.coords), outline=(20, 26, 22), fill=(34, 44, 38))
    d.rectangle([((-6 - x0)*ppm, (0 - y0)*ppm), ((6 - x0)*ppm, (F.HEM - y0)*ppm)], fill=(176, 138, 58))
    for pnl in (F.PANEL_R, F.PANEL_L): d.line(T(pnl.exterior.coords), fill=(40, 40, 40), width=3)
    return out

def clearances(p):
    u = unary_union([r["geom"] for r in VIS[p]]); b = u.bounds; side = "R" if b[2] < 0 else "L"
    mir = (lambda g: g) if side == "R" else F.mirror
    arm = mir(F.ARM_R); sd = mir(F.SIDE_R); col = F.COLLAR_R if side == "R" else F.COLLAR_L; wl = F.WELT_R if side == "R" else F.WELT_L
    cf = LineString([(0, -150), (0, 900)]); hem = LineString([(-400, F.HEM), (400, F.HEM)])
    return [("Art box " + p, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}"), ("  x range / y range", f"{b[0]:+.0f} to {b[2]:+.0f} / {b[1]:.0f} to {b[3]:.0f}"),
            ("  → CF (zip centre)", f"{u.distance(cf):.0f}"), ("  → shoulder + armhole seam", f"{u.distance(arm):.0f}"),
            ("  → side seam", f"{u.distance(sd):.0f}"), ("  → collar (lying flat)", f"{u.distance(col):.0f}"),
            ("  → welt pocket", f"{u.distance(wl):.0f}"), ("  → hem seam", f"{u.distance(hem):.0f}")]

def page1():
    o = header("02 · CHEST MOSSY BRANCH (split at zip) — stitch-out preview + placement",
               "Direct embroidery on both cut front panels, before zip + welts · two pieces registered across the CF zip · mm, finished size · art files 1:1 · size M (grade B)", "p1 / 5")
    bbox = (-325, -110, 325, 540); ppm = 2.6
    fv = front_view_png(VIS, bbox, ppm)
    w_mm = 152; s = w_mm / (bbox[2] - bbox[0]); ax, ay = 12, 29
    tag, h = img_tag(fv, ax, ay, w_mm); o.append(tag)
    X = lambda x: ax + (x - bbox[0])*s; Y = lambda y: ay + (y - bbox[1])*s
    for p in PIECES:
        b = BBs[p]
        o.append(f'<rect x="{f(X(b[0]))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{GUIDE}" stroke-width="0.25" stroke-dasharray="1.2 0.8"/>')
        o.append(t(X(b[0]) + 0.6, Y(b[3]) + 2.6, f"{p}: {b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.7, 700, GUIDE))
    o.append(t(ax, ay + h + 3.5, "Front view, size M (shown 0.23:1). Black = collar lying flat; gold = zip at CF; dark bars = welt pockets.", 1.8, 400, MUTED))
    rx = 172; o.append(t(rx, 33, "PLACEMENT (x from CF, + = wearer's left; y down from CF neck seam)", 2.1, 700)); yy = 38
    for a_, b_ in clearances("02R") + clearances("02L"):
        o.append(t(rx, yy, a_, 1.85, 400, MUTED)); o.append(t(rx + 48, yy, b_, 1.85, 600)); yy += 3.45
    yy += 2; o.append(t(rx, yy, "BY THE NUMBERS (read from the DST)", 2.3, 700)); yy += 4.4
    for p in PIECES:
        d = CUR.get(p, {})
        o.append(t(rx, yy, f"Piece {p}", 1.85, 400, MUTED))
        o.append(t(rx + 48, yy, f"{d.get('stitches', 0):,} st · {d.get('trims_dst', 0)} trims · {d.get('stops', 0)} stops · {d.get('threads', 0)} threads", 1.85, 600)); yy += 3.5
    tot = sum(CUR.get(p, {}).get("stitches", 0) for p in PIECES)
    o.append(t(rx, yy, "Est. run time / head", 1.85, 400, MUTED)); o.append(t(rx + 48, yy, f"≈ {tot/750:.0f} min at 750 spm + stops (both pieces)", 1.85, 600)); yy += 5
    for l in ["!Zip: art stops 15 each side of CF (teeth + tape + topstitch).", "The main limb is cut on the same y band each side so it reads",
              "as one branch passing behind the zip (marks below).",
              "!Hanging moss (02R) hangs from the main limb; strands end",
              "15 inside the armhole + shoulder seams (pattern seams, 10 mm",
              "forward shoulder per chart P)."]:
        c = ORANGE if l.startswith("!") else MUTED
        o.append(t(rx, yy, l.lstrip("!"), 1.75, 600 if c == ORANGE else 400, c)); yy += 3.2
    yy += 1.5; o.append(t(rx, yy, "ZIP MATCH MARKS (main limb at the 15 mm keep-out lines)", 2.1, 700)); yy += 4
    for xx, a, b in MARKS:
        o.append(t(rx, yy, f"x = {xx:+.0f}", 1.85, 600)); o.append(t(rx + 18, yy, f"limb from y {a:.0f} to {b:.0f} (centre {0.5*(a+b):.0f})", 1.85)); yy += 3.3
    return o

def page2():
    o = header("02 · STITCH-DIRECTION MAP + REGION CODES", "Hatch = stitch direction. Dark solid = line work (run). Labels = region code → stitch table p3.", "p2 / 5")
    xcur = 12
    widths = [(BBs[p][2]-BBs[p][0]) for p in PIECES]; scale = min(160 / max(BBs[p][3]-BBs[p][1] for p in PIECES), (172 - 6) / sum(widths))
    for p in PIECES:
        b = BBs[p]; bb = (b[0]-3, b[1]-3, b[2]+3, b[3]+3)
        dm = direction_map(VIS[p], bb, 5.0, label_min=40, label_mm=2.4)
        wmm = (bb[2]-bb[0])*scale; tag, hh = img_tag(dm, xcur, 30, wmm, 88); o.append(tag)
        o.append(f'<rect x="{f(xcur)}" y="30" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(xcur, 30 + hh + 3.2, f"Piece {p} (shown {scale:.2f}:1)", 1.9, 700)); xcur += wmm + 6
    zx = 192; o.append(t(zx, 32, "DETAIL CROPS (shown 2:1)", 2.4, 700)); yy = 35
    b = BBs["02R"]
    for c, cap in [((b[0] + 5, b[1] + 40, b[0] + 50, b[1] + 65), "Hanging moss: turning satin strands + light run"),
                   ((-120, 120, -75, 145), "Main limb: tatami along, padded moss across"),
                   ((60, 170, 105, 195), "Limb moss: padded across, lit top + lump runs")]:
        im = direction_map(ALL, c, 14, label_min=30, label_mm=1.2)
        wmm = (c[2]-c[0])*2; tag, hh = img_tag(im, zx, yy, wmm, 90); o.append(tag)
        o.append(f'<rect x="{zx}" y="{f(yy)}" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(zx, yy + hh + 3, cap, 1.75, 400, MUTED)); yy += hh + 6.5
    return o

def page3():
    o = header("02 · REGION STITCH TABLE — digitizing parameters per region code",
               "Same parameters as element 01 (shared system). Density = row spacing (mm). Pull comp = added width per side (mm). Width = measured share below minimum.", "p3 / 5")
    yb, tot = SPB.region_table(o, ALL, QA02)
    o.append(t(12, yb + 2, "Globals: 40wt polyester, 75/11 sharp needle, 2.5 oz cutaway, no topping. Satin > 7.0 wide → split satin. Tie-in/off every object.", 1.75, 400, MUTED))
    return o

def page4():
    o = header("02 · COLOUR STOP SEQUENCE + THREADS", "Order: leaves → bark + twigs → moss + hanging moss → bark line work (leaves first so their travel hides under the twigs). Thread codes = shared jacket palette (G3).", "p4 / 5")
    SPB.stops_table(o, STOPS["02R"], 12, 30.5, "PIECE 02R", width=134)
    SPB.stops_table(o, STOPS["02L"], 152, 30.5, "PIECE 02L", width=134)
    return o

def page5():
    o = header("02 · 1:1 DETAILS, WHAT CHANGED, PRODUCTION NOTES", "", "p5 / 5")
    o.append(t(14, 31, "1:1 STITCH-OUT DETAILS (print at 100% to check scale)", 2.6, 700))
    b = BBs["02R"]
    x = 14
    for c, cap in [((b[0] + 2, b[1] + 30, b[0] + 52, b[1] + 80), "Hanging moss from the limb"), ((-95, 110, -45, 160), "Main limb at the zip (02R)"),
                   ((20, 130, 70, 180), "02L: limb restarts after the zip"), ((150, 60, 200, 110), "Upper twig + leaf sprays")]:
        im = SR.render(ALL, c, 14, base=fbcore.FABRIC); tag, hh = img_tag(im, x, 35, c[2] - c[0]); o.append(tag)
        o.append(t(x, 35 + hh + 3, cap, 1.8, 600)); x += (c[2] - c[0]) + 4
    my = 98
    tag, hh = SHT.embed("inputs/front.png", (60, 60, 690, 500), 56, 14, my + 3); o.append(tag)
    o.append(t(14, my, "MOCKUP", 2.4, 700))
    o.append(t(76, my, "WHAT CHANGED vs MOCKUP (and why)", 2.4, 700))
    for i, c in enumerate(["Composition traced from the mockup: mossy limb from the wearer's",
                           "  right shoulder across the zip to the left chest, upper twig on",
                           "  02L, leaf sprays all along; moss hanging over the right shoulder.",
                           "Zip: the mockup runs the branch over the zip — impossible.",
                           "  Split into 02R + 02L, each stopping 15 from CF.",
                           "Shoulder: mockup moss touches the armhole/shoulder seams.",
                           "  Starts 15 inside the pattern seams; strands hang from the",
                           "  limb (LESSONS A1), longest ends ≥ 15 above the welt.",
                           "Collar: twig tips under the collar pulled 6 clear; sprays cut",
                           "  off from their twig by a keep-out are removed (nothing floats).",
                           "Moss, bark + leaves use the 01 system (same codes + threads)."]):
        o.append(t(76, my + 4.5 + i*3.3, c, 1.85))
    o.append(t(196, my, "PRODUCTION", 2.4, 700))
    for i, c in enumerate(["Embroider the cut front panels flat, BEFORE",
                           "  zip, welt pockets and side seams.",
                           "Mark the welt boxes on the panel before",
                           "  hooping (welts are cut after embroidery).",
                           "Canvas: 75/11 sharp, 2.5 oz cutaway, no",
                           "  topping. Polyester thread; wash test if",
                           "  the jacket is washed after embroidery.",
                           "Hoop each front panel once (≤ 344 × 344);",
                           "  the two pieces are registered to CF ± 1.",
                           "Sew-out on production canvas before bulk."]):
        o.append(t(196, my + 4.5 + i*3.3, c, 1.85))
    return o

def build():
    pages = [page1(), page2(), page3(), page4(), page5()]
    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"e02_{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_02_p{i}.png", output_width=2400)
        w.append(PdfReader(f"e02_{i}.pdf"))
    w.write(f"{OUT}/HAKI_FB_02_chest-branch_SPEC_{REV.replace(' ', '')}.pdf")
    for p in PIECES:
        b = BBs[p]; ox, oy = b[0] - 5, b[1] - 5; Wd, Hd = b[2] - b[0] + 10, b[3] - b[1] + 10
        panel = F.PANEL_R if p == "02R" else F.PANEL_L
        gd = (f'<path d="{geom_to_path(affinity.translate(panel, -ox, -oy))}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
              f'<line x1="{f(-ox)}" y1="0" x2="{f(-ox)}" y2="{f(Hd)}" stroke="#00A3FF" stroke-width="0.3" stroke-dasharray="4 2"/>')
        open(f"{OUT}/HAKI_FB_02_chest-branch_{p}_ART.svg", "w").write(production_svg(VIS[p], STOPS[p], Wd, Hd, ox, oy))
        open(f"{OUT}/HAKI_FB_02_chest-branch_{p}_ART+guides.svg", "w").write(production_svg(VIS[p], STOPS[p], Wd, Hd, ox, oy, gd))
    UB = unary_union([r["geom"] for r in ALL]).bounds
    SR.render(ALL, (UB[0]-6, UB[1]-6, UB[2]+6, UB[3]+6), 7, base=fbcore.FABRIC).save(f"{OUT}/HAKI_FB_02_chest-branch_STITCH-PREVIEW.png")
    print("02 stops", {p: len(STOPS[p]) for p in PIECES}, "boxes", {p: [round(v) for v in BBs[p]] for p in PIECES})

if __name__ == "__main__":
    build()
