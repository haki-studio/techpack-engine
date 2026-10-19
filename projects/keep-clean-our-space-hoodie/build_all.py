"""Documents: numbers from the DST files -> compare sheets (DST read-back) -> pattern (QA, DXF, 1:1 plot) -> DST welt check ->
embroidery pack (G/E/S/R/F) -> garment pages T1-T9 -> merged PDF -> shrink. usage: python3 build_all.py"""
import kccore
import subprocess, sys, os
from pypdf import PdfReader
for cmd in (["make_current.py"], ["compare.py", "M"], ["pattern_kc.py", "qa", "dxf", "pdf"], ["welt_check.py"]):
    subprocess.run([sys.executable] + cmd, check=True)
import pack, kcgtp
pack.build()
base = len(kcgtp.PAGES) + 1
names = ["G1 Cover + contents", "G2 Placement overview", "G3 Thread + trim summary", "G4 Stitch summary + open questions", "G5 Production stitch files + hoop splits",
         "G6 Hooping table", "E01 JP badge", "E02 EN badge", "E03 CN badge", "E04 KR oval", "E05 Star field", "S1 Stop sequence FR + FL", "S2 Stop sequence SR + SL",
         "R1 Region stitch table", "F1 Factory requests"]
sub = [("   " + n, base + i) for i, n in enumerate(names) if n.split()[0] in ("G2", "G3", "G4", "G5", "G6", "E01", "E05", "S1", "R1", "F1")]
full = f"out/HAKI_{kccore.SHORT}_FULL-TECHPACK_{kccore.REV_EMB.replace(' ', '')}.pdf"
n = kcgtp.build(pack.OUT_PDF, sub, full + ".tmp.pdf")
subprocess.run([sys.executable, "shrink.py", full + ".tmp.pdf", full, "3000", "82"], check=True); os.remove(full + ".tmp.pdf")
print("garment pages", n, "pages", len(PdfReader(full).pages), full, round(os.path.getsize(full) / 1e6, 1), "MB")
