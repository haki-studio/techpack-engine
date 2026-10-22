"""Package: thread charts for every stitch file, elements/ folder, README, zip (out/HAKI_KCOS_<Rev>_files.zip)."""
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
import factory as FA, kcdoc as KD
ALL = json.load(open("dst_all.json")); _fl = ["FOAM PROCEDURE (read from each file's own stop list; the same on F2 + S1):"]
for _sz in kccore.SIZES:
    for _p in ("FR", "FL"):
        _r = ALL[_sz][_p]
        for _nm, _f in [("full", _r["full"])] + list(_r.get("splits", {}).get("sections", {}).items()):
            _fs = KD.foam_steps(_f)
            _fl.append(f"  {os.path.basename(_f['file'])}.dst: " + (_fs["line"] if _fs else "no puff in this hooping - no foam."))
FOAM = "\n".join(_fl) + "\n"
FR = " x ".join(f"{v:.0f}" for v in FA.largest_frame(FA.load()))
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {kccore.NAME} (style {kccore.STYLE})
Embroidery {kccore.REV_EMB} - {kccore.DATE}

{os.path.basename(full)}
    Embroidery pack: G1-G6, element specs E01-E05, stop sequences S1-S2, region table R1, F1 factory requests.
    Garment pages T1-T9 (zip-hoodie block) come first, then the embroidery pages.
pattern/                        DXF per size + all sizes, 1:1 plot PDF (size M).

elements/stitch-files/<size>/   per size: FR (wearer's right front), FL (wearer's left front), SR (right sleeve), SL (left sleeve)
                                stitch files (DST + PES), previews, thread charts. splits/ = hoop sections for the """ + FR + """ frame
                                (stop 1 opens with registration crosses in its own thread - pick out after the last hooping).
                                Fronts FR + FL carry 3D puff: see FOAM PROCEDURE below (one machine STOP per puff hooping).
elements/art/                   per-size flat art previews + mockup comparison sheets.

Size M: """ + ", ".join(f"{P} {cur[P]['stitches']:,} stitches / {cur[P]['trims']} trims" for P in kccore.PIECES) + """ (read from the DST).
Max 12 thread colours per file (factory limit); size M uses """ + ", ".join(f"{P} {cur[P]['threads']}" for P in kccore.PIECES) + f""" ({len(kccore.KC_KEYS)} threads on the jacket).
Full files (no splits/) = one hooping on a frame that holds the whole piece (sizes on G5); else sew the split sections.
Rev D (founder answers 20 Oct): 3D puff on every sign part (not the field stars); strokes under 2.5 mm stay flat (list on G4);
CN text 不要世界污染 (Simplified). Back + hood: artwork to follow [MISSING]. Foam on its own machine stop, no flat stitches
inside the foam beyond a 1 mm edge band (checked on every file, S1), all files rebuilt from the current art. Compare sheets in
elements/art are drawn from the DST files; the art is traced from the garment mockup (source of truth).
""" + FOAM + """
Files are production-intent drafts: the factory digitizer checks
density, pull and puff on the washed duck, edits if needed, and sews out size M before bulk. Every value marked
[proposed - confirm] in the PDF is still open.
""")
for z in glob.glob(f"out/HAKI_{kccore.SHORT}_{kccore.REV_EMB.replace(' ', '')}_files.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_{kccore.SHORT}_{kccore.REV_EMB.replace(' ', '')}_files.zip .", shell=True)
print("zip MB", round(os.path.getsize(f"out/HAKI_{kccore.SHORT}_{kccore.REV_EMB.replace(' ', '')}_files.zip") / 1e6, 1))
