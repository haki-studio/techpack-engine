"""Pattern outputs for Forestball: engine pattern_out with this style's name + embroidery marks (incl. the LICENSED placeholder box).
usage: ./py.sh pattern_fb.py qa dxf pdf"""
import sys
import fbcore
import pattern_out as _PO
from pattern_out import *            # measure, shape_checks, qa_table, write_dxf, plot_pdf ...
import emb_place as EP

_PO.STYLE = STYLE = fbcore.STYLE
_PO.EMB_ON = EMB_ON = {"B01": ["back"], "F01": ["02L"], "F02": ["02R"]}
_PO.EMB_NAME = EMB_NAME = {"back": "01 back scene", "02R": "02R chest branch", "02L": "02L chest branch"}
_orig = _PO.emb_marks

def emb_marks(size, pl=None):
    pl = pl or EP.place(size)[0]
    out = _orig(size, pl)
    b = pl["_ph"].bounds
    out["B01"].append(("LICENSED FIGURE placeholder (licensor art)", [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])], "box"))
    out["B01"].append(("LICENSED FIGURE placeholder centre", [((b[0]+b[2])/2, (b[1]+b[3])/2)], "cross"))
    return out
_PO.emb_marks = emb_marks

if __name__ == "__main__":
    import drum, pattern as PT
    if "qa" in sys.argv:
        rows = qa_table(); bad = 0
        for sz, r in rows.items():
            dev = {k: round(r["meas"][k]/10 - drum.POM_CM[k][2][drum.SIZES.index(sz)], 2) for k in drum.POM_CM}
            out = {k: v for k, v in dev.items() if abs(v) > drum.POM_CM[k][3]}
            sc = [c for c in shape_checks(sz) if not c[1]]
            wb = [w[0] for w in r["walks"] if w[3] is not None and abs(w[1] - w[2]) > w[3]]
            bad += len(out) + len(sc) + len(wb)
            print(sz, "out of tol", out or "none", "shape", sc or "pass", "walks", wb or "pass", "ease", round(r["ease"], 1))
        print("PATTERN QA", "all pass" if not bad else f"{bad} failures")
    if "dxf" in sys.argv:
        for sz in PT.SIZES: write_dxf([sz], f"{OUTD}/{STYLE}_pattern_{sz}.dxf")
        write_dxf(PT.SIZES, f"{OUTD}/{STYLE}_pattern_ALL-SIZES.dxf"); print("dxf ok")
    if "pdf" in sys.argv:
        plot_pdf("M", f"{OUTD}/{STYLE}_pattern_M_1to1_PLOT.pdf"); print("pdf ok")
