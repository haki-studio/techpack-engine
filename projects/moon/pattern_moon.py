"""Pattern outputs for the moon jacket: engine pattern_out with the moon style code, embroidery elements per piece
and the licensed-figure placeholder box on B01 (DXF layer 8 + 1:1 plot). usage: ./py.sh pattern_moon.py qa dxf pdf"""
import sys
import moonpal, moonpattern
import pattern_out as PO, emb_place as EP, drum
PO.STYLE = moonpattern.STYLE
PO.EMB_ON = {"B01": ["back", "box"], "F01": ["02L", "03L"], "F02": ["02R", "03R"], "S01": ["04R"], "S02": ["04L"]}
PO.EMB_NAME = EP.NAME
if __name__ == "__main__":
    a = sys.argv[1:]
    if "qa" in a:
        bad = 0
        for sz, r in PO.qa_table().items():
            over = {k: round(r["meas"][k] / 10 - drum.POM_CM[k][2][drum.SIZES.index(sz)], 2) for k in drum.POM_CM
                    if abs(r["meas"][k] / 10 - drum.POM_CM[k][2][drum.SIZES.index(sz)]) > drum.POM_CM[k][3]}
            sc = [c for c in PO.shape_checks(sz) if not c[1]]
            wk = [w[0] for w in r["walks"] if w[3] is not None and abs(w[1] - w[2]) > w[3]]
            bad += len(over) + len(sc) + len(wk); print(sz, "POM out:", over, "shape:", sc, "walks:", wk, "ease", round(r["ease"], 1))
        print("PATTERN QA FAILS", bad)
    if "dxf" in a:
        for sz in drum.SIZES: PO.write_dxf([sz], f"{PO.OUTD}/{PO.STYLE}_pattern_{sz}.dxf")
        PO.write_dxf(drum.SIZES, f"{PO.OUTD}/{PO.STYLE}_pattern_ALL-SIZES.dxf"); print("dxf ok")
    if "pdf" in a:
        PO.plot_pdf("M", f"{PO.OUTD}/{PO.STYLE}_pattern_M_1to1_PLOT.pdf"); print("pdf ok")
