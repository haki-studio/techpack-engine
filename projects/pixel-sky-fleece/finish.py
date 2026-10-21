"""Package: recompressed pack PDF + zip (elements/, jacquard/, pattern/, compare/, README). usage: python3 finish.py"""
import os, shutil, subprocess, json, glob
from pypdf import PdfReader, PdfWriter

STYLE = "HK-FL-PIXSKY"; REV = "RevC"; OUT = "out"
src = f"{OUT}/HAKI_{STYLE}_TECHPACK_{REV}.pdf"; dst = f"{OUT}/HAKI_{STYLE}_TECHPACK_{REV}_small.pdf"
w = PdfWriter(clone_from=src)
for page in w.pages:
    for img in page.images:
        im = img.image
        if max(im.size) > 3000: im.thumbnail((3000, 3000))
        img.replace(im.convert("RGB"), quality=82)
w.compress_identical_objects(remove_identicals=True, remove_orphans=True); w.write(dst)
pkg = f"{OUT}/pkg"; shutil.rmtree(pkg, ignore_errors=True)
for d in ("elements", "jacquard", "pattern", "compare", "art"): os.makedirs(f"{pkg}/{d}")
shutil.copy(dst, f"{pkg}/HAKI_{STYLE}_TECHPACK_{REV}.pdf")
for F in ("E1", "E2", "E3", "E1B"):
    for ext in ("dst", "pes"): shutil.copy(f"{OUT}/stitch/{F}/HAKI_{STYLE}_{F}.{ext}" if False else f"{OUT}/stitch/{F}/{STYLE}_{F}.{ext}", f"{pkg}/elements/")
    shutil.copy(f"{OUT}/art/{STYLE}_{F}_ART.svg", f"{pkg}/art/")
    shutil.copy(f"{OUT}/compare_{F}.png", f"{pkg}/compare/")
shutil.copy(f"{OUT}/compare_jacquard.png", f"{pkg}/compare/")
for p in glob.glob(f"{OUT}/jacquard/{STYLE}_JQ_*"): shutil.copy(p, f"{pkg}/jacquard/")
shutil.copy(f"{OUT}/jacquard/jacquard_stats.json", f"{pkg}/jacquard/")
for p in glob.glob(f"{OUT}/pattern/{STYLE}_*"): shutil.copy(p, f"{pkg}/pattern/")
shutil.copy(f"{OUT}/art/placements.json", f"{pkg}/elements/")
G = json.load(open(f"{OUT}/stitch/gates_fl.json"))
lines = "\n".join(f"elements/{STYLE}_{F}.dst/.pes   {r['piece']}  {r['stitches']:,} stitches, {r['trims']} trims, {r['stops']} stops, {r['threads']} threads, {r['size_mm'][0]} x {r['size_mm'][1]} mm"
                  for F, r in G.items())
open(f"{pkg}/README.txt", "w").write(f"""HAKI STUDIOS - Pixel Sky sherpa fleece jacket ({STYLE}) - Rev C - 21 Oct 2026

HAKI_{STYLE}_TECHPACK_{REV}.pdf   T1-T5 garment, J1-J3 jacquard, G1-G5 embroidery, F1-F2 factory + mill requests, Q1 questions, R1 checks

EMBROIDERY (size M = every size, art 100 %; placement on G1 + pattern layer 8)
{lines}
  option A (bird knitted):  E1 + E2 + E3      option B (bird embroidered): E1B + E2 + E3
  art/*.svg = the traced art, true size mm, one layer per thread in stitch order

JACQUARD (engineered sherpa, 1 px = 1 cell = 2.5 mm finished [proposed]; palette 0 sky, 1 cream, 2 black, 9 outside)
  jacquard/{STYLE}_JQ_<panel>_<size>.png + .bmp    panels: front_L (F01), front_R (F02: _birdA / _birdB), back (B01), sleeve_R (S01), sleeve_L (S02)

PATTERN  pattern/{STYLE}_pattern_<size>.dxf (AAMA layers, mm), _ALL-SIZES.dxf, _M_1to1_PLOT.pdf (check the 100 mm box)
COMPARE  compare/*.png  mockup vs stitch preview / cell map, same scale

Amber = proposed by Haki tech design - confirm. Fit sample in M before the size set (first fleece).
""")
z = f"{OUT}/HAKI_{STYLE}_{REV}_files.zip"
if os.path.exists(z): os.remove(z)
subprocess.run(f"cd {pkg} && zip -qr ../{os.path.basename(z)} .", shell=True, check=True)
print(dst, round(os.path.getsize(dst) / 1e6, 1), "MB;", z, round(os.path.getsize(z) / 1e6, 1), "MB")
