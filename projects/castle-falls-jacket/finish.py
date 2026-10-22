"""Package: thread charts for every stitch file, elements/ + pattern/ folders, README, recompressed PDF, zip."""
import cfcore
import os, shutil, glob, subprocess, json
import pyembroidery as pe
# prune stitch files no current result references (e.g. XXL/3XL front S1_top/S2_bottom from the 16 Oct split naming) so the
# package can only carry the files the documents describe
ALL = json.load(open("dst_all.json")); live = set()
for sz, d in ALL.items():
    for P, v in d.items():
        live.add(v["full"]["file"]); live.update(s["file"] for s in (v.get("splits") or {}).get("sections", {}).values())
for f_ in glob.glob("out/0[123]_*/**/HAKI_*.*", recursive=True):
    stem = f_
    for suf in ("_thread-chart.txt", "_preview.png", ".dst", ".pes"):
        if f_.endswith(suf): stem = f_[: -len(suf)]; break
    else: continue
    if stem not in live: print("pruned stale", f_); os.remove(f_)
for f_ in sorted(glob.glob("out/0[123]_*/**/*.pes", recursive=True)):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace(".pes", ""), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1): lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace(".pes", "_thread-chart.txt"), "w").write("\n".join(lines) + "\n")
full = glob.glob(f"out/HAKI_{cfcore.SHORT}_FULL-TECHPACK_*.pdf"); full = [p for p in full if "_small" not in p][0]
small = full.replace(".pdf", "_small.pdf")
subprocess.run(["python3", "shrink.py", full, small, "3000", "82"], check=True)
os.replace(small, full)
PKG = "out/pkg"; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f"{PKG}/elements")
for e, (slug, _, _) in cfcore.ELEMS.items():
    shutil.copytree(f"out/{e}_{slug}", f"{PKG}/elements/{e}_{slug}", ignore=shutil.ignore_patterns("summary.json", "result_*.json"))
shutil.copytree("out/pattern", f"{PKG}/pattern", ignore=shutil.ignore_patterns("*.png"))
for c in glob.glob("out/compare_*.png"): shutil.copy(c, PKG)
shutil.copy(full, PKG)
cur = json.load(open("dst_current.json"))
tot = sum(cur[p]["stitches"] for p in cfcore.PIECES); trims = sum(cur[p]["trims"] for p in cfcore.PIECES)
lines = "\n".join(f"    {p} ({cfcore.PIECE_NAME[p]}): {cur[p]['stitches']:,} stitches / {cur[p]['trims']} trims / {cur[p]['threads']} colours / {len(cur[p]['splits']['sections'])} hoopings" for p in cfcore.PIECES)
open(f"{PKG}/README.txt", "w").write(f"""HAKI STUDIOS - {cfcore.NAME} (style {cfcore.STYLE})
Garment tech pack {cfcore.REV_GAR} + embroidery {cfcore.REV_EMB} - {cfcore.DATE}

{os.path.basename(full)}
    T1-T16 garment pages (Drum Island block + pattern), then embroidery G1-G6, element specs 01 / 02 / 03, F1 factory requests.

pattern/
    {cfcore.STYLE}_pattern_<size>.dxf      AAMA-layer DXF per size (1 cut, 14 sew, 4 notches, 7 grain, 8 internal + embroidery placement
                                           + split lines, 13 drill holes / needle starts, 15 annotation). Units mm.
    {cfcore.STYLE}_pattern_ALL-SIZES.dxf   every size in one file
    {cfcore.STYLE}_pattern_M_1to1_PLOT.pdf size M, one page per piece at 1:1 (check the 100 mm test box)

elements/01_back-scene/<size>/     BK back (B01)
elements/02_front-scene/<size>/    FR wearer's right front (F02) + FL wearer's left front (F01)
elements/03_sleeve-scene/<size>/   SR wearer's right sleeve (S01) + SL wearer's left sleeve (S02)
    per size + piece: full stitch file (DST + PES), preview, thread chart; splits/ = sections for a 360 x 360 frame
    (stop 1 opens with registration crosses in its own thread - pick out after the last hooping).
elements/*/*_SPEC_*.pdf            element spec (5 pages); *_M_ART*.svg = size-M region art with digitizing attributes.
compare_*.png                      mockup vs stitch render at the same scale, with zoomed regions.

Size M, read from the DST files ({tot:,} stitches / {trims:,} trims per jacket):
{lines}
Max 12 thread colours per file (factory limit, incl. registration). Fidelity first: density, trims and run time are reported,
not limited - clean-up after the strike-off. The files are production-intent drafts: the factory digitizer opens them, checks
density + pull on 12 oz duck, edits if needed, and sews out before bulk. Every value marked [proposed - confirm] is still open.
""")
for z in glob.glob("out/*.zip"): os.remove(z)
if os.path.isdir("out/labels"): shutil.copytree("out/labels", f"{PKG}/labels")   # Haki standard main + care label files (gtp.build, LESSONS D7)
subprocess.run(f"cd {PKG} && zip -qr ../HAKI_{cfcore.SHORT}_{cfcore.REV_GAR.replace(' ', '')}_files.zip .", shell=True)
print("pdf MB", round(os.path.getsize(full) / 1e6, 1), "zip MB", round(os.path.getsize(glob.glob('out/*.zip')[0]) / 1e6, 1))
