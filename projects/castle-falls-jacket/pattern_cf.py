"""Pattern outputs for the Castle Falls jacket: Drum Island pattern (engine/pattern.py) with this jacket's welt position
(front.py), materials and embroidery placement. usage: python3 pattern_cf.py qa dxf pdf"""
import cfcore
import sys, os, json
import pattern as PT
_draft = PT.draft
MAT = {"Corduroy — 14 wale, dark brown": "Corduroy — 14 wale, washed navy", "Rib knit 1×1 — tan": "Rib knit 1×1 — navy",
       "Rib knit 1×1 — dark brown": "Rib knit 1×1 — navy", "Shell — 12 oz duck": "Shell — 12 oz duck, washed navy",
       "Lining — cotton flannel": "Lining — cotton flannel, navy/red plaid"}
NOTE = {"B01": "embroidery 01 back scene placement (cut 1, flat)", "F01": "welt pocket marked; embroidery 02 front scene FL placement",
        "F02": "welt pocket marked; embroidery 02 front scene FR placement", "S01": "embroidery 03 sleeve scene SR placement",
        "S02": "embroidery 03 sleeve scene SL placement"}
_cache = {}
def draft(size):
    if size not in _cache:
        g, mt = _draft(size)
        for pc in g.values():
            pc.material = MAT.get(pc.material, pc.material)
            if pc.code in NOTE: pc.note = NOTE[pc.code]
        _cache[size] = (g, mt)
    return _cache[size]
PT.draft = draft
PT.PROPOSED["Welt"] = "1.4 × 13 cm (Drum Island) at the mockup position: centre 23.0 cm from CF, 38.4 cm below the neck, 56°"
PT.PROPOSED.pop("Armhole", None)   # founder decision 2026-10-19: wrap seam accepted (no longer proposed; construction note on T2 / T7)
import pattern_out as PO
PO.STYLE = cfcore.STYLE
PO.EMB_ON = {"B01": ["BK"], "F01": ["FL"], "F02": ["FR"], "S01": ["SR"], "S02": ["SL"]}
PO.EMB_NAME = {"BK": "01 back scene", "FR": "02 front scene FR", "FL": "02 front scene FL", "SR": "03 sleeve SR", "SL": "03 sleeve SL"}
_emb0 = PO.emb_marks
def emb_marks(size, pl=None):
    """art outline + box + centre, plus the needle start of every split file (DXF layer 13 points, layer 8 crosses)"""
    out = _emb0(size, pl)
    for P in cfcore.PIECES:
        code = cfcore.PIECE_CODE[P]; e = cfcore.PIECE_ELEM[P]
        rp = f"out/{e}_{cfcore.ELEMS[e][0]}/{size}/result_{P}.json"
        if not os.path.exists(rp): continue
        r = json.load(open(rp))
        lst = [m for m in out.get(code, []) if not m[0].endswith(" centre")]
        lst.append((f"{e} {P} full file start", [tuple(r["full"]["origin"])], "cross"))
        for nm, s in r.get("splits", {}).get("sections", {}).items():
            lst.append((f"{e} {P} {nm} start", [tuple(s["origin"])], "cross"))
        b = r["full"]["art_box"]
        for sy in r.get("splits", {}).get("ys", []):
            lst.append((f"{e} {P} split line y", [(b[0] - 5, sy), (b[2] + 5, sy)], "line"))
        for sx in r.get("splits", {}).get("xs", []):
            lst.append((f"{e} {P} split line x", [(sx, b[1] - 5), (sx, b[3] + 5)], "line"))
        out[code] = lst
    return out
PO.emb_marks = emb_marks

if __name__ == "__main__":
    import drum
    a = sys.argv[1:]
    if "qa" in a:
        rows = PO.qa_table(); allok = True
        for sz, r in rows.items():
            dev = {k: round(r["meas"][k]/10 - drum.POM_CM[k][2][drum.SIZES.index(sz)], 2) for k in drum.POM_CM}
            bad = [k for k in drum.POM_CM if abs(dev[k]) > drum.POM_CM[k][3]]
            sh = [c for c in PO.shape_checks(sz) if not c[1]]
            wk = [nm for nm, x, y, tol in r["walks"] if tol is not None and abs(x - y) > tol]
            allok &= not (bad or sh or wk)
            print(sz, "POM out of tol:", bad or "none", "| shape:", sh or "all pass", "| walks:", wk or "all pass", "| ease", round(r["ease"], 1))
        print("PATTERN QA PASS" if allok else "PATTERN QA FAIL")
    if "dxf" in a:
        for sz in PT.SIZES: PO.write_dxf([sz], f"{PO.OUTD}/{cfcore.STYLE}_pattern_{sz}.dxf")
        PO.write_dxf(PT.SIZES, f"{PO.OUTD}/{cfcore.STYLE}_pattern_ALL-SIZES.dxf"); print("dxf ok")
    if "pdf" in a:
        PO.plot_pdf("M", f"{PO.OUTD}/{cfcore.STYLE}_pattern_M_1to1_PLOT.pdf"); print("pdf ok")
