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
for c in glob.glob("out/compare_*.png") + ["out/continuity_M.png", "out/crops_before_after.png"]: shutil.copy(c, f"{PKG}/compare/")
os.makedirs(f"{PKG}/compare/seams", exist_ok=True)
for c in glob.glob("out/continuity_*.png") + glob.glob("out/discont_*.png"):
    if "_art" in c or "_before" in c or c.endswith("continuity_M.png"): continue
    shutil.copy(c, f"{PKG}/compare/seams/")
shutil.copytree("out/placement", f"{PKG}/placement", ignore=shutil.ignore_patterns("*.png"))
emb = f"out/HAKI_WAVE_EMBROIDERY-PACK_{WC.REV_EMB.replace(' ', '')}_small.pdf"; shutil.copy(emb, PKG)
cur = json.load(open("dst_current.json"))
def TS(r): return r.get("total_stitches", r["stitches"])
def TT(r): return r.get("total_trims", r["trims"])
lines = "\n".join(f"    {P} {WC.PIECE_NAME[P]:<22} {TS(cur[P]):>9,} stitches  {TT(cur[P]):>5} trims  {cur[P]['hoopings']} hooping(s)  (lockstitch {cur[P]['stitches']:,} + chenille {cur[P].get('chenille', {}).get('stitches', 0):,})" for P in WC.PIECES)
tot = sum(TS(cur[P]) for P in WC.PIECES); trm = sum(TT(cur[P]) for P in WC.PIECES); hp = sum(cur[P]['hoopings'] for P in WC.PIECES)
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {WC.NAME} (style {WC.STYLE})
EMBROIDERY SAMPLING PACKAGE - embroidery {WC.REV_EMB} - {WC.DATE} - size M strike-off

{WC.GARMENT_NOTE}. This package is the embroidery only: sew the size-M files on cut pieces of the
production shell (washed navy 12 oz duck) and answer the F1 page.

{os.path.basename(emb)}
    G1-G6 embroidery pages, the 01 wave element spec (6 pages) and F1 factory requests
    (frames / sewing field, chenille vs padded satin for the foam, thread card, quote basis).

elements/01_wave/M/                    BK back, FR / FL fronts, SR / SL sleeves (PRIMARY): per piece the lockstitch file +
                                       its _CHENILLE file (foam, chenille head, same hooping + origin, sewn after the
                                       lockstitch). Fronts = ONE hooping each (full files); splits/ = the back (2) and sleeve
                                       hoopings for the {'x'.join(str(int(v)) for v in FA.largest_frame(FA.load()))} frame, each with its _CHENILLE file
                                       (stop 1 opens with the registration crosses - pick out after the last hooping).
elements/01_wave/M/alt_padded/         ALTERNATIVE: foam as padded tatami + loop runs (no chenille), same hoopings.
elements/01_wave/M/swatch/             FOAM SWATCH: one crest x4 (padded / moss look, Foam white / ecru) - sew first.
placement/                             ART PLACEMENT ONLY (garment pattern to follow): 1:1 plot PDF + DXF per piece, size M,
                                       art outline, split lines, crosses, needle starts, MATCH MARKS (notch both pieces).
elements/01_wave/*_SPEC_*.pdf          element spec; *_M_ART*.svg = size-M region art with digitizing attributes per piece.
compare/                               render vs the shipped DST (live view, every stitch) per piece + zooms + gate tables;
                                       continuity_M.png + seams/ = every seam closed up (from the DSTs) + the cut-line check.

Size M (read from the DST):
{lines}
    total {tot:,} stitches, {trm:,} trims, {hp} hoopings

max {FA.max_threads(FA.load())} thread colours per file (factory limit, incl. registration); this jacket uses 9 (+ the ecru candidate in the swatch). The files are
production-intent drafts: the factory digitizer opens them, checks density + pull on 12 oz duck, edits if needed, and
sews out size M before anything else. Every value marked [proposed - confirm] in the PDF is still open.
Other sizes (XS-3XL) are rebuilt from the same art after the strike-off.
""")
for z in glob.glob("out/HAKI_WAVE_*SAMPLING*.zip"): os.remove(z)
zp = f"out/HAKI_WAVE_EMB-SAMPLING_{WC.REV_EMB.replace(' ', '')}_M.zip"
if os.path.isdir("out/labels"): shutil.copytree("out/labels", f"{PKG}/labels")   # Haki standard main + care label files (gtp.build, LESSONS D7)
subprocess.run(f"cd {PKG} && zip -qr ../{os.path.basename(zp)} .", shell=True)
print("zip MB", round(os.path.getsize(zp) / 1e6, 1), zp)
