"""Package: thread charts for every stitch file, elements/ + pattern/ folders, README, zip (shrunk PDF)."""
import cccore
import os, shutil, glob, subprocess, json
import pyembroidery as pe
for f_ in sorted(glob.glob("out/0[12]_*/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
for e, (slug, title, pcs) in cccore.ELEMS.items():
    shutil.copytree(f"out/{e}_{slug}", f"{PKG}/elements/{e}_{slug}", ignore=shutil.ignore_patterns("summary.json", "result_*.json"))
shutil.copytree("out/pattern", f"{PKG}/pattern", ignore=shutil.ignore_patterns("*.png"))
full = glob.glob(f"out/HAKI_{cccore.SHORT}_FULL-TECHPACK_*.pdf")[0]; shutil.copy(full, PKG)
cur = json.load(open("dst_current.json"))
nums = "\n".join(f"    {p} {cccore.PIECE_NAME[p]}: {cur[p]['stitches']:,} stitches / {cur[p]['trims']} trims / {cur[p]['threads']} threads" for p in cccore.PIECES)
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {cccore.NAME} (style {cccore.STYLE})
Garment tech pack {cccore.REV_GAR} + embroidery {cccore.REV_EMB} - {cccore.DATE}

{os.path.basename(full)}
    T1-T9 garment pages (zip-hoodie block = Drum Island body + 3-panel sherpa hood + self-fabric bands; welts at this jacket's
    position; embroidery placement + keep-outs per size), then embroidery G1-G6, the 01 + 02 element specs and F1 factory requests.

pattern/
    {cccore.STYLE}_pattern_<size>.dxf      AAMA-layer DXF per size (1 cut, 14 sew, 4 notches, 7 grain, 8 internal + embroidery placement,
                                          13 drill holes / needle starts, 15 annotation). Units mm.
    {cccore.STYLE}_pattern_ALL-SIZES.dxf   every size in one file
    {cccore.STYLE}_pattern_M_1to1_PLOT.pdf size M, one page per piece at 1:1 (check the 100 mm test box)

elements/01_front-scene/<size>/           FR (wearer's right front) + FL (wearer's left front): DST + PES, previews, thread charts.
elements/02_sleeve-garden/<size>/         SR (wearer's right sleeve) + SL (wearer's left sleeve).
    splits/ = S1_top + S2_bottom for the 360 x 360 frame (stop 1 opens with registration crosses in its own thread -
    pick out after the last hooping). Full files = one hooping on a larger frame.
elements/*/ *_SPEC_*.pdf                  element specs (5 pages each); *_M_ART*.svg = size-M region art with digitizing attributes.

Size M (read back from the DST):
{nums}
Max 12 thread colours per file (factory limit, incl. registration). The files are production-intent drafts: the factory digitizer
opens them, checks density + pull on the washed duck, edits if needed, and sews a strike-off (F1) before bulk.
Every value marked [proposed - confirm] in the PDF is still open.
""")
for z in glob.glob("out/*.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_{cccore.SHORT}_{cccore.REV_GAR.replace(' ', '')}_files.zip .", shell=True)
print("zip MB", round(os.path.getsize(glob.glob('out/*.zip')[0]) / 1e6, 1))
