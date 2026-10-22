"""Pattern outputs: AAMA-style DXF (per size + all sizes), 1:1 plot PDF (one page per piece), pattern QA."""
import os, json, math, io
import numpy as np
import ezdxf, cairosvg
from pypdf import PdfWriter, PdfReader
from shapely.geometry import Point, LineString, Polygon
import pattern as PT, pattern_draw as PD, drum      # emb_place (project module) is imported only when placements are drawn

STYLE = "HK-JK-DRUM-PP"; OUTD = "out/pattern"; os.makedirs(OUTD, exist_ok=True)
EMB_ON = {"B01": ["back"], "F01": ["02L", "03"], "F02": ["02R", "04"], "S01": ["sleeve"]}
EMB_NAME = {"back": "01 back scene", "sleeve": "01 sleeve wrap", "02R": "02R chest branch", "02L": "02L chest branch", "03": "03 chest pine", "04": "04 lower bamboo"}

def emb_marks(size, pl=None):
    """{piece_code: [(name, pts, kind)]} — art outline, art box and design centre (= DST origin / needle start)."""
    if pl is None:
        import emb_place as EP
        pl = EP.place(size)[0]
    out = {}
    for pc, elems in EMB_ON.items():
        lst = []
        for e in elems:
            _, geom = pl[e]
            polys = [geom] if geom.geom_type == "Polygon" else [q for q in getattr(geom, "geoms", []) if q.geom_type == "Polygon"]
            for q in polys:
                if q.area > 4: lst.append((EMB_NAME[e], list(q.simplify(0.8).exterior.coords), "outline"))
            b = geom.bounds
            lst.append((EMB_NAME[e] + " art box", [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])], "box"))
            lst.append((EMB_NAME[e] + " centre", [((b[0]+b[2])/2, (b[1]+b[3])/2)], "cross"))
        out[pc] = lst
    return out

# ---------------------------------------------------------------- DXF (AAMA layer convention)
def add_block(doc, pc, size, emb=(), style=None):
    name = f"{pc.code}_{size}"; blk = doc.blocks.new(name=name)
    F = lambda pts: [(x, -y) for x, y in pts]
    cut = PT.cut_poly(pc)
    blk.add_polyline2d(F(list(cut.exterior.coords)), close=True, dxfattribs={"layer": "1"})
    if not getattr(pc, "inset", 0):
        blk.add_polyline2d(F(pc.sew()), close=True, dxfattribs={"layer": "14"})
        for a, b in pc.notch_marks():
            blk.add_line(F([a])[0], F([b])[0], dxfattribs={"layer": "4"})
        for nm, pts in pc.internal:
            blk.add_polyline2d(F(pts), dxfattribs={"layer": "8"})
        for x, y in pc.drills:
            blk.add_point((x, -y), dxfattribs={"layer": "13"})
    (g0, g1) = pc.grain
    blk.add_line(F([g0])[0], F([g1])[0], dxfattribs={"layer": "7"})
    for nm, pts, kind in emb:
        if kind == "cross":
            (x, y), = pts
            blk.add_line((x - 8, -y), (x + 8, -y), dxfattribs={"layer": "8"}); blk.add_line((x, -y - 8), (x, -y + 8), dxfattribs={"layer": "8"})
            blk.add_point((x, -y), dxfattribs={"layer": "13"})
        else:
            blk.add_polyline2d(F(pts), close=True, dxfattribs={"layer": "8"})
    c = cut.representative_point(); tx, ty = c.x, -c.y
    lines = [f"Piece Name: {pc.code} {pc.name}", f"Size: {size}", f"Quantity: {pc.qty}", f"Material: {pc.material}",
             f"Category: {pc.category}", f"Style Name: {style or STYLE}", "Units: mm"]
    if pc.fuse: lines.append("Fuse: yes")
    for i, l in enumerate(lines):
        blk.add_text(l, dxfattribs={"layer": "15", "height": 6, "insert": (tx - 60, ty - i * 9)})
    return name, cut.bounds

def write_dxf(sizes, path, pieces=None, blk=None, style=None, emb=True):
    """blk = block module with draft()/ORDER (default: the Drum Island jacket, pattern.py)."""
    blk = blk or PT
    doc = ezdxf.new("R12"); msp = doc.modelspace()
    for ln in ("1", "4", "7", "8", "13", "14", "15"): doc.layers.add(ln)
    y0 = 0.0
    for size in sizes:
        g, mt = blk.draft(size); em = emb_marks(size) if (size and emb) else {}
        x0 = 0.0; rowh = 0.0
        for code in (pieces or blk.ORDER):
            pc = g[code]; name, b = add_block(doc, pc, size, em.get(code, ()), style)
            w, h = b[2] - b[0], b[3] - b[1]
            msp.add_blockref(name, (x0 - b[0], y0 + b[3]))      # y flipped: top of piece at y0
            x0 += w + 60; rowh = max(rowh, h)
        msp.add_text(f"{style or STYLE} size {size}", dxfattribs={"layer": "15", "height": 25, "insert": (0, y0 + 60)})
        # 100 mm references on x AND y next to a "100 mm" label: pattern_diff refuses a DXF without both (scale / unit check)
        msp.add_line((0, y0 + 120), (100, y0 + 120), dxfattribs={"layer": "8"})
        msp.add_text("100 mm", dxfattribs={"layer": "15", "height": 6, "insert": (20, y0 + 124)})
        msp.add_line((-30, y0 + 20), (-30, y0 + 120), dxfattribs={"layer": "8"})
        msp.add_text("100 mm", dxfattribs={"layer": "15", "height": 6, "insert": (-27, y0 + 70)})
        y0 -= rowh + 200
    doc.saveas(path)

