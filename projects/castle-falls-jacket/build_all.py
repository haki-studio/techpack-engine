"""Embroidery pack (G1-G6 + element specs + F1) + garment pack (T1-T16) -> one merged tech pack PDF."""
import cfcore
from pypdf import PdfReader
import pack, gtp
idx = pack.build()
base = len(gtp.PAGES)
sub = [("   " + n, base + p) for n, p in idx]
OUT = f"out/HAKI_{cfcore.SHORT}_FULL-TECHPACK_{cfcore.REV_GAR.replace(' ', '')}.pdf"
n = gtp.build(pack.OUT_PDF, sub, OUT)
print("garment pages", n, "total", len(PdfReader(OUT).pages), OUT)
