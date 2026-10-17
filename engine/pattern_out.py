"""Pattern outputs: AAMA-style DXF (per size + all sizes), 1:1 plot PDF (one page per piece), pattern QA.
Variant: set VARIANT = "hooded" (and HOOD = {...overrides}) before calling, or `pattern_out.py qa dxf pdf --hooded`."""
import os, json, math, io
import numpy as np
import ezdxf, cairosvg
from pypdf import PdfWriter, PdfReader
from shapely.geometry import Point, LineString, Polygon
import pattern as PT, pattern_draw as PD, drum
try:
    import emb_place as EP            # project embroidery placement (none yet on a brand-new project -> no marks)
except ImportError:
    EP = None

STYLE = "HK-JK-DRUM-PP"; OUTD = "out/pattern"; os.makedirs(OUTD, exist_ok=True)
EMB_ON = {"B01": ["back"], "F01": ["02L", "03"], "F02": ["02R", "04"], "S01": ["sleeve"]}
EMB_NAME = {"back": "01 back scene", "sleeve": "01 sleeve wrap", "02R": "02R chest branch", "02L": "02L chest branch", "03": "03 chest pine", "04": "04 lower bamboo"}
VARIANT = "default"; HOOD = None      # pattern.draft variant + hood overrides used by every output below

def draft(size):
    return PT.draft(size) if VARIANT == "default" else PT.draft(size, VARIANT, HOOD)

def emb_marks(size, pl=None):
    """{piece_code: [(name, pts, kind)]} — art outline, art box and design centre (= DST origin / needle start)."""
    if pl is None and EP is None: return {}
    pl = pl or EP.place(size)[0]; out = {}
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
def add_block(doc, pc, size, emb=()):
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
             f"Category: {pc.category}", f"Style Name: {STYLE}", "Units: mm"]
    if pc.fuse: lines.append("Fuse: yes")
    for i, l in enumerate(lines):
        blk.add_text(l, dxfattribs={"layer": "15", "height": 6, "insert": (tx - 60, ty - i * 9)})
    return name, cut.bounds

def write_dxf(sizes, path, pieces=None):
    doc = ezdxf.new("R12"); msp = doc.modelspace()
    for ln in ("1", "4", "7", "8", "13", "14", "15"): doc.layers.add(ln)
    y0 = 0.0
    for size in sizes:
        g, mt = draft(size); em = emb_marks(size) if size else {}
        x0 = 0.0; rowh = 0.0
        for code in (pieces or PT.order(VARIANT)):
            pc = g[code]; name, b = add_block(doc, pc, size, em.get(code, ()))
            w, h = b[2] - b[0], b[3] - b[1]
            msp.add_blockref(name, (x0 - b[0], y0 + b[3]))      # y flipped: top of piece at y0
            x0 += w + 60; rowh = max(rowh, h)
        msp.add_text(f"{STYLE} size {size}", dxfattribs={"layer": "15", "height": 25, "insert": (0, y0 + 60)})
        y0 -= rowh + 200
    doc.saveas(path)

# ---------------------------------------------------------------- 1:1 plot PDF: one page per piece (cut quantity on the page)
def plot_pdf(size, path):
    g, mt = draft(size); em = emb_marks(size); w = PdfWriter()
    for code in PT.order(VARIANT):
        pc = g[code]; b = PT.cut_poly(pc).bounds; m = 25.0
        W = (b[2] - b[0]) + 2*m; H = (b[3] - b[1]) + 2*m + 40
        X = lambda x: x - b[0] + m; Y = lambda y: y - b[1] + m + 40
        o = [f'<rect width="{W:.1f}" height="{H:.1f}" fill="#FFFFFF"/>']
        o += PD.piece_svg(pc, X, Y, 1.0, label=True, size=size, emb=em.get(code, ()), lw=1.0, text_mm=7, emb_fill=False)
        o.append(f'<rect x="{m}" y="8" width="100" height="25" fill="none" stroke="#000" stroke-width="0.4"/>')
        o.append(f'<text x="{m + 2}" y="18" font-size="5" font-family="Helvetica">TEST: 100 mm</text>')
        o.append(f'<text x="{m + 2}" y="28" font-size="4" font-family="Helvetica">print at 100 % — no scaling</text>')
        o.append(f'<text x="{m + 110}" y="18" font-size="6" font-weight="700" font-family="Helvetica">{STYLE} · {pc.code} {pc.name.replace("&", "+")} · size {size} · cut {pc.qty}</text>')
        o.append(f'<text x="{m + 110}" y="28" font-size="4.5" font-family="Helvetica">{pc.material} · seam allowance included (dashed = sew line) · notches = slits · ⊕ = drill holes</text>')
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H:.1f}mm" viewBox="0 0 {W:.1f} {H:.1f}">' + "".join(o) + "</svg>"
        buf = io.BytesIO(); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=buf); buf.seek(0); w.append(PdfReader(buf))
    w.write(path)