# ---------------------------------------------------------------- 1:1 plot PDF: one page per piece (cut quantity on the page)
def plot_pdf(size, path, blk=None, style=None, emb=True):
    blk = blk or PT; ST = style or STYLE
    g, mt = blk.draft(size); em = emb_marks(size) if emb else {}; w = PdfWriter()
    for code in blk.ORDER:
        pc = g[code]; b = PT.cut_poly(pc).bounds; m = 25.0
        W = (b[2] - b[0]) + 2*m + 14; H = max((b[3] - b[1]) + 2*m + 40, 150.0)    # room for the vertical 100 mm ruler
        X = lambda x: x - b[0] + m; Y = lambda y: y - b[1] + m + 40
        o = [f'<rect width="{W:.1f}" height="{H:.1f}" fill="#FFFFFF"/>']
        o += PD.piece_svg(pc, X, Y, 1.0, label=True, size=size, emb=em.get(code, ()), lw=1.0, text_mm=7, emb_fill=False)
        o.append(f'<rect x="{m}" y="8" width="100" height="25" fill="none" stroke="#000" stroke-width="0.4"/>')
        o.append(f'<text x="{m + 2}" y="18" font-size="5" font-family="Helvetica">TEST: 100 mm</text>')
        o.append(f'<text x="{m + 2}" y="28" font-size="4" font-family="Helvetica">print at 100 % — no scaling</text>')
        # vertical 100 mm ruler: with the 100 mm box it checks the scale on BOTH axes (pattern_diff, TD design §4)
        rx = W - 8
        o.append(f'<line x1="{rx}" y1="40" x2="{rx}" y2="140" stroke="#000" stroke-width="0.4"/>')
        for ty in (40, 140): o.append(f'<line x1="{rx - 3}" y1="{ty}" x2="{rx + 3}" y2="{ty}" stroke="#000" stroke-width="0.4"/>')
        o.append(f'<text x="{rx - 2}" y="92" font-size="3.5" font-family="Helvetica" text-anchor="end">100 mm</text>')
        o.append(f'<text x="{m + 110}" y="18" font-size="6" font-weight="700" font-family="Helvetica">{ST} · {pc.code} {pc.name.replace("&", "+")} · size {size} · cut {pc.qty}</text>')
        o.append(f'<text x="{m + 110}" y="28" font-size="4.5" font-family="Helvetica">{pc.material} · seam allowance included (dashed = sew line) · notches = slits · ⊕ = drill holes</text>')
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H:.1f}mm" viewBox="0 0 {W:.1f} {H:.1f}">' + "".join(o) + "</svg>"
        buf = io.BytesIO(); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=buf); buf.seek(0); w.append(PdfReader(buf))
    w.write(path)

# ---------------------------------------------------------------- QA: pattern measured vs chart + seam walks
def measure(size):
    g, mt = PT.draft(size); b = mt["block"]
    S = g["S01"]; cap_e = S.edges[0]
    def sleeve_width(yy):
        u = LineString(S.sew()).intersection(LineString([(-1000, yy), (1000, yy)]))
        xs = [p.x for p in (u.geoms if hasattr(u, "geoms") else [u])]; return max(xs) - min(xs)
    R01, R02 = g["R01"], g["R02"]
    m = {"A": (mt["hem_b"] - (mt["hps_b"][1] + PT.FWD) + PT.HEM_RIB),
         "B": 2 * mt["ua_f"][0], "C": 2 * mt["sp_b"][0], "D": R01.edges[0].length / 2,
         "E": math.hypot(b.chest2 - b.sh2, mt["ua_b"][1] - b.b_sp[1]),
         "F": sleeve_width(25.0) / 2, "G": mt["cap_h"] + mt["Lu"] + PT.CUFF_RIB, "H": R02.edges[0].length / 2,
         "J": 2 * mt["hps_f"][0], "K": -(mt["hps_f"][1] - PT.FWD), "L": -(mt["hps_b"][1] + PT.FWD),
         "M": drum.m("M", size), "N": next(e.length for e in g["C02"].edges if e.name == "front R"), "P": PT.FWD}
    walks = [("Shoulder: back vs front", next(e.length for e in g["B01"].edges if e.name == "shoulder R"), next(e.length for e in g["F01"].edges if e.name == "shoulder"), 1.5),
             ("Side seam: back vs front", next(e.length for e in g["B01"].edges if e.name == "side R"), next(e.length for e in g["F01"].edges if e.name == "side"), 1.5),
             ("Sleeve cap vs armhole (ease)", cap_e.length, mt["AH"], None),
             ("Underarm: front vs back", S.edges[1].length, S.edges[3].length, 1.0),
             ("Collar neck vs body neckline", next(e.length for e in g["C02"].edges if e.name == "neck"), 2 * (mt["neck_b"] + mt["neck_f"]), 2.0),
             ("Top vs under collar outer", next(e.length for e in g["C01"].edges if e.name == "outer"), next(e.length for e in g["C02"].edges if e.name == "outer"), None),
             ("Facing CF vs front CF", g["K01"].edges[0].length, g["F01"].edges[0].length, 1.0),
             ("Lining side vs shell side (front)", next(e.length for e in g["L01"].edges if e.name == "side"), next(e.length for e in g["F01"].edges if e.name == "side"), 1.0),
             ("Hem rib vs body hem (ratio)", R01.edges[0].length, 2 * g["F01"].edges[-1].length + g["B01"].edges[4].length, None),
             ("Cuff rib vs shell sleeve opening (ratio)", R02.edges[0].length, S.edges[2].length, None)]
    return m, walks, mt

