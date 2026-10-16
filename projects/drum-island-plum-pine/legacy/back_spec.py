import os, json, pickle, random
import cairosvg
from shapely import affinity
from shapely.geometry import box, Point
from shapely.ops import unary_union
from pypdf import PdfWriter, PdfReader
import sheet as SH
from sheet import t, dim_h, dim_v, header, swatch, embed, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN
from render import geom_to_path, f, stack_svg, png
from motifs import *
import garment as G
import export

A = pickle.load(open("back_A.pkl", "rb")); B = pickle.load(open("back_B.pkl", "rb"))
QA = json.load(open("qa_back.json"))
OUT = "out/01_back-scene"; os.makedirs(OUT, exist_ok=True)

STITCH = {
    "snow": "Tatami; padded underlay on trunk snow",
    "shadow": "Satin crescents; mist + outline: triple run",
    "bark": "Tatami along limb; twigs < 3: satin",
    "barkdk": "Bean stitch (triple run)",
    "plum": "Satin, radial per petal",
    "petal": "Satin rims / dots",
    "plumdk": "Bean outlines; calyx satin",
    "gold": "Satin dots; inner zone tatami; needles bean",
    "orange": "Satin",
    "leaf": "Satin, split at midrib",
    "leaflt": "Run stitch",
    "indigo": "Satin along blade",
    "lavender": "Satin / run",
    "vermilion": "Tatami, radial from hub",
}

def art_group(vis, ox, oy, s, clipW=None, clipH=None):
    stack = [(f"{z}", col, g) for z, col, g, role in vis]
    o = [f'<g transform="translate({f(ox)} {f(oy)}) scale({f(s)})">']
    for _, col, g in stack:
        d = geom_to_path(g)
        if d: o.append(f'<path d="{d}" fill="{HEX[col]}" fill-rule="evenodd"/>')
    o.append("</g>")
    return "".join(o)

def tot_stitches(tag): return sum(r["stitches"] for r in QA[tag]["rows"])

