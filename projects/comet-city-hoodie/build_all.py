"""Embroidery pack (G1-G6 + element specs + F1) + garment pages (T1-T9) -> one merged tech pack PDF."""
import cccore
from pypdf import PdfReader
import pack, gtp
pack.build()
base = len(gtp.PAGES) + 1
n01 = len(PdfReader(pack.SPEC["01"]).pages); n02 = len(PdfReader(pack.SPEC["02"]).pages)
sub = [("   G1 Cover · G2 Placement · G3 Threads · G4 Stitch summary", base), ("   G5 Production stitch files + hoop splits", base + 4),
       ("   G6 Hooping table", base + 5), ("   01 Front scene (element spec)", base + 6), ("   02 Sleeves (element spec)", base + 6 + n01),
       ("   F1 Factory requests", base + 6 + n01 + n02)]
OUT = f"out/HAKI_{cccore.SHORT}_FULL-TECHPACK_{cccore.REV_GAR.replace(' ', '')}.pdf"
n = gtp.build(pack.OUT_PDF, sub, OUT)
print("garment pages", n, "total", len(PdfReader(OUT).pages), OUT)
