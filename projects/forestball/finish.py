"""Package: thread charts for every stitch file, out/pkg (elements/, pattern/, merged PDF, README), zip."""
import os, shutil, glob, subprocess, json
import fbcore
import pyembroidery as pe

for f_ in sorted(glob.glob("out/0*/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1):
        d = th.description or ""
        lines.append(f"{i:>3}   {th.hex_color()}  {d}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")

PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
for e in ("01_back-scene", "02_chest-branch"):
    shutil.copytree(f"out/{e}", f"{PKG}/elements/{e}", ignore=shutil.ignore_patterns("summary.json", "result.json"))
shutil.copytree("out/pattern", f"{PKG}/pattern")
full = glob.glob("out/HAKI_FB_Forestball_FULL-TECHPACK_*.pdf")
for pdf in full: shutil.copy(pdf, PKG)
A = json.load(open("dst_all.json"))
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {fbcore.NAME} (style {fbcore.STYLE})
Garment tech pack {fbcore.REV_GAR} + embroidery {fbcore.REV_EMB} - {fbcore.DATE}

{os.path.basename(full[0]) if full else 'FULL-TECHPACK pdf'}
    T1-T16 garment pages (pattern T11-T13, inside view, operations, revision log), then embroidery G1-G5 + element specs 01, 02.

LICENSED ELEMENT - READ FIRST
    The orb in the back stream is a LICENSED figure. It is NOT in these files and no lookalike was drawn.
    Its area is reserved as a placeholder box (01 spec p1, G2, pattern B01 layer 8): the stitch file sews only an
    outline of the box in Stream-light thread as its first stop (factory 12-colour limit: no separate basting colour). The factory digitizer adds the figure from the
    licensor-approved artwork, sized to the box. Licence approval is not verified by Haki tech - confirm before production.

pattern/
    {fbcore.STYLE}_pattern_<size>.dxf     AAMA-layer DXF per size (1 cut, 14 sew, 4 notches, 7 grain, 8 internal + embroidery
                                         placement incl. the licensed placeholder box, 13 drill holes / needle start, 15 annotation). mm.
    {fbcore.STYLE}_pattern_ALL-SIZES.dxf  every size in one file
    {fbcore.STYLE}_pattern_M_1to1_PLOT.pdf  size M, one page per piece at 1:1 (check the 100 mm test box)
    Drum Island pattern (same chart as the plum + pine jacket). Sew + fit a size-M sample before cutting the size set.

elements/01_back-scene/<grade>/            01 back stitch file per art grade (DST + PES), preview, thread chart;
                                           splits/S1-S4 for a 360 x 360 frame (registration crosses in the first thread)
elements/02_chest-branch/<grade>/          02R + 02L per art grade
    grades: A = XS-S (90 %), B = M-XL (100 %), C = XXL-3XL (108 %)
elements/*/*_SPEC_*.pdf, *_ART*.svg         element specs + region art with digitizing attributes (size M)

All stitch files: <= 12 thread colours per file (factory limit, incl. outline + crosses). Production-intent drafts: the factory digitizer opens them, checks density + pull
on 12 oz duck, edits if needed, and sews out before bulk.
""")
for z in glob.glob("out/*.zip"): os.remove(z)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_FB_Forestball_{fbcore.REV_GAR.replace(' ', '')}_files.zip .", shell=True)
z = glob.glob("out/*.zip")[0]; print("zip", z, os.path.getsize(z) // 1_000_000, "MB")