def shape_checks(size):
    """automated pattern sanity checks (LESSONS C1-C3). Returns [(name, ok, detail)]."""
    g, mt = PT.draft(size); out = []
    def sag(pts, inside_poly):
        a, b = pts[0], pts[-1]; m = pts[len(pts)//2]
        mid = ((a[0]+b[0])/2, (a[1]+b[1])/2)
        # concave neck: the curve's middle lies INSIDE the body relative to its chord's midpoint
        return inside_poly.contains(Point(m)) is False and inside_poly.contains(Point(mid)) is False, math.hypot(m[0]-mid[0], m[1]-mid[1])
    for code, nm in (("F01", "neck"), ("B01", "neck")):
        pc = g[code]; e = next(x for x in pc.edges if x.name == nm)
        poly = pc.sew_poly(); a, b = e.pts[0], e.pts[-1]; m = e.pts[len(e.pts)//2]
        chord_mid = ((a[0]+b[0])/2, (a[1]+b[1])/2)
        # scooped: the chord midpoint lies OUTSIDE the piece (the neck cuts into the body)
        ok = not poly.buffer(-0.01).contains(Point(chord_mid)) if code == "F01" else True
        out.append((f"{code} neck scooped (chord outside piece)", ok, f"sagitta {math.hypot(m[0]-chord_mid[0], m[1]-chord_mid[1]):.1f} mm"))
    for code in PT.ORDER:
        pc = g[code]; c = PT.cut_poly(pc); sp = pc.sew_poly()
        if getattr(pc, "inset", 0): continue
        ok = c.buffer(0.5).contains(sp) and (c.area > sp.area or all(e.sa == 0 for e in pc.edges))
        out.append((f"{code} cut line encloses sew line", ok, f"+{(c.area - sp.area)/100:.0f} cm²"))
    rib = g["R02"].edges[0].length / g["S01"].edges[2].length
    out.append(("cuff rib / sleeve opening 0.75–0.85", 0.75 <= rib <= 0.85, f"{rib:.2f}"))
    return out

def qa_table():
    rows = {}
    for sz in PT.SIZES:
        m, walks, mt = measure(sz); rows[sz] = dict(meas=m, walks=walks, cap_h=mt["cap_h"], ease=mt["cap"] - mt["AH"])
    return rows

if __name__ == "__main__":
    import sys
    if "qa" in sys.argv or len(sys.argv) == 1:
        rows = qa_table()
        for sz, r in rows.items():
            dev = {k: round(r["meas"][k]/10 - drum.POM_CM[k][2][drum.SIZES.index(sz)], 2) for k in drum.POM_CM}
            print(sz, "dev cm", {k: v for k, v in dev.items() if abs(v) > 0.05}, "cap h", round(r["cap_h"]), "ease", round(r["ease"], 1))
            bad = [c for c in shape_checks(sz) if not c[1]]
            print("    shape checks:", "all pass" if not bad else bad)
            for nm, a, b, tol in r["walks"]:
                flag = "" if tol is None or abs(a - b) <= tol else "  <-- CHECK"
                print("   ", nm, round(a, 1), round(b, 1), flag)
    if "dxf" in sys.argv:
        for sz in PT.SIZES: write_dxf([sz], f"{OUTD}/{STYLE}_pattern_{sz}.dxf")
        write_dxf(PT.SIZES, f"{OUTD}/{STYLE}_pattern_ALL-SIZES.dxf"); print("dxf ok")
    if "pdf" in sys.argv:
        plot_pdf("M", f"{OUTD}/{STYLE}_pattern_M_1to1_PLOT.pdf"); print("pdf ok")