# ---------------------------------------------------------------- QA: pattern measured vs chart + seam walks
COLLAR_POMS = ("M", "N")              # collar POMs: not on a hooded garment

def edge(pc, name): return next(e for e in pc.edges if e.name == name)

def measure(size):
    g, mt = draft(size); b = mt["block"]; hooded = mt.get("variant") == "hooded"
    S = g["S01"]; cap_e = S.edges[0]
    def sleeve_width(yy):
        u = LineString(S.sew()).intersection(LineString([(-1000, yy), (1000, yy)]))
        xs = [p.x for p in (u.geoms if hasattr(u, "geoms") else [u])]; return max(xs) - min(xs)
    R01, R02 = g["R01"], g["R02"]
    m = {"A": (mt["hem_b"] - (mt["hps_b"][1] + PT.FWD) + mt.get("hem_band", PT.HEM_RIB)),
         "B": 2 * mt["ua_f"][0], "C": 2 * mt["sp_b"][0], "D": R01.edges[0].length / 2,
         "E": math.hypot(b.chest2 - b.sh2, mt["ua_b"][1] - b.b_sp[1]),
         "F": sleeve_width(25.0) / 2, "G": mt["cap_h"] + mt["Lu"] + mt.get("cuff_band", PT.CUFF_RIB), "H": R02.edges[0].length / 2,
         "J": 2 * mt["hps_f"][0], "K": -(mt["hps_f"][1] - PT.FWD), "L": -(mt["hps_b"][1] + PT.FWD),
         "M": drum.m("M", size), "N": next(e.length for e in g["C02"].edges if e.name == "front R") if not hooded else None, "P": PT.FWD}
    walks = [("Shoulder: back vs front", next(e.length for e in g["B01"].edges if e.name == "shoulder R"), next(e.length for e in g["F01"].edges if e.name == "shoulder"), 1.5),
             ("Side seam: back vs front", next(e.length for e in g["B01"].edges if e.name == "side R"), next(e.length for e in g["F01"].edges if e.name == "side"), 1.5),
             ("Sleeve cap vs armhole (ease)", cap_e.length, mt["AH"], None),
             ("Underarm: front vs back", S.edges[1].length, S.edges[3].length, 1.0)]
    body_neck = 2 * (mt["neck_b"] + mt["neck_f"])
    if not hooded:
        walks += [("Collar neck vs body neckline", next(e.length for e in g["C02"].edges if e.name == "neck"), body_neck, 2.0),
                  ("Top vs under collar outer", next(e.length for e in g["C01"].edges if e.name == "outer"), next(e.length for e in g["C02"].edges if e.name == "outer"), None)]
    else:
        for k in COLLAR_POMS: m.pop(k)
        d = mt["hood"]; H1, H2, H3, H4, H5, H6 = (g[c] for c in ("H01", "H02", "H03", "H04", "H05", "H06"))
        side_neck = edge(H1, "neck")
        walks += [("Hood neck vs body neck (CF to CF)", 2 * side_neck.length + edge(H2, "neck end").length + 2 * d["cf_set"], body_neck, 1.0),
                  ("Hood shoulder notch vs body front neck", side_neck.notches[0], mt["neck_f"] - d["cf_set"], 0.5),
                  ("Hood centre panel vs side (centre seam)", edge(H2, "side R").length, edge(H1, "centre seam").length, 0.5),
                  ("Hood facing vs hood face edge", edge(H3, "face").length, edge(H1, "face").length, 0.5),
                  ("Hood facing centre vs facing side seam", edge(H4, "side R").length, edge(H3, "centre seam").length, 0.5),
                  ("Facing join: facing side vs sherpa side", edge(H3, "lining join").length, edge(H5, "facing join").length, 0.5),
                  ("Facing join: facing centre vs sherpa centre", edge(H4, "lining join").length, edge(H6, "face end").length, 0.5),
                  ("Sherpa centre vs sherpa side (centre seam)", edge(H6, "side R").length, edge(H5, "centre seam").length, 0.5),
                  ("Sherpa + facing neck vs body neck (CF to CF)", 2 * (edge(H5, "neck").length + edge(H3, "neck").length) + edge(H6, "neck end").length + 2 * d["cf_set"], body_neck, 1.0)]
        sp = H1.sew(); xs = [p[0] for p in sp]
        mt["hood_measured"] = {"height": -min(p[1] for p in sp), "width": max(xs) - min(xs),
                               "face_opening": 2 * edge(H1, "face").length + edge(H2, "face end").length}
    walks += [("Facing CF vs front CF", g["K01"].edges[0].length, g["F01"].edges[0].length, 1.0),
              ("Lining side vs shell side (front)", next(e.length for e in g["L01"].edges if e.name == "side"), next(e.length for e in g["F01"].edges if e.name == "side"), 1.0)]
    body_hem = 2 * g["F01"].edges[-1].length + g["B01"].edges[4].length
    if R01.category == "BAND":       # woven self-fabric band: no negative ease, band = the seam it joins
        walks += [("Hem band vs body hem (woven, 1:1)", R01.edges[0].length, body_hem, 1.0),
                  ("Cuff vs shell sleeve opening (woven, 1:1)", R02.edges[0].length, S.edges[2].length, 1.0)]
    else:
        walks += [("Hem rib vs body hem (ratio)", R01.edges[0].length, body_hem, None),
                  ("Cuff rib vs shell sleeve opening (ratio)", R02.edges[0].length, S.edges[2].length, None)]
    return m, walks, mt