# =============================================================== PAGE 1 — art + placement
def page1():
    o = header("01 · BACK SCENE — snow plum, red + white pine, bamboo, mist",
               "Direct embroidery on the cut back panel before assembly · all dimensions in mm, finished size · "
               "art files 1:1 · defines the shared motif + thread system for elements 02–04", "p1 / 3")
    s = 0.285; ax, ay = 22, 40
    o.append(t(ax, ay - 7, "A · ART — OPTION A, FULL BACK (shown 0.285:1)", 2.6, 700))
    o.append(f'<rect x="{f(ax)}" y="{f(ay)}" width="{f(A["W"]*s)}" height="{f(A["H"]*s)}" fill="{FABRIC}"/>')
    o.append(art_group(A["vis"], ax, ay, s))
    o.append(dim_h(ax, ax + A["W"]*s, ay - 2.4, f"{A['W']:.0f}"))
    o.append(dim_v(ay, ay + A["H"]*s, ax - 4, f"{A['H']:.0f}"))
    # option B outline overlay (centred, bottom-aligned)
    bw, bh = B["W"]*s, B["H"]*s
    o.append(f'<rect x="{f(ax + (A["W"]*s - bw)/2)}" y="{f(ay + A["H"]*s - bh)}" width="{f(bw)}" height="{f(bh)}" '
             f'fill="none" stroke="{GUIDE}" stroke-width="0.3" stroke-dasharray="1.4 0.9"/>')
    o.append(t(ax + (A["W"]*s - bw)/2 + 1, ay + A["H"]*s - bh - 1.2, f"Option B frame: same art scaled to {B['W']:.0f} × {B['H']:.0f}", 1.9, 600, GUIDE))
    o.append(t(ax, ay + A["H"]*s + 6, f"14 threads · est. {tot_stitches('A')/1000:.0f}k stitches (Option A) / {tot_stitches('B')/1000:.0f}k (Option B), ±25%", 2.2, 600))
    o.append(t(ax, ay + A["H"]*s + 9.6, "Art edges are the design limit: trunk base and red-pine branch end flat at the box edge by design.", 2.0, 400, MUTED))

    # B · placement
    ps = 0.145; px, py = 222, 52
    o.append(t(170, 33, "B · PLACEMENT ON BACK PANEL (size M, shown 0.145:1)", 2.6, 700))
    o += G.svg_back(px, py, ps)
    for tag, D, col, dash, bottom in (("A", A, RED, "", 10.0), ("B", B, GUIDE, "1.2 0.8", 15.0)):
        x0 = -D["W"]/2; y1 = G.BACK_LEN - bottom; y0 = y1 - D["H"]
        o.append(f'<rect x="{f(px + x0*ps)}" y="{f(py + y0*ps)}" width="{f(D["W"]*ps)}" height="{f(D["H"]*ps)}" fill="none" '
                 f'stroke="{col}" stroke-width="0.35" {"stroke-dasharray=" + chr(34) + dash + chr(34) if dash else ""}/>')
    # dims for A
    y1 = G.BACK_LEN - 10; y0 = y1 - A["H"]
    o.append(dim_h(px - A["W"]/2*ps, px + A["W"]/2*ps, py + y0*ps - 2.2, f"A {A['W']:.0f}, centred on CB", 1.8, col=RED))
    o.append(dim_v(py + 0, py + y0*ps, px - 372*ps, f"{y0:.0f}", 1.9, col=RED))
    o.append(dim_v(py + y1*ps, py + G.BACK_LEN*ps, px - 372*ps, "10", 1.9, col=RED))
    o.append(t(px - 368*ps, py - 1.2, "CB collar seam", 1.7, 400, RED))
    o.append(t(px - 368*ps, py + (G.BACK_LEN)*ps + 3.2, "hem seam", 1.7, 400, RED))
    ly = py + (G.BACK_LEN + G.RIB + 22)*ps
    leg = [("#FF8A30", f"Keep-out: {G.KEEP_SEAM:.0f} mm from shoulder, armhole + side seams (allowance + topstitch + 3)"),
           (RED, f"Option A box — bottom {10} above hem seam; clear of keep-out on all sides"),
           (GUIDE, f"Option B box — {B['W']:.0f} × {B['H']:.0f}, bottom 15 above hem seam"),
           (GUIDE, "Blue centre line = CB. Rib is knit: never embroidered.")]
    for i, (c, s_) in enumerate(leg):
        o.append(f'<rect x="170" y="{f(ly + i*3.6 - 2.2)}" width="4" height="2.6" fill="{c}" fill-opacity="0.7"/>')
        o.append(t(176, ly + i*3.6, s_, 1.95))
    # clearance table
    ty = ly + 17
    o.append(t(170, ty, "Measured clearances (assumed size-M panel)", 2.1, 700))
    rows = [("Design → armhole seam (top corners)", "≥ 42", "≥ 88"), ("Design → side seam (bottom corners)", "≥ 47", "≥ 92"),
            ("Design → hem seam", "10", "15"), ("Design → CB collar seam", f"{y0:.0f}", f"{G.BACK_LEN - 15 - B['H']:.0f}")]
    o.append(t(232, ty + 4, "Option A", 1.9, 700, RED)); o.append(t(252, ty + 4, "Option B", 1.9, 700, GUIDE))
    for i, (a, b, c) in enumerate(rows):
        yy = ty + 7.6 + i*3.4
        o.append(t(170, yy, a, 1.9)); o.append(t(232, yy, b, 1.9, 600)); o.append(t(252, yy, c, 1.9, 600))
    return o

