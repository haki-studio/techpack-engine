"""Package: stale split files removed, merged INTERNAL tech pack (garment T + embroidery G), thread charts for every stitch file, elements/, README, zip."""
import kbcore
import os, shutil, glob, subprocess, json
import pyembroidery as pe
# stale split files (from an earlier build whose split differed) are removed: only files named in result_*.json stay
for rp in glob.glob("out/0*_*/*/result_*.json"):
    r = json.load(open(rp)); keep = {os.path.basename(s["file"]) for s in r.get("splits", {}).get("sections", {}).values()}
    P = os.path.basename(rp)[7:-5]
    for fn in glob.glob(os.path.join(os.path.dirname(rp), "splits", f"*_{P}_*")):
        b = os.path.basename(fn)
        if not any(b.startswith(k + ".") or b.startswith(k + "_") for k in keep): os.remove(fn); print("removed stale", fn)
for f_ in sorted(glob.glob("out/0*_*/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
for el, (slug, _, _) in kbcore.ELEMS.items():
    shutil.copytree(f"out/{el}_{slug}", f"{PKG}/elements/{el}_{slug}", ignore=shutil.ignore_patterns("summary.json", "result_*.json"))
emb = f"out/HAKI_{kbcore.SHORT}_EMBROIDERY-PACK_{kbcore.REV_EMB.replace(' ', '')}.pdf"
gar = f"out/garment/HAKI_{kbcore.SHORT}_GARMENT_{kbcore.REV_GAR.replace(' ', '')}.pdf"   # this revision's garment pages (a glob [0] picked an older Rev in out/)
from pypdf import PdfWriter, PdfReader
w = PdfWriter(); w.append(PdfReader(gar)); w.append(PdfReader(emb))
full = f"out/HAKI_{kbcore.SHORT}_INTERNAL_{kbcore.REV_EMB.replace(' ', '')}.pdf"; w.write(full + ".tmp.pdf")     # internal merged pack; factory copies = rfq.py
subprocess.run(["python3", "shrink.py", full + ".tmp.pdf", full, "3000", "82"], check=True); os.remove(full + ".tmp.pdf")
pdf = full; shutil.copy(pdf, PKG)
shutil.copytree("out/garment/pattern", f"{PKG}/pattern")
NP = len(PdfReader(pdf).pages)
for c in glob.glob("out/compare_*.png"): shutil.copy(c, PKG)
cur = json.load(open("dst_current.json"))
nums = "\n".join(f"    {p} ({kbcore.PIECE_NAME[p]}): {cur[p]['stitches']:,} stitches / {cur[p]['trims']} trims / {cur[p]['stops']} stops" for p in kbcore.PIECES)
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {kbcore.NAME} (style {kbcore.STYLE})
Embroidery {kbcore.REV_EMB} - {kbcore.DATE}

{os.path.basename(pdf)}   ({NP} pages)
    T1-T8 garment pages (zip-hoodie block + this design's welts: flats, size chart + pattern check, pieces + cut list,
    hood + bands, BOM, embroidery placement per size, questions + revision log), then G1-G6 embroidery pages
    (G1 has the revision log), 01 front + 02 sleeves element specs (5 pp each), F1 factory requests.
    Rev B: FOUNDER CHANGE - the fish are tetras (inputs/reference_fish.png), not koi; lilies + petals traced from the close-up.
pattern/   AAMA-layer DXF per size + all sizes (layer 8 = art outline + box + design centre per piece, 13 = needle start),
           1:1 plot PDF size M (check the 100 mm box). Block: engine hoodie.py (founder decision 19 Oct, hood option 1).

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
for z in glob.glob("out/*_INTERNAL_files.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_{kbcore.SHORT}_{kbcore.REV_EMB.replace(' ', '')}_INTERNAL_files.zip .", shell=True)
print("zip MB", round(os.path.getsize(glob.glob('out/*_INTERNAL_files.zip')[0]) / 1e6, 1))
