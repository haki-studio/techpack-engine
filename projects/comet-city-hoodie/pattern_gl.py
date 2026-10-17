"""Pattern outputs for the Grand Line jacket: Drum Island pattern (engine/pattern.py) with this jacket's welt position
(front.py), materials and embroidery placement. usage: python3 pattern_gl.py qa dxf pdf"""
import glcore
import sys
import pattern as PT
_draft = PT.draft
MAT = {"Corduroy — 14 wale, dark brown": "Corduroy — 14 wale, black", "Rib knit 1×1 — tan": "Rib knit 1×1 — black",
       "Rib knit 1×1 — dark brown": "Rib knit 1×1 — black", "Shell — 12 oz duck": "Shell — 12 oz duck, washed navy"}
_cache = {}
def draft(size):
    if size not in _cache:
        g, mt = _draft(size)
        for pc in g.values():
            pc.material = MAT.get(pc.material, pc.material)
            if pc.code in ("S01", "B01"): pc.note = "no embroidery"
            if pc.code in ("F01", "F02"): pc.note = "welt pocket marked; embroidery 01 front scene placement"
        _cache[size] = (g, mt)
    return _cache[size]
PT.draft = draft
PT.PROPOSED["Welt"] = "1.4 × 13 cm (Drum Island) at the mockup position: centre 20.5 cm from CF, 34.7 cm below the neck, 38°"
import pattern_out as PO
PO.STYLE = glcore.STYLE
PO.EMB_ON = {"F01": ["FL"], "F02": ["FR"]}
PO.EMB_NAME = {"FL": "01 front scene FL", "FR": "01 front scene FR"}
import json as _json, os as _os
_emb0 = PO.emb_marks
def emb_marks(size, pl=None):
    """art outline + box + centre, plus the needle start of every split file (DXF layer 13 points, layer 8 crosses)"""
    out = _emb0(size, pl)
    for P, code in (("FL", "F01"), ("FR", "F02")):
        rp = f"out/01_front-scene/{size}/result_{P}.json"
        if not _os.path.exists(rp): continue
        r = _json.load(open(rp))
        lst = [m for m in out.get(code, []) if not m[0].endswith(" centre")]
        lst.append((f"01 {P} full file start", [tuple(r["full"]["origin"])], "cross"))
        for nm, s in r.get("splits", {}).get("sections", {}).items():
            lst.append((f"01 {P} {nm} start", [tuple(s["origin"])], "cross"))
        sy = r.get("splits", {}).get("sy")
        if sy is not None:
            b = r["full"]["art_box"]; lst.append((f"01 {P} split line", [(b[0] - 5, sy), (b[2] + 5, sy)], "line"))
        out[code] = lst
    return out
PO.emb_marks = emb_marks

if __name__ == "__main__":
    import drum
    a = sys.argv[1:]
    if "qa" in a:
        rows = PO.qa_table()
        for sz, r in rows.items():
            dev = {k: round(r["meas"][k]/10 - drum.POM_CM[k][2][drum.SIZES.index(sz)], 2) for k in drum.POM_CM}
            bad = [k for k in drum.POM_CM if abs(dev[k]) > drum.POM_CM[k][3]]
            sh = [c for c in PO.shape_checks(sz) if not c[1]]
            wk = [nm for nm, x, y, tol in r["walks"] if tol is not None and abs(x - y) > tol]
            print(sz, "POM out of tol:", bad or "none", "| shape:", sh or "all pass", "| walks:", wk or "all pass", "| ease", round(r["ease"], 1))
    if "dxf" in a:
        for sz in PT.SIZES: PO.write_dxf([sz], f"{PO.OUTD}/{glcore.STYLE}_pattern_{sz}.dxf")
        PO.write_dxf(PT.SIZES, f"{PO.OUTD}/{glcore.STYLE}_pattern_ALL-SIZES.dxf"); print("dxf ok")
    if "pdf" in a:
        PO.plot_pdf("M", f"{PO.OUTD}/{glcore.STYLE}_pattern_M_1to1_PLOT.pdf"); print("pdf ok")
