"""Package: thread charts for every stitch file, elements/ + pattern/ folders, compare sheets, README, zip."""
import wavecore as WC
import os, shutil, glob, subprocess, json
import factory as FA
import pyembroidery as pe
for f_ in sorted(glob.glob("out/01_wave/M/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")
PKG = "out/pkg_sampling"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements/01_wave")
ign = shutil.ignore_patterns("summary.json", "result_*.json")
shutil.copytree("out/01_wave/M", f"{PKG}/elements/01_wave/M", ignore=ign)
for f_ in glob.glob("out/01_wave/*_SPEC_*.pdf") + glob.glob("out/01_wave/*_M_ART*.svg"): shutil.copy(f_, f"{PKG}/elements/01_wave/")
os.makedirs(f"{PKG}/compare", exist_ok=True)
for c in glob.glob("out/compare_*.png"): shutil.copy(c, f"{PKG}/compare/")
emb = sorted(glob.glob("out/HAKI_WAVE_EMBROIDERY-PACK_*_small.pdf"))[0]; shutil.copy(emb, PKG)
cur = json.load(open("dst_current.json"))
lines = "\n".join(f"    {P} {WC.PIECE_NAME[P]:<22} {cur[P]['stitches']:>9,} stitches  {cur[P]['trims']:>5} trims  {cur[P]['stops']:>3} stops  {cur[P]['hoopings']} hooping(s)" for P in WC.PIECES)
tot = sum(cur[P]['stitches'] for P in WC.PIECES); trm = sum(cur[P]['trims'] for P in WC.PIECES); hp = sum(cur[P]['hoopings'] for P in WC.PIECES)
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {WC.NAME} (style {WC.STYLE})
EMBROIDERY SAMPLING PACKAGE - embroidery {WC.REV_EMB} - {WC.DATE} - size M strike-off

{WC.GARMENT_NOTE}. This package is the embroidery only: sew the size-M files on cut pieces of the
production shell (washed navy 12 oz duck) and answer the F1 page.

{os.path.basename(emb)}
    G1-G6 embroidery pages, the 01 wave element spec (6 pages) and F1 factory requests
    (frames / sewing field, chenille vs padded satin for the foam, thread card, quote basis).

elements/01_wave/M/                    BK back, FR / FL fronts, SR / SL sleeves - full stitch files (DST + PES), previews,
                                       thread charts. splits/ = the hoop sections for the assumed {'x'.join(str(int(v)) for v in FA.largest_frame(FA.load()))} frame
                                       (stop 1 opens with the registration crosses in that stop's thread - pick out after
                                       the last hooping). If your frame is bigger, tell us: every split is rebuilt in one run.
elements/01_wave/*_SPEC_*.pdf          element spec; *_M_ART*.svg = size-M region art with digitizing attributes per piece.
compare/                               render vs the shipped DST (every stitch) at the same scale, per piece, + zoomed regions.

Size M (read from the DST):
{lines}
    total {tot:,} stitches, {trm:,} trims, {hp} hoopings

max {FA.max_threads(FA.load())} thread colours per file (factory limit, incl. registration); this jacket uses 9. The files are
production-intent drafts: the factory digitizer opens them, checks density + pull on 12 oz duck, edits if needed, and
sews out size M before anything else. Every value marked [proposed - confirm] in the PDF is still open.
Other sizes (XS-3XL) are rebuilt from the same art after the strike-off.
""")
for z in glob.glob("out/HAKI_WAVE_*SAMPLING*.zip"): os.remove(z)
zp = f"out/HAKI_WAVE_EMB-SAMPLING_{WC.REV_EMB.replace(' ', '')}_M.zip"
subprocess.run(f"cd {PKG} && zip -qr ../{os.path.basename(zp)} .", shell=True)
print("zip MB", round(os.path.getsize(zp) / 1e6, 1), zp)
