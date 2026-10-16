"""Embroidery pack (G1-G5 + element specs) -> full garment tech pack."""
import glob
from pypdf import PdfReader
import pack, gtp

pack.build()
base = len(gtp.PAGES) + 1          # first embroidery page in the merged PDF
sub = [("   G1 Cover · G2 Placement · G3 Threads · G4 Stitch summary", base), ("   G5 Production stitch files + hoop splits", base + 4)]
pg = base + 5
for name, pat in [("01 Back scene", "out/01_back-scene/*SPEC_RevE.pdf"), ("02 Chest plum branch", "out/02_*/*SPEC_RevB.pdf"),
                  ("03 Chest white pine", "out/03_*/*SPEC_RevB.pdf"), ("04 Lower-front bamboo", "out/04_*/*SPEC_RevB.pdf")]:
    sub.append((f"   {name}", pg)); pg += len(PdfReader(glob.glob(pat)[0]).pages)
OUT = "out/HAKI_Drum-Island_plum-pine_FULL-TECHPACK_RevA.pdf"
n = gtp.build(pack.OUT_PDF, sub, OUT)
print("garment pages", n, "total", len(PdfReader(OUT).pages), OUT)
