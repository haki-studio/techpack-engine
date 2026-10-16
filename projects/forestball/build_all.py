"""Embroidery pack (G1-G5 + element specs) -> full garment tech pack (T1-T16 first)."""
import glob, json
import fbcore
from pypdf import PdfReader
import pack, gtp
pack.build()
base = len(gtp.PAGES) + 1
sub = [("   G1 Cover · G2 Placement · G3 Threads · G4 Stitch summary", base), ("   G5 Stitch files + splits · G6 Hooping plan", base + 4),
       ("   F1 Factory requests", base + 6)]
pg = base + 7
for name, pat in [("01 Back scene (licensed placeholder)", "out/01_back-scene/*SPEC_*.pdf"), ("02 Chest mossy branch", "out/02_*/*SPEC_*.pdf")]:
    sub.append((f"   {name}", pg)); pg += len(PdfReader(glob.glob(pat)[0]).pages)
OUT = f"out/HAKI_FB_Forestball_FULL-TECHPACK_{fbcore.REV_GAR.replace(' ', '')}.pdf"
n = gtp.build(pack.OUT_PDF, sub, OUT)
print("garment pages", n, "total", len(PdfReader(OUT).pages), OUT)
