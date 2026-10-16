"""Package: thread charts for every stitch file, elements/ + pattern/ folders, README, zip."""
import glcore
import os, shutil, glob, subprocess, json
import pyembroidery as pe
for f_ in sorted(glob.glob("out/01_front-scene/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
shutil.copytree("out/01_front-scene", f"{PKG}/elements/01_front-scene", ignore=shutil.ignore_patterns("summary.json", "result_*.json"))
shutil.copytree("out/pattern", f"{PKG}/pattern", ignore=shutil.ignore_patterns("*.png"))
full = glob.glob("out/HAKI_GRLN_FULL-TECHPACK_*.pdf")[0]; shutil.copy(full, PKG)
cur = json.load(open("dst_current.json"))
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {glcore.NAME} (style {glcore.STYLE})
Garment tech pack {glcore.REV_GAR} + embroidery {glcore.REV_EMB} - {glcore.DATE}

{os.path.basename(full)}
    T1-T16 garment pages (Drum Island block + pattern, welts at this jacket's position), then embroidery G1-G5 + the 01 front-scene spec.

pattern/
    {glcore.STYLE}_pattern_<size>.dxf      AAMA-layer DXF per size (1 cut, 14 sew, 4 notches, 7 grain, 8 internal + embroidery placement,
                                           13 drill holes / needle start, 15 annotation). Units mm.
    {glcore.STYLE}_pattern_ALL-SIZES.dxf   every size in one file
    {glcore.STYLE}_pattern_M_1to1_PLOT.pdf size M, one page per piece at 1:1 (check the 100 mm test box)

elements/01_front-scene/<size>/            per size: FR (wearer's right front) + FL (wearer's left front) stitch files (DST + PES),
                                           previews, thread charts. splits/ = S1_top + S2_bottom for a 360 x 360 frame
                                           (stop 1 = basting registration crosses, water-soluble, remove after sewing).
elements/01_front-scene/*_SPEC_*.pdf       element spec (5 pages); *_M_ART*.svg = size-M region art with digitizing attributes.

Size M: FR {cur['FR']['stitches']:,} stitches / {cur['FR']['trims_dst']} trims, FL {cur['FL']['stitches']:,} / {cur['FL']['trims_dst']} (read from the DST).
12 threads per file (<= 15-needle head). The files are production-intent drafts: the factory digitizer opens them, checks density + pull
on 12 oz duck, edits if needed, and sews out before bulk. Every value marked [proposed - confirm] in the PDF is still open.
""")
for z in glob.glob("out/*.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_GRLN_{glcore.REV_GAR.replace(' ', '')}_files.zip .", shell=True)
print("zip MB", round(os.path.getsize(glob.glob('out/*.zip')[0]) / 1e6, 1))
