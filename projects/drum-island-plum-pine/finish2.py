"""Rev E packaging: refresh flat art + comparison, thread charts for v2 files, clean superseded files, zip."""
import pickle, cairocffi as cairo, os, shutil, glob, subprocess, json
from PIL import Image, ImageDraw, ImageFont
from shapely.ops import unary_union
import pyembroidery as pe
from motifs2 import HEX
import stitchrender as SR

# ---- superseded files out of the element folders
for pat in ["out/01_back-scene/*SPEC_RevD.pdf", "out/0[234]_*/*SPEC_RevA.pdf", "out/01_back-scene/*DRAFT*", "out/01_back-scene/*MOCKUP-vs-RevD.jpg"]:
    for f_ in glob.glob(pat): os.remove(f_)

# ---- flat art for auto-digitize (back), refit geometry
d = pickle.load(open('back2_vis.pkl', 'rb')); vb = d['back']
ub = unary_union([r['geom'] for r in vb]).bounds
ppm = 6.0; x0, y0 = ub[0]-4, ub[1]-4; W = int((ub[2]-ub[0]+8)*ppm); H = int((ub[3]-ub[1]+8)*ppm)
surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H); c = cairo.Context(surf); c.set_antialias(cairo.ANTIALIAS_NONE)
c.set_source_rgb(1, 1, 1); c.paint(); c.scale(ppm, ppm); c.translate(-x0, -y0)
for r in vb:
    for p in SR.polys(r['geom']):
        for ring in [p.exterior, *p.interiors]:
            cs = list(ring.coords); c.move_to(*cs[0])
            for q in cs[1:]: c.line_to(*q)
            c.close_path()
        c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); c.set_source_rgb(*SR.hexrgb(HEX[r['col']])); c.fill()
Image.frombuffer("RGBA", (W, H), bytes(surf.get_data()), "raw", "BGRA", 0, 1).convert("RGB").save(
    'out/01_back-scene/HAKI_jacket_01_back-scene_FLAT-ART_for-auto-digitize.png', dpi=(ppm*25.4, ppm*25.4))

# ---- mockup vs Rev E
m = Image.open('flat.png').convert('RGB').crop((870, 140, 1730, 1010)); p = Image.open('sr_back_4.png').convert('RGB'); Hh = 1400
m = m.resize((int(m.width*Hh/m.height), Hh), Image.LANCZOS); p = p.resize((int(p.width*Hh/p.height), Hh), Image.LANCZOS)
out = Image.new('RGB', (m.width+p.width+60, Hh+90), 'white'); out.paste(m, (20, 70)); out.paste(p, (m.width+40, 70))
dr = ImageDraw.Draw(out); F = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 34)
dr.text((20, 15), 'Mockup', fill=(30, 30, 30), font=F); dr.text((m.width+40, 15), 'Rev E stitch-out preview (back panel, Drum Island M)', fill=(30, 30, 30), font=F)
out.save('out/01_back-scene/HAKI_jacket_01_back-scene_MOCKUP-vs-RevE.jpg', quality=90)

# ---- thread chart per v2 stitch file
for f_ in sorted(glob.glob('out/**/*_v2.pes', recursive=True) + glob.glob('out/01_back-scene/splits/*.pes')):
    pt = pe.read(f_); lines = [os.path.basename(f_).replace('.pes', ''), "stop  thread", "-" * 60]
    for i, th in enumerate(pt.threadlist, 1):
        lines.append(f"{i:>3}   {th.hex_color()}  {th.description}")
    open(f_.replace('.pes', '_thread-chart.txt'), 'w').write("\n".join(lines) + "\n")

# ---- package
PKG = 'out/pkg'; shutil.rmtree(PKG, ignore_errors=True); os.makedirs(f'{PKG}/elements')
for e in ('01_back-scene', '02_chest-branch', '03_chest-pine', '04_lower-bamboo'):
    shutil.copytree(f'out/{e}', f'{PKG}/elements/{e}', ignore=shutil.ignore_patterns('summary.json'))
for pdf in glob.glob('out/HAKI_Drum-Island*.pdf'): shutil.copy(pdf, PKG)
for z in glob.glob('out/*.zip'): os.remove(z)
for old in glob.glob('out/HAKI_plum-pine-jacket_TECHPACK_RevD.pdf'): os.remove(old)
subprocess.run(f'cd {PKG} && zip -qr ../HAKI_Drum-Island_plum-pine_RevE_files.zip .', shell=True)
print('finished', os.path.getsize('out/HAKI_Drum-Island_plum-pine_RevE_files.zip') // 1e6, 'MB')
