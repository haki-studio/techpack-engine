"""Documents in LESSONS D3 order: results (DST read-back) -> placement check -> compare sheets -> garment pages + pattern
(T1-T8, DXF, 1:1 plot) -> element specs -> embroidery pack (G1-G6, specs, F1) -> ONE merged tech pack -> shrink -> package.
usage: python3 build_all.py"""
import rbcore
import subprocess, sys, os
from pypdf import PdfWriter, PdfReader
def run(*a): print(">", *a, flush=True); subprocess.run([sys.executable, *a], check=True)
run("make_current.py"); run("emb_place.py"); run("qa_gates.py"); run("compare.py"); run("garment.py"); run("run_spec.py"); run("pack.py")
R = rbcore.REV_EMB.replace(' ', '')
emb = f"out/HAKI_{rbcore.SHORT}_EMBROIDERY-PACK_{R}.pdf"; gar = f"out/HAKI_{rbcore.SHORT}_GARMENT-PAGES_{rbcore.REV_GAR.replace(' ', '')}.pdf"
src = f"out/HAKI_{rbcore.SHORT}_TECHPACK_{R}.pdf"
w = PdfWriter(); w.append(PdfReader(gar)); w.append(PdfReader(emb)); w.write(src)
print("merged pages", len(PdfReader(src).pages))
run("shrink.py", src, src.replace(".pdf", "_small.pdf"), "3000", "82")
print("MB", round(os.path.getsize(src)/1e6, 1), "->", round(os.path.getsize(src.replace(".pdf", "_small.pdf"))/1e6, 1))
run("finish.py")
