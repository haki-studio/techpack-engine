"""Package: recompress the merged PDF + element specs, collect stitch files, pattern, art, README -> zip."""
import os, shutil, glob, subprocess, json
OUT = "out/HAKI_Drum-Island_moon_FULL-TECHPACK_RevC.pdf"
def shrink(p):
    subprocess.run(["python3" if False else os.environ.get("PYBIN", "python"), "shrink.py", p, p + ".tmp", "3000", "82"], check=True); os.replace(p + ".tmp", p)
for p in [OUT] + glob.glob("out/0*/*SPEC_RevC.pdf"): shrink(p)
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
for e in ("01_back-scene", "02_chest-clouds", "03_lower-front", "04_sleeve-clouds"):
    shutil.copytree(f"out/{e}", f"{PKG}/elements/{e}", ignore=shutil.ignore_patterns("summary.json", "result.json"))
shutil.copytree("out/pattern", f"{PKG}/pattern"); shutil.copy(OUT, PKG)
open(f"{PKG}/README.txt", "w").write("""HAKI STUDIOS - Drum Island Jacket, MOON colourway (style HK-JK-DRUM-MOON)
Garment tech pack Rev C + embroidery Rev C - 19 Oct 2026

HAKI_Drum-Island_moon_FULL-TECHPACK_RevC.pdf
    T1-T16 garment pages (flats, details, size chart, grading, BOM, construction, labels, colourway, open questions,
    pattern T11-T13, inside view, operations, revision log), then embroidery G1-G5 + element specs 01-04.

LICENSED FIGURE: the figure on the pole is a licensed character (licence confirmed by client 2026-10-16). It is NOT
drawn in these files. Its area is a placeholder box: knocked out of our art, marked on the pattern (B01, DXF layer 8)
and basted (pink, water-soluble) as the last stop of every 01 back file. The factory digitizer adds the figure from
the licensor-approved artwork.

pattern/
    HK-JK-DRUM-MOON_pattern_<size>.dxf     AAMA-layer DXF per size (1 cut, 14 sew, 4 notches, 7 grain, 8 internal +
                                           embroidery placement + placeholder box, 13 drill / needle start, 15 text). mm.
    HK-JK-DRUM-MOON_pattern_ALL-SIZES.dxf  every size in one file
    HK-JK-DRUM-MOON_pattern_M_1to1_PLOT.pdf  size M, one page per piece at 1:1 (check the 100 mm test box)
    Same Drum Island first pattern as plum + pine: sew + fit a size-M sample before cutting the size set.

elements/01_back-scene/by-size/<size>/     01 back stitch file for that size (DST + PES, preview, thread chart) and
                                           splits/ (360 x 360 hoopings, stop 1 = basting crosses; 4 sections, 3XL 6)
elements/03_lower-front/by-size/<size>/    03L (pole + wires) + 03R (wires) for that size - wires meet the side seams
elements/02_chest-clouds/grade-<A|B|C>/    02R/02L per art grade: A = XS-S, B = M-XL, C = XXL-3XL
elements/04_sleeve-clouds/grade-<A|B|C>/   04R/04L per grade; the full-sleeve file + _S1/_S2 split files (2 hoopings per sleeve)
elements/*/*_SPEC_RevC.pdf, *_ART*.svg     element specs + region art with digitizing attributes (size M / grade B)

All stitch files: <= 12 thread colours per file incl. registration + placeholder (manufacturer limit), max stitch 7.5 mm, trims counted from the DST. They are
production-intent drafts: the factory digitizer opens them, checks density + pull on 12 oz duck, edits if needed,
and sews out before bulk. Thread colours, densities and every [proposed - confirm] item: see T10 + G4.
""")
for z in glob.glob("out/*.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_Drum-Island_moon_RevC_files.zip .", shell=True, check=True)
print("pdf MB", round(os.path.getsize(OUT) / 1e6, 1), "zip MB", round(os.path.getsize("out/HAKI_Drum-Island_moon_RevC_files.zip") / 1e6, 1))