def _angle(u, v):
    return math.degrees(math.acos(max(-1.0, min(1.0, (u[0]*v[0] + u[1]*v[1]) / (math.hypot(*u) * math.hypot(*v) or 1)))))

def sew_simple(pc):
    """the sew line is one simple closed ring (no self-intersection, no slivers at the closure)"""
    ring = pc.sew(); ring = ring if ring[0] == ring[-1] else ring + [ring[0]]
    return Polygon(ring).is_valid

def band_check(pc, opening):
    """(name, ok, detail) for a cuff/hem joining piece: knit rib is stretched onto the shell (0.75-0.85 of the opening,
    LESSONS C2); a woven self-fabric BAND can't stretch, so it must equal the opening (LESSONS C9)."""
    r = pc.edges[0].length / opening
    if pc.category == "BAND": return (f"{pc.code} woven {pc.name.lower()} / opening = 1.00", abs(r - 1) <= 0.005, f"{r:.3f}")
    return (f"{pc.code} {pc.name.lower()} / opening 0.75–0.85", 0.75 <= r <= 0.85, f"{r:.2f}")

def hood_checks(g):
    """hood shape rules (LESSONS C10-C11): convex neck (mate of the scooped body neck), square corners where the side
    panel meets the centre panel (so the neck and face lines run on across it), lining inside the shell."""
    out = []; H1 = g["H01"]; poly = H1.sew_poly()
    nk = edge(H1, "neck").pts; a, b = nk[0], nk[-1]; mid = ((a[0]+b[0])/2, (a[1]+b[1])/2)
    out.append(("H01 hood neck convex (chord inside piece)", poly.buffer(-0.01).contains(Point(mid)), f"sagitta {Point(nk[len(nk)//2]).distance(Point(mid)):.1f} mm"))
    bk, fc = edge(H1, "centre seam").pts, edge(H1, "face").pts
    for nm, u, v in (("neck / centre seam", (nk[-2][0]-nk[-1][0], nk[-2][1]-nk[-1][1]), (bk[1][0]-bk[0][0], bk[1][1]-bk[0][1])),
                     ("centre seam / face", (bk[-2][0]-bk[-1][0], bk[-2][1]-bk[-1][1]), (fc[1][0]-fc[0][0], fc[1][1]-fc[0][1]))):
        ang = _angle(u, v); out.append((f"H01 corner {nm} square (90 ± 3°)", abs(ang - 90) <= 3, f"{ang:.1f}°"))
    shell = poly.area; lin = g["H05"].sew_poly().area + g["H03"].sew_poly().area
    out.append(("H05+H03 sherpa + facing smaller than the shell side (turn-of-cloth)", 100 < shell - lin < 0.05 * shell, f"-{(shell - lin)/100:.1f} cm²"))
    return out

