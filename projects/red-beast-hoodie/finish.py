"""Package: thread charts for every stitch file, elements/ folder, README, zip. Pattern folder is added once the hooded
pattern exists (engine PR 'hooded-variant'); until then the pack is embroidery-only."""
import rbcore
import os, shutil, glob, subprocess, json
import pyembroidery as pe
for f_ in sorted(glob.glob("out/0[12]_*/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
for e, (slug, title, pcs) in rbcore.ELEMS.items():
    shutil.copytree(f"out/{e}_{slug}", f"{PKG}/elements/{e}_{slug}", ignore=shutil.ignore_patterns("summary.json", "result_*.json"))
if os.path.isdir("out/pattern"): shutil.copytree("out/pattern", f"{PKG}/pattern", ignore=shutil.ignore_patterns("*.png"))
for c in glob.glob("out/compare_*.png"): shutil.copy(c, PKG)
pdfs = sorted(glob.glob("out/HAKI_RBST_*PACK*_small.pdf")) or sorted(glob.glob("out/HAKI_RBST_*PACK*.pdf"))
for p in pdfs: shutil.copy(p, PKG)
cur = json.load(open("dst_current.json"))
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {rbcore.NAME} (style {rbcore.STYLE})
Embroidery {rbcore.REV_EMB} - {rbcore.DATE}

{', '.join(os.path.basename(p) for p in pdfs)}
    G1-G6 embroidery pages, element specs 01 (beast head, fronts) + 02 (slash streaks, sleeves), F1 factory requests.
    Garment pages (T) + pattern follow when the hooded Drum Island pattern is released (hood block pending).

elements/01_beast-head/<size>/        FR (wearer's right front) + FL (wearer's left front): DST + PES, previews, thread charts.
elements/02_sleeve-streaks/<size>/    SR (wearer's right sleeve, S01) + SL (wearer's left sleeve, S02).
    splits/ = S1_top + S2_bottom for the factory frame (stop 1 opens with registration crosses in its own thread -
    pick out after the last hooping). Pieces that fit one hooping have no splits/.
elements/*/*_SPEC_*.pdf               element spec (5 pages); *_M_ART*.svg = size-M region art with digitizing attributes.
compare_*.png                         mockup vs stitch render, same scale, zoomed regions.

Size M (read from the DST): """ + " · ".join(f"{P} {cur[P]['stitches']:,} st / {cur[P]['trims']} trims" for P in rbcore.PIECES) + f""".
Max {12} thread colours per file (factory limit, incl. registration). Production-intent drafts: the factory digitizer checks density + pull
on the shell and sews out size M before bulk. Every value marked [proposed - confirm] in the PDF is still open.
""")
for z in glob.glob("out/*.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_RBST_{rbcore.REV_EMB.replace(' ', '')}_files.zip .", shell=True)
print("zip MB", round(os.path.getsize(glob.glob('out/*.zip')[0]) / 1e6, 1))
