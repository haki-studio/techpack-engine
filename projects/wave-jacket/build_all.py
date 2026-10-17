"""Element spec + embroidery pack (G1-G6, F1) + garment pack (T1-T16) -> one merged tech pack PDF."""
import wavecore as WC
from pypdf import PdfReader
import espec
espec.build()
import pack, gtp
pack.build()
base = len(gtp.PAGES) + 1
sub = [("   G1 Cover · G2 Placement · G3 Threads · G4 Stitch summary", base), ("   G5 Production stitch files + hoop splits", base + 4),
       ("   G6 Hooping table", base + 5), ("   01 Wave (element spec, 6 pp)", base + 6), ("   F1 Factory requests", base + 12)]
OUT = f"out/HAKI_WAVE_FULL-TECHPACK_{WC.REV_GAR.replace(' ', '')}.pdf"
n = gtp.build(pack.OUT_PDF, sub, OUT)
print("garment pages", n, "total", len(PdfReader(OUT).pages), OUT)
