"""Documents: numbers from the DST files -> A14/A15 gates (gates.json, shipped DSTs) -> compare sheets (DST read-back) -> pattern (QA, DXF, 1:1 plot) -> DST welt check ->
embroidery pack (G/E/S/R/F) -> garment pages T1-T9 -> merged PDF -> shrink. usage: python3 build_all.py"""
import kccore
import subprocess, sys, os
from pypdf import PdfReader
for cmd in (["make_current.py"], ["prod_gates.py"], ["glyph_gate.py"], ["frag_gate.py"], ["gates.py"], ["compare.py", "M"], ["pattern_kc.py", "qa", "dxf", "pdf"], ["welt_check.py"]):
    r = subprocess.run([sys.executable] + cmd)
    if r.returncode:
        sys.exit(f"STOP: {' '.join(cmd)} failed (exit {r.returncode}) - " + ("the A14/A15 gate has a FAIL row or a bare gap >= 25 mm2 (gates.json); "
                 "fix the art, rebuild the DSTs, then rerun. No pack is built on a failing gate." if cmd[0] == "gates.py" else "see the output above."))
import json
assert json.load(open("gates.json"))["blocking"] == 0, "gates.json BLOCKING > 0: no pack on a failing gate"
import pack, kcgtp
pack.build()
base = len(kcgtp.PAGES) + 1
names = ["G1 Cover + contents", "G2 Placement overview", "G3 Thread + trim summary", "G4 Stitch summary + open questions", "G5 Production stitch files + hoop splits",
         "G6 Hooping table", "E01 JP badge", "E02 EN badge", "E03 CN badge", "E04 KR oval", "E05 Star field", "E06 Back stars", "S1 Stop sequence FR + FL", "S2 Stop sequence SR + SL", "S3 Stop sequence BK",
         "R1 Region stitch table", "F1 Factory requests", "F2 Factory requests (cont.)"]
sub = [("   " + n, base + i) for i, n in enumerate(names) if n.split()[0] in ("G2", "G3", "G4", "G5", "G6", "E01", "E05", "E06", "S1", "R1", "F1", "F2")]
full = f"out/HAKI_{kccore.SHORT}_FULL-TECHPACK_{kccore.REV_EMB.replace(' ', '')}.pdf"
n = kcgtp.build(pack.OUT_PDF, sub, full + ".tmp.pdf")
subprocess.run([sys.executable, "shrink.py", full + ".tmp.pdf", full, "3000", "82"], check=True); os.remove(full + ".tmp.pdf")
print("garment pages", n, "pages", len(PdfReader(full).pages), full, round(os.path.getsize(full) / 1e6, 1), "MB")
