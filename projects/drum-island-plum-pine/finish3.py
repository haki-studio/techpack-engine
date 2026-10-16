"""Garment Rev C / embroidery Rev G packaging: drop superseded files, thread charts for v3, pattern folder, zip."""
import os, shutil, glob, subprocess, pickle
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFont

# ---- superseded: v1 drafts, v2 stitch files + splits, older specs
for pat in ["out/01_back-scene/*SPEC_RevD.pdf", "out/01_back-scene/*SPEC_RevE.pdf", "out/0[234]_*/*SPEC_RevA.pdf", "out/0[234]_*/*SPEC_RevB.pdf",
            "out/01_back-scene/*DRAFT*", "out/*/*_v2.dst", "out/*/*_v2.pes", "out/*/*_v2_preview.png", "out/*/*_v2_thread-chart.txt",
            "out/01_back-scene/*MOCKUP-vs-RevD.jpg", "out/*FULL-TECHPACK_RevB.pdf", "out/*EMBROIDERY-PACK_RevF.pdf"]:
    for f_ in glob.glob(pat): os.remove(f_)
shutil.rmtree("out/01_back-scene/splits", ignore_errors=True)
for G in ("A", "B", "C"):                      # grade back/sleeve files are superseded by the per-size set
    for f_ in glob.glob(f"out/01_back-scene/v3_{G}/*"): os.remove(f_) if os.path.isfile(f_) else shutil.rmtree(f_)
    if os.path.isdir(f"out/01_back-scene/v3_{G}"): os.rmdir(f"out/01_back-scene/v3_{G}")

# ---- thread charts for every v3 file
for f_ in sorted(glob.glob("out/**/*_v3_*.pes", recursive=True) + glob.glob("out/**/splits/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")

# ---- package
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
for e in ("01_back-scene", "02_chest-branch", "03_chest-pine", "04_lower-bamboo"):
    shutil.copytree(f"out/{e}", f"{PKG}/elements/{e}", ignore=shutil.ignore_patterns("summary.json", "result.json"))
shutil.copytree("out/pattern", f"{PKG}/pattern")
for pdf in glob.glob("out/HAKI_Drum-Island_*FULL-TECHPACK_RevC*.pdf"): shutil.copy(pdf, PKG)
open(f"{PKG}/README.txt", "w").write("""HAKI STUDIOS - Drum Island Jacket, Plum + Pine (style HK-JK-DRUM-PP)
Garment tech pack Rev C + embroidery Rev G - 16 Oct 2026

HAKI_Drum-Island_plum-pine_FULL-TECHPACK_RevC.pdf
    T1-T16 garment pages (incl. pattern T11-T13, inside view, operations, revision log), then embroidery G1-G5 + element specs.

pattern/
    HK-JK-DRUM-PP_pattern_<size>.dxf     AAMA-layer DXF, one size per file (1 cut, 14 sew, 4 notches, 7 grain, 8 internal +
                                         embroidery placement, 13 drill holes / needle start, 15 annotation). Units mm.
    HK-JK-DRUM-PP_pattern_ALL-SIZES.dxf  every size in one file
    HK-JK-DRUM-PP_pattern_M_1to1_PLOT.pdf  size M, one page per piece at 1:1 (check the 100 mm test box)
    FIRST pattern drafted from the measurement chart: sew + fit a size-M sample before cutting the size set.

elements/01_back-scene/v3_by-size/<size>/   01 back + sleeve-wrap stitch files for that size (DST + PES), previews,
                                            thread charts, splits/S1-S4 for a 360 x 360 frame (stop 1 = basting crosses)
elements/0[234]_*/v3_<A|B|C>/               front stitch files per art grade: A = XS-S, B = M-XL, C = XXL-3XL (04 uses B on XXL/3XL)
elements/*/*_SPEC_*.pdf, *_ART*.svg          element specs + region art with digitizing attributes (size M)

All stitch files: 15 threads max (15-needle head). Thread: Madeira Polyneon 40 (confirmed); Isacord numbers are alternates only. They are production-intent drafts: the factory digitizer opens them,
checks density + pull on 12 oz duck, edits if needed, and sews out before bulk.
""")
for z in glob.glob("out/*.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_Drum-Island_plum-pine_RevC-G_files.zip .", shell=True)
print("zip MB", os.path.getsize("out/HAKI_Drum-Island_plum-pine_RevC-G_files.zip") // 1_000_000)
