"""Embroidery pack (G1–G5 + element specs) -> garment pack T1–T16 + embroidery -> merged FULL tech pack."""
from pypdf import PdfReader
import moonpal
import pack, gtp
idx = pack.build()
base = len(gtp.PAGES) + 1
sub = [("   G1 Cover · G2 Placement · G3 Threads · G4 Stitch summary", base), ("   G5 Production stitch files + hoop splits", base + 4)]
for name, pg in idx[5:]: sub.append(("   " + name, base + pg - 1))
OUT = "out/HAKI_Drum-Island_moon_FULL-TECHPACK_RevC.pdf"
n = gtp.build(pack.OUT_PDF, sub, OUT)
print("garment pages", n, "total", len(PdfReader(OUT).pages), OUT)
