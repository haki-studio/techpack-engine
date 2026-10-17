"""Package: thread charts for every stitch file, elements/ + pattern/ folders, compare sheets, README, zip."""
import wavecore as WC
import os, shutil, glob, subprocess, json
import pyembroidery as pe
for f_ in sorted(glob.glob("out/01_wave/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
shutil.copytree("out/01_wave", f"{PKG}/elements/01_wave", ignore=shutil.ignore_patterns("summary.json", "result_*.json"))
shutil.copytree("out/pattern", f"{PKG}/pattern", ignore=shutil.ignore_patterns("*.png"))
os.makedirs(f"{PKG}/compare", exist_ok=True)
for c in glob.glob("out/compare_*.png"): shutil.copy(c, f"{PKG}/compare/")
full = sorted(glob.glob("out/HAKI_WAVE_FULL-TECHPACK_*_small.pdf") or glob.glob("out/HAKI_WAVE_FULL-TECHPACK_*.pdf"))[0]; shutil.copy(full, PKG)
cur = json.load(open("dst_current.json"))
lines = "\n".join(f"    {P} {WC.PIECE_NAME[P]:<22} {cur[P]['stitches']:>9,} stitches  {cur[P]['trims']:>5} trims  {cur[P]['stops']:>3} stops  {cur[P]['hoopings']} hooping(s)" for P in WC.PIECES)
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {WC.NAME} (style {WC.STYLE})
Garment tech pack {WC.REV_GAR} + embroidery {WC.REV_EMB} - {WC.DATE}

{os.path.basename(full)}
    T1-T16 garment pages (Drum Island block + pattern, welts at this jacket's position), then embroidery G1-G6, the 01 wave
    element spec (6 pages) and F1 factory requests.

pattern/
    {WC.STYLE}_pattern_<size>.dxf      AAMA-layer DXF per size (1 cut, 14 sew, 4 notches, 7 grain, 8 internal + embroidery placement,
                                       13 drill holes / needle starts, 15 annotation). Units mm.
    {WC.STYLE}_pattern_ALL-SIZES.dxf   every size in one file
    {WC.STYLE}_pattern_M_1to1_PLOT.pdf size M, one page per piece at 1:1 (check the 100 mm test box)

elements/01_wave/<size>/               per size: BK back, FR / FL fronts, SR / SL sleeves - full stitch files (DST + PES), previews,
                                       thread charts. splits/ = the hoop sections for the factory frame (stop 1 opens with the
                                       registration crosses in its own thread - pick out after the last hooping).
elements/01_wave/*_SPEC_*.pdf          element spec; *_M_ART*.svg = size-M region art with digitizing attributes per piece.
compare/                               render vs stitch preview at the same scale, per piece, with zoomed regions.

Size M (read from the DST):
{lines}
max 12 thread colours per file (factory limit, incl. registration); this jacket uses 9. The files are production-intent drafts:
the factory digitizer opens them, checks density + pull on 12 oz duck, edits if needed, and sews out size M before bulk.
Every value marked [proposed - confirm] in the PDF is still open.
""")
for z in glob.glob("out/*.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_WAVE_{WC.REV_GAR.replace(' ', '')}_files.zip .", shell=True)
print("zip MB", round(os.path.getsize(glob.glob('out/*.zip')[0]) / 1e6, 1))
