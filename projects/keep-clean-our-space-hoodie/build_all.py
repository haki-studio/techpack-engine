"""Documents: refresh numbers from the DST files -> embroidery pack (G/E/S/R/F pages) -> (garment pages T* once the
hooded pattern lands) -> merged PDF -> shrink. usage: python3 build_all.py"""
import kccore
import subprocess, sys, os, glob
from pypdf import PdfReader, PdfWriter
subprocess.run([sys.executable, "make_current.py"], check=True)
subprocess.run([sys.executable, "compare.py", "M"], check=True)
import pack
pack.build()
parts = [pack.OUT_PDF]
gar = glob.glob("out/HAKI_KCOS_GARMENT_*.pdf")
if gar: parts = gar + parts
w = PdfWriter()
for p in parts: w.append(PdfReader(p))
full = f"out/HAKI_{kccore.SHORT}_FULL-TECHPACK_{kccore.REV_EMB.replace(' ', '')}.pdf"
w.write(full + ".tmp.pdf")
subprocess.run([sys.executable, "shrink.py", full + ".tmp.pdf", full, "3000", "82"], check=True); os.remove(full + ".tmp.pdf")
print("pages", len(PdfReader(full).pages), full, round(os.path.getsize(full) / 1e6, 1), "MB")