def shape_checks(size):
    """automated pattern sanity checks (LESSONS C1-C3, C9-C11). Returns [(name, ok, detail)]."""
    g, mt = draft(size); out = []
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
    for code in PT.order(mt.get("variant", "default")):
        pc = g[code]; c = PT.cut_poly(pc); sp = pc.sew_poly()
        if getattr(pc, "inset", 0): continue
        ok = c.buffer(0.5).contains(sp) and (c.area > sp.area or all(e.sa == 0 for e in pc.edges))
        out.append((f"{code} cut line encloses sew line", ok, f"+{(c.area - sp.area)/100:.0f} cm²"))
        out.append((f"{code} sew line does not cross itself", sew_simple(pc) and c.is_valid, ""))
    S = g["S01"]
    out.append(band_check(g["R02"], S.edges[2].length))
    if g["R01"].category == "BAND": out.append(band_check(g["R01"], 2 * g["F01"].edges[-1].length + g["B01"].edges[4].length))
    if "H01" in g: out += hood_checks(g)
    return out

def qa_table():
    rows = {}
    for sz in PT.SIZES:
        m, walks, mt = measure(sz); rows[sz] = dict(meas=m, walks=walks, cap_h=mt["cap_h"], ease=mt["cap"] - mt["AH"], hood=mt.get("hood_measured"))
    return rows

if __name__ == "__main__":
    import sys
    if "--hooded" in sys.argv: VARIANT = "hooded"
    if "qa" in sys.argv or len(sys.argv) == 1 or sys.argv[1:] == ["--hooded"]:
        rows = qa_table(); bad = 0
        for sz, r in rows.items():
            dev = {k: round(r["meas"][k]/10 - drum.POM_CM[k][2][drum.SIZES.index(sz)], 2) for k in drum.POM_CM if k in r["meas"]}
            out = [k for k in dev if abs(dev[k]) > drum.POM_CM[k][3]]
            print(sz, "dev cm", {k: v for k, v in dev.items() if abs(v) > 0.05}, "cap h", round(r["cap_h"]), "ease", round(r["ease"], 1),
                  "OUT OF TOL " + str(out) if out else "")
            if r["hood"]: print("    hood (cm):", {k: round(v / 10, 1) for k, v in r["hood"].items()})
            bad_sc = [c for c in shape_checks(sz) if not c[1]]
            print("    shape checks:", "all pass" if not bad_sc else bad_sc)
            bad += len(out) + len(bad_sc)
            for nm, a, b, tol in r["walks"]:
                flag = "" if tol is None or abs(a - b) <= tol else "  <-- CHECK"
                bad += bool(flag)
                print("   ", nm, round(a, 1), round(b, 1), flag)
        print("PATTERN QA", VARIANT, "all pass" if not bad else f"{bad} failures")
    if "dxf" in sys.argv:
        for sz in PT.SIZES: write_dxf([sz], f"{OUTD}/{STYLE}_pattern_{sz}.dxf")
        write_dxf(PT.SIZES, f"{OUTD}/{STYLE}_pattern_ALL-SIZES.dxf"); print("dxf ok")
    if "pdf" in sys.argv:
        plot_pdf("M", f"{OUTD}/{STYLE}_pattern_M_1to1_PLOT.pdf"); print("pdf ok")
