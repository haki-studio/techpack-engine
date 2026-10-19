"""Pattern outputs for the wave jacket: Drum Island pattern (engine/pattern.py) with this jacket's welt position
(front.py), materials and embroidery placement. usage: python3 pattern_wave.py qa dxf pdf"""
import wavecore as WC
import sys
import pattern as PT
_draft = PT.draft
MAT = {"Corduroy — 14 wale, dark brown": "Corduroy — 14 wale, navy [proposed]", "Rib knit 1×1 — tan": "Rib knit 1×1 — navy [proposed]",
       "Rib knit 1×1 — dark brown": "Rib knit 1×1 — navy [proposed]", "Shell — 12 oz duck": "Shell — 12 oz duck, washed navy [proposed]"}
NOTE = {"B01": "embroidery 01 wave BK sewn on the cut piece", "F01": "welt pocket marked; embroidery 01 wave FL",
        "F02": "welt pocket marked; embroidery 01 wave FR", "S01": "embroidery 01 wave SR (front + back of the sleeve)",
        "S02": "embroidery 01 wave SL (front + back of the sleeve)"}
_cache = {}
def draft(size):
    if size not in _cache:
        g, mt = _draft(size)
        for pc in g.values():
            pc.material = MAT.get(pc.material, pc.material)
            if pc.code in NOTE: pc.note = NOTE[pc.code]
        if "S02" in g: g["S02"].note = NOTE["S02"]
        _cache[size] = (g, mt)
    return _cache[size]
PT.draft = draft
PT.PROPOSED["Welt"] = "1.4 × 13 cm, Drum Island block position: centre 17.0 cm from CF, 36.8 cm below the CF neck, 43° (render: ~5 cm further out)"
import pattern_out as PO
PO.STYLE = WC.STYLE
PO.EMB_ON = {"B01": ["BK"], "F01": ["FL"], "F02": ["FR"], "S01": ["SR"], "S02": ["SL"]}
PO.EMB_NAME = {P: f"01 wave {P}" for P in WC.PIECES}
import json as _json, os as _os
_emb0 = PO.emb_marks
def emb_marks(size, pl=None):
    """art outline + box, plus the needle start of every file and split section (DXF layer 13 points, layer 8 crosses)"""
    out = _emb0(size, pl)
    for P in WC.PIECES:
        code = WC.PIECE_CODE[P]; rp = f"out/01_wave/{size}/result_{P}.json"
        if not _os.path.exists(rp): continue
        r = _json.load(open(rp))
        lst = [m for m in out.get(code, []) if not m[0].endswith(" centre")]
        lst.append((f"01 {P} full file start", [tuple(r["full"]["origin"])], "cross"))
        for nm, s in r.get("splits", {}).get("sections", {}).items():
            lst.append((f"01 {P} {nm} start", [tuple(s["origin"])], "cross"))
        sp = r.get("splits", {})
        b = r["full"]["art_box"]
        for yv in sp.get("ys") or ([sp["sy"]] if sp.get("sy") is not None else []): lst.append((f"01 {P} split line", [(b[0] - 5, yv), (b[2] + 5, yv)], "line"))
        for xv in sp.get("xs") or ([sp["sx"]] if sp.get("sx") is not None else []): lst.append((f"01 {P} split line", [(xv, b[1] - 5), (xv, b[3] + 5)], "line"))
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
        for sz in PT.SIZES: PO.write_dxf([sz], f"{PO.OUTD}/{WC.STYLE}_pattern_{sz}.dxf")
        PO.write_dxf(PT.SIZES, f"{PO.OUTD}/{WC.STYLE}_pattern_ALL-SIZES.dxf"); print("dxf ok")
    if "pdf" in a:
        PO.plot_pdf("M", f"{PO.OUTD}/{WC.STYLE}_pattern_M_1to1_PLOT.pdf"); print("pdf ok")
