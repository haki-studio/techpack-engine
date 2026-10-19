"""Package: thread charts for every stitch file, elements/ folder, README, zip (out/HAKI_KCOS_RevA_files.zip)."""
import kccore
import os, shutil, glob, subprocess, json
import pyembroidery as pe
for f_ in sorted(glob.glob("out/stitch/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
shutil.copytree("out/stitch", f"{PKG}/elements/stitch-files", ignore=shutil.ignore_patterns("result_*.json"))
os.makedirs(f"{PKG}/elements/art", exist_ok=True)
for f_ in glob.glob("out/art/*_flat.png") + glob.glob("out/compare_*.png"): shutil.copy(f_, f"{PKG}/elements/art/")
if os.path.isdir("out/pattern"): shutil.copytree("out/pattern", f"{PKG}/pattern", ignore=shutil.ignore_patterns("*.png"))
full = f"out/HAKI_{kccore.SHORT}_FULL-TECHPACK_{kccore.REV_EMB.replace(' ', '')}.pdf"; shutil.copy(full, PKG)
cur = json.load(open("dst_current.json"))
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {kccore.NAME} (style {kccore.STYLE})
Embroidery {kccore.REV_EMB} - {kccore.DATE}

{os.path.basename(full)}
    Embroidery pack: G1-G6, element specs E01-E05, stop sequences S1-S2, region table R1, F1 factory requests.
    Garment pages (T*) and the pattern follow when the hooded Drum Island block is merged into the engine.

elements/stitch-files/<size>/   per size: FR (wearer's right front), FL (wearer's left front), SR (right sleeve), SL (left sleeve)
                                stitch files (DST + PES), previews, thread charts. splits/ = hoop sections for a 360 x 360 frame
                                (stop 1 opens with registration crosses in its own thread - pick out after the last hooping).
                                Fronts FR + FL: PAUSE before the first puff stop (lay 3 mm black foam: FR over badge 01 + the 03 dot
                                ring, FL over badge 02), tear the foam before the last stop on FR (white star centre) - see S1.
elements/art/                   per-size flat art previews + mockup comparison sheets.

Size M: """ + ", ".join(f"{P} {cur[P]['stitches']:,} stitches / {cur[P]['trims']} trims" for P in kccore.PIECES) + """ (read from the DST).
Max 12 thread colours per file (factory limit); size M uses """ + ", ".join(f"{P} {cur[P]['threads']}" for P in kccore.PIECES) + f""" ({len(kccore.KC_KEYS)} threads on the jacket).
Rev B (review fixes): stroke-column satin text, stipple glow halo, domed puff rims (lighter tint threads), faceted stars, curved JP
baseline, KR ornaments, every mockup star placed. Compare sheets in elements/art are drawn from the DST files.
Files are production-intent drafts: the factory digitizer checks
density, pull and puff on the washed duck, edits if needed, and sews out size M before bulk. Every value marked
[proposed - confirm] in the PDF is still open.
""")
for z in glob.glob(f"out/HAKI_{kccore.SHORT}_{kccore.REV_EMB.replace(' ', '')}_files.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_{kccore.SHORT}_{kccore.REV_EMB.replace(' ', '')}_files.zip .", shell=True)
print("zip MB", round(os.path.getsize(f"out/HAKI_{kccore.SHORT}_{kccore.REV_EMB.replace(' ', '')}_files.zip") / 1e6, 1))
