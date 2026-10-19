"""Pattern outputs for the Comet City hoodie: block `zip-hoodie` (engine/hoodie.py = Drum Island body + 3-panel sherpa hood +
self-fabric bands) with this jacket's welt position (front.py) and the embroidery placement of the four pieces.
usage: python3 pattern_cc.py qa dxf pdf"""
import cccore
import sys, os, json
import front as F                     # front.WELT = this mockup's welt (engine per-design welt override)
import hoodie as HD, pattern as PT, pattern_out as PO
BLK = HD.Variant(welt=F.WELT)
STYLE = cccore.STYLE
OUTD = "out/pattern"; os.makedirs(OUTD, exist_ok=True)
PO.EMB_ON = {"F01": ["FL"], "F02": ["FR"], "S01": ["SR"], "S02": ["SL"]}
PO.EMB_NAME = {"FL": "01 front scene FL", "FR": "01 front scene FR", "SR": "02 sleeve SR", "SL": "02 sleeve SL"}
_emb0 = PO.emb_marks
def emb_marks(size, pl=None):
    """art outline + box, plus the needle start of every file (full + split sections) and the split line"""
    out = _emb0(size, pl)
    for P, code in cccore.PIECE_CODE.items():
        rp = f"{cccore.edir(P)}/{size}/result_{P}.json"
        if not os.path.exists(rp): continue
        r = json.load(open(rp))
        lst = [m for m in out.get(code, []) if not m[0].endswith(" centre")]
        lst.append((f"{cccore.ELEM_OF[P]} {P} full file start", [tuple(r["full"]["origin"])], "cross"))
        for nm, s in r.get("splits", {}).get("sections", {}).items():
            lst.append((f"{cccore.ELEM_OF[P]} {P} {nm} start", [tuple(s["origin"])], "cross"))
        sy = r.get("splits", {}).get("sy")
        if sy is not None:
            b = r["full"]["art_box"]; lst.append((f"{cccore.ELEM_OF[P]} {P} split line", [(b[0] - 5, sy), (b[2] + 5, sy)], "line"))
        out[code] = lst
    return out
PO.emb_marks = emb_marks
PROPOSED = dict(HD.PROPOSED)
PROPOSED["Welt"] = "1.4 × 13 cm (Drum Island) at the mockup position: centre 21.8 cm from CF, 35.2 cm below the neck, 54°"

def qa():
    ok = True; rows = {}
    CH = HD.chart()
    for sz in HD.SIZES:
        meas, walks = HD.measure(sz)[:2]
        bad = [k for k in CH if abs(meas[k] / 10 - CH[k][2][HD.SIZES.index(sz)]) > CH[k][3]]
        wk = [nm for nm, a, b, tol in walks if tol is not None and abs(a - b) > tol]
        sh = [c[0] for c in HD.shape_checks(sz) if not c[1]]
        rows[sz] = dict(pom_out=bad, walks_out=wk, shape_fail=sh)
        ok &= not (bad or wk or sh)
        print(sz, "POM out of tol:", bad or "none", "| walks:", wk or "all pass", "| shape:", sh or "all pass")
    json.dump(rows, open("pattern_qa.json", "w"), indent=1)
    return ok

if __name__ == "__main__":
    a = sys.argv[1:]
    if "qa" in a: print("PATTERN QA", "ALL PASS" if qa() else "FAIL")
    if "dxf" in a:
        for sz in HD.SIZES: PO.write_dxf([sz], f"{OUTD}/{STYLE}_pattern_{sz}.dxf", blk=BLK, style=STYLE, emb=True)
        PO.write_dxf(HD.SIZES, f"{OUTD}/{STYLE}_pattern_ALL-SIZES.dxf", blk=BLK, style=STYLE, emb=True); print("dxf ok")
    if "pdf" in a:
        PO.plot_pdf("M", f"{OUTD}/{STYLE}_pattern_M_1to1_PLOT.pdf", blk=BLK, style=STYLE, emb=True); print("pdf ok")
