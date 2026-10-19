"""Package (embroidery; garment pages wait for the hooded pattern): thread charts for every stitch file, elements/, README, zip."""
import kbcore
import os, shutil, glob, subprocess, json
import pyembroidery as pe
for f_ in sorted(glob.glob("out/0*_*/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
for el, (slug, _, _) in kbcore.ELEMS.items():
    shutil.copytree(f"out/{el}_{slug}", f"{PKG}/elements/{el}_{slug}", ignore=shutil.ignore_patterns("summary.json", "result_*.json"))
pdf = glob.glob(f"out/HAKI_{kbcore.SHORT}_EMBROIDERY-PACK_*.pdf")[0]; shutil.copy(pdf, PKG)
for c in glob.glob("out/compare_*.png"): shutil.copy(c, PKG)
cur = json.load(open("dst_current.json"))
nums = "\n".join(f"    {p} ({kbcore.PIECE_NAME[p]}): {cur[p]['stitches']:,} stitches / {cur[p]['trims']} trims / {cur[p]['stops']} stops" for p in kbcore.PIECES)
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {kbcore.NAME} (style {kbcore.STYLE})
Embroidery {kbcore.REV_EMB} - {kbcore.DATE}

{os.path.basename(pdf)}
    G1-G6 embroidery pages (G1 has the revision log), 01 front + 02 sleeves element specs (5 pp each), F1 factory requests.
    Rev B: FOUNDER CHANGE - the fish are tetras (inputs/reference_fish.png), not koi; lilies + petals traced from the close-up.
    Garment pages (T1-T16) + pattern (DXF / 1:1 PDF): WAITING for the hood decision (hooded Drum Island pattern).

elements/01_front-fish/<size>/     FR (wearer's right front) + FL (wearer's left front) stitch files (DST + PES), previews, thread charts.
elements/02_sleeve-fish/<size>/    SR (wearer's right sleeve) + SL (wearer's left sleeve), front half of each sleeve.
    splits/ = S1_top + S2_bottom for a 360 x 360 frame where the art is taller than the frame (stop 1 opens with
    registration crosses in its own thread - pick out after the last hooping).
elements/*/ *_SPEC_*.pdf          element specs; *_M_ART*.svg = size-M region art with digitizing attributes.
compare_*.png                     mockup | close-up | stitches read back from the size-M DST | fish reference, same scale + zooms.

Size M (read from the DST):
{nums}
max 12 thread colours per file (factory limit, incl. registration). Production-intent drafts: the factory digitizer checks
density + pull on the shell and sews out size M before bulk. Every [proposed - confirm] in the PDF is still open.
""")
for z in glob.glob("out/*.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_{kbcore.SHORT}_{kbcore.REV_EMB.replace(' ', '')}_files.zip .", shell=True)
print("zip MB", round(os.path.getsize(glob.glob('out/*.zip')[0]) / 1e6, 1))