# =============================================================== PAGE 2 — shared system: threads + motif library
def motif_cell(x, y, label, dims, geoms_by_col, scale, w=40, h=34):
    o = [f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{FABRIC}" rx="0.8"/>']
    allg = unary_union([g for _, g in geoms_by_col])
    bx = allg.bounds; cw, ch = (bx[2]-bx[0])*scale, (bx[3]-bx[1])*scale
    tx, ty = x + (w - cw)/2 - bx[0]*scale, y + (h - 6 - ch)/2 - bx[1]*scale
    o.append(f'<g transform="translate({f(tx)} {f(ty)}) scale({f(scale)})">')
    for col, g in geoms_by_col:
        o.append(f'<path d="{geom_to_path(g)}" fill="{HEX[col]}" fill-rule="evenodd"/>')
    o.append("</g>")
    o.append(t(x + 1.2, y + h - 3.2, label, 1.95, 700)); o.append(t(x + 1.2, y + h - 0.8, dims, 1.7, 400, MUTED))
    return o

def page2():
    o = header("01 · SHARED SYSTEM — threads + motif library (used by every element on this jacket)",
               "Fixed mm values. Elements 02–04 reuse these motifs at these sizes; only placement and composition change.", "p2 / 3")
    # threads
    o.append(t(14, 34, "C · THREADS — 14 colours, one 15-needle setup for the whole jacket", 2.6, 700))
    o.append(t(14, 38.4, "40wt polyester (bleach-fast). Match to approved lab-dip; hex values are on-screen targets.", 1.9, 400, MUTED))
    hy = 43.5
    for x, h in ((14, "#"), (19, ""), (26, "Thread"), (55, "Hex"), (69, "Used for"), (122, "Stitch")):
        o.append(t(x, hy, h, 1.8, 700, MUTED))
    for i, (k, (hx, name, use)) in enumerate(PAL.items()):
        yy = hy + 4.2 + i*4.25
        o.append(t(14, yy, f"{i+1:02d}", 1.9, 600, MUTED)); o.append(swatch(19, yy, k))
        o.append(t(26, yy, name, 2.0, 600)); o.append(t(55, yy, hx, 1.85, 400, MUTED))
        o.append(t(69, yy, use, 1.8)); o.append(t(122, yy, STITCH[k], 1.75, 400, MUTED))
    # motif library
    mx, my = 14, 112
    o.append(t(mx, my - 3, "D · MOTIF LIBRARY (shown 1:1 unless noted)", 2.6, 700))
    cells = []
    def bl(d): b = blossom(0, 0, d, 0); return [("plum", b["plum"]), ("petal", b["petal"]), ("plumdk", b["plumdk"]), ("gold", b["gold"]), ("orange", b["orange"])]
    cells.append(("Blossom L", "Ø 40–44", bl(43.5), 0.62))
    cells.append(("Blossom M", "Ø 28–34", bl(30), 0.85))
    cells.append(("Blossom S", "Ø 16–22  (8 stamens below 22)", bl(18), 1.0))
    bd = bud(0, 0, 7.0, 120)
    cells.append(("Bud", "Ø 5.6–8, calyx toward twig", [("plum", bd["plum"]), ("plumdk", bd["plumdk"]), ("petal", bd["petal"])], 2.4))
    lc = leaf_cluster(0, 0, 27, [70, 100, 130], rng=random.Random(3))
    cells.append(("Leaf cluster", "leaf 22–30 long, snow top 26%", [("leaf", lc["leaf"]), ("leaflt", lc["leaflt"]), ("snow", lc["snow"]), ("barkdk", lc["outline"])], 0.75))
    rp, _ = canopy([(0, 0, 40, 0)], "red")
    cells.append(("Pine fan, red", "R 30–42, 13 needles", [("vermilion", rp["vermilion_body"]), ("gold", rp["needle"]), ("orange", rp["hub"]), ("snow", rp["snow"]), ("barkdk", rp["outline"])], 0.42))
    wp, _ = canopy([(0, 0, 40, 0)], "white")
    cells.append(("Pine fan, white", "R 26–40, gold inner 46%", [("snow", wp["snow_body"]), ("gold", wp["gold_inner"]), ("barkdk", wp["needle"]), ("orange", wp["hub"]), ("snow", wp["snow"]), ("shadow", wp["outline"])], 0.42))
    bc = bamboo_cluster(0, 0, 45, [40, 75, 110, 145], rng=random.Random(2))
    cells.append(("Bamboo cluster", "blade 30–52 long, width 24%", [("indigo", bc["indigo"]), ("lavender", bc["lavender"]), ("snow", bc["snow"]), ("barkdk", bc["outline"])], 0.38))
    cells.append(("Mist band", "rows 3.4 apart, triple run", [("shadow", mist(0, 0, 70, 3, 3.4, random.Random(4)))], 0.45))
    poly, Sm = sweep(taper([(0, 20), (25, 12), (50, 8), (70, 0)], 8, 2))
    sn = snow_ridge(Sm, 0, 0.9, random.Random(5), size=1.2, lift=0.8, min_r=2.0, gap_p=0.15)
    cells.append(("Snow on limb", "clumps, 2.0 min radius, grey shadow 1.3 down", [("bark", poly), ("barkdk", poly.boundary.buffer(0.35)), ("shadow", affinity.translate(sn, 0.5, 1.3).difference(sn)), ("snow", sn)], 0.48))
    for i, (lab, dims, geoms, sc) in enumerate(cells):
        cx = mx + (i % 5)*41.5; cy = my + (i // 5)*39
        o += motif_cell(cx, cy, lab, dims, geoms, sc)
    o.append(t(mx, my + 82, "Scale shown: blossoms 0.62–1.0, bud 2.4, leaf 0.75, pine 0.42, bamboo 0.38, mist 0.45, snow 0.48. Dimensions are real mm.", 1.8, 400, MUTED))
    # rules
    rx = 228
    o.append(t(rx, 34, "E · SHARED RULES", 2.6, 700))
    rules = ["Line art (outlines, texture, needles, mist,",
             "  veins) = triple run 0.7 wide, 60wt OK.",
             "Fills: min width 0.8, gaps ≥ 0.5, counters ≥ 0.6.",
             "Dots ≥ 1.1 (stamens 1.2, bud highlight 1.35).",
             "Twigs ≥ 1.5 wide at Option A, ≥ 1.2 at B.",
             "Knockout art: no colour sits under another —",
             "  stitch each region once, in layer order.",
             "Stitch order: mist → pines → bark → texture →",
             "  snow shadow → snow → leaves → blossoms →",
             "  buds → bamboo.",
             "Snow is the hero texture: padded underlay",
             "  (2 layers) on trunk snow, flat elsewhere.",
             "No 3D puff foam — irregular snow edges",
             "  won't cut cleanly.",
             "Backing: 2.5 oz cutaway. No topping",
             "  needed (canvas surface is firm).",
             "Hoop/frame: one hooping per element; never",
             "  split a motif across hoopings."]
    for i, r in enumerate(rules):
        o.append(t(rx, 39.5 + i*3.55, r, 1.95))
    return o

# =============================================================== PAGE 3 — mockup diff + QA + production
def page3():
    o = header("01 · BACK SCENE — what changed, stitch check, production notes", "", "p3 / 3")
    img, ih = embed("flat.png", (940, 250, 1660, 960), 58, 14, 34)
    o.append(t(14, 31, "F · MOCKUP REFERENCE", 2.6, 700)); o.append(img)
    o.append(f'<rect x="14" y="34" width="58" height="{f(ih)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
    o.append(t(76, 31, "WHAT CHANGED vs MOCKUP", 2.6, 700))
    ch = ["Width: mockup art is ~600 wide and wraps onto both sleeves.",
          "  Pulled inside the back panel: 476 wide, ≥ 42 clear of seams.",
          "Bottom: mockup runs into the knit rib. Now stops 10 above",
          "  the hem seam (rib can't be embroidered).",
          "Top-right twigs: crossed the right armhole seam. Pulled",
          "  back inside the panel; blossom cluster kept.",
          "Density: mockup snow + buds are ~2× denser. Simplified to",
          "  keep stitch count and stiffness sane on canvas.",
          "Snow: mockup reads as 3D foam. Specced as padded satin/",
          "  tatami — same lift, survives washing, clean edges.",
          "White-pine gold fade → two-tone split (gold inner 46%).",
          "Leaves kept in slate (as mockup) although winter plum is",
          "  leafless — flag if you want them removed (saves ~2k st).",
          "Reference art: motif language only; nothing traced."]
    for i, c in enumerate(ch):
        o.append(t(76, 36 + i*3.45, c, 1.95))
    # QA table
    qx, qy = 14, 100
    o.append(t(qx, qy, "G · STITCH CHECK AT REAL SIZE (per thread, measured on the art files)", 2.6, 700))
    hdr = ["Thread", "Type", "Area mm²", "A: thin runs", "A: taper tips", "B: thin runs", "B: taper tips", "Stitches A", "Stitches B"]
    cx = [qx, qx + 30, qx + 42, qx + 58, qx + 76, qx + 92, qx + 110, qx + 126, qx + 144]
    for x, h in zip(cx, hdr): o.append(t(x, qy + 5, h, 1.8, 700, MUTED))
    rowsA = {(r["col"], r["cls"]): r for r in QA["A"]["rows"]}
    rowsB = {(r["col"], r["cls"]): r for r in QA["B"]["rows"]}
    keys = [k for k in rowsA]
    for i, k in enumerate(keys):
        yy = qy + 9 + i*3.05
        a, b = rowsA[k], rowsB.get(k)
        o.append(swatch(qx, yy, k[0], 3.5, 2.3)); o.append(t(qx + 4.5, yy, PAL[k[0]][1], 1.7))
        o.append(t(cx[1], yy, k[1], 1.7, 400, MUTED)); o.append(t(cx[2], yy, f"{a['area']:,.0f}", 1.7))
        for j, (r, base) in enumerate(((a, 3), (b, 5))):
            if r is None: continue
            pct = r["long_pct"]; okc = GREEN if pct < 1.0 else (ORANGE if pct < 3.0 else RED)
            o.append(t(cx[base], yy, f"{pct:.1f}%", 1.7, 600, okc))
            o.append(t(cx[base+1], yy, f"{r['thin_pct'] - r['long_pct']:.1f}%", 1.7, 400, MUTED))
        o.append(t(cx[7], yy, f"{a['stitches']:,.0f}", 1.7)); o.append(t(cx[8], yy, f"{b['stitches']:,.0f}" if b else "", 1.7))
    yy = qy + 9 + len(keys)*3.05 + 1.5
    o.append(t(cx[6], yy, "TOTAL", 1.8, 700)); o.append(t(cx[7], yy, f"{tot_stitches('A'):,.0f}", 1.8, 700)); o.append(t(cx[8], yy, f"{tot_stitches('B'):,.0f}", 1.8, 700))
    o.append(t(qx, yy + 4, "Thin runs = share of area narrower than the minimum (fills/satin 0.8, lines 0.6) for more than 2.5 mm: green < 1 %, amber < 3 %.", 1.75, 400, MUTED))
    o.append(t(qx, yy + 7, "Taper tips = pointed ends of satin shapes (blade tips, petal-rim ends, snow-cap ends) — normal satin tapers, not a defect.", 1.75, 400, MUTED))
    sa, sb = QA["A"]["sil"], QA["B"]["sil"]
    o.append(t(qx, yy + 10, f"Whole design: {sa['gaps']} / {sb['gaps']} near-touch points (A / B) where motifs sit < 0.5 apart — they will stitch as touching, which reads correctly;", 1.75, 400, MUTED))
    o.append(t(qx, yy + 13, f"{sa['small_holes']} / {sb['small_holes']} enclosed fabric specks < 0.6 will close up. No lettering on this element, so nothing legibility-critical.", 1.75, 400, MUTED))
    # production
    px_ = 178
    o.append(t(px_, 100, "H · PRODUCTION", 2.6, 700))
    notes = [f"Option A {A['W']:.0f} × {A['H']:.0f}: needs a field ≥ 490 × 525",
             "  (jumbo/border frame). One hooping.",
             f"Option B {B['W']:.0f} × {B['H']:.0f}: fits the standard 400 × 450",
             "  jacket-back frame. Same art, same 14 threads.",
             f"Est. {tot_stitches('A')/1000:.0f}k (A) / {tot_stitches('B')/1000:.0f}k (B) stitches ±25%.",
             "  Quote both; A runs ~1.6× longer per head.",
             "Embroider the cut back panel flat, BEFORE the",
             "  yoke/side seams and rib are attached.",
             "Canvas is heavy: 75/11 sharp needle, 2.5 oz cutaway.",
             "If the jacket is garment-washed/dyed after",
             "  embroidery: polyester thread only + wash test",
             "  (enzyme/stone wash greys whites and golds).",
             "Lining covers the back of the embroidery: confirm",
             "  lining is cut after the embroidered panel is",
             "  pressed (embroidery shrinks the panel ~1–2%).",
             "Sew-out on production canvas before bulk."]
    for i, n in enumerate(notes):
        o.append(t(px_, 105 + i*3.5, n, 1.95))
    return o

def build():
    pages = [page1(), page2(), page3()]
    w = PdfWriter()
    for i, p in enumerate(pages, 1):
        svg = doc(p)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"p{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_back_p{i}.png", output_width=2400)
        w.append(PdfReader(f"p{i}.pdf"))
    w.write(f"{OUT}/HAKI_jacket_01_back-scene_SPEC.pdf")
    # production art
    for tag, D in (("A", A), ("B", B)):
        gd = (f'<rect x="0" y="0" width="{f(D["W"])}" height="{f(D["H"])}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
              f'<line x1="{f(D["W"]/2)}" y1="-10" x2="{f(D["W"]/2)}" y2="{f(D["H"]+10)}" stroke="#00A3FF" stroke-width="0.3" stroke-dasharray="4 2"/>')
        svg, order = export.production_svg(D["vis"], D["W"], D["H"])
        open(f"{OUT}/HAKI_jacket_01_back-scene_OPT-{tag}_ART.svg", "w").write(svg)
        svgg, _ = export.production_svg(D["vis"], D["W"], D["H"], gd)
        open(f"{OUT}/HAKI_jacket_01_back-scene_OPT-{tag}_ART+guides.svg", "w").write(svgg)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/HAKI_jacket_01_back-scene_OPT-{tag}_ART.png",
                         output_width=int(D["W"] * (12 if tag == "A" else 14)))
    print("thread order:", order)

if __name__ == "__main__":
    build()
