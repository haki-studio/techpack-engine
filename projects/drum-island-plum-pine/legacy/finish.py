import pickle, cairocffi as cairo, os, shutil, glob, subprocess
from PIL import Image, ImageDraw, ImageFont
from shapely.ops import unary_union
from motifs2 import HEX
import stitchrender as SR
d=pickle.load(open('back2_vis.pkl','rb')); vb=d['back']
ub=unary_union([r['geom'] for r in vb]).bounds
ppm=6.0; x0,y0=ub[0]-4,ub[1]-4; W=int((ub[2]-ub[0]+8)*ppm); H=int((ub[3]-ub[1]+8)*ppm)
surf=cairo.ImageSurface(cairo.FORMAT_RGB24,W,H); c=cairo.Context(surf); c.set_antialias(cairo.ANTIALIAS_NONE)
c.set_source_rgb(1,1,1); c.paint(); c.scale(ppm,ppm); c.translate(-x0,-y0)
for r in vb:
    for p in SR.polys(r['geom']):
        for ring in [p.exterior,*p.interiors]:
            cs=list(ring.coords); c.move_to(*cs[0])
            for q in cs[1:]: c.line_to(*q)
            c.close_path()
        c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); c.set_source_rgb(*SR.hexrgb(HEX[r['col']])); c.fill()
Image.frombuffer("RGBA",(W,H),bytes(surf.get_data()),"raw","BGRA",0,1).convert("RGB").save(
    'out/01_back-scene/HAKI_jacket_01_back-scene_FLAT-ART_for-auto-digitize.png', dpi=(ppm*25.4,ppm*25.4))
m=Image.open('flat.png').convert('RGB').crop((870,140,1730,1010)); p=Image.open('sr_back_4.png').convert('RGB'); Hh=1400
m=m.resize((int(m.width*Hh/m.height),Hh),Image.LANCZOS); p=p.resize((int(p.width*Hh/p.height),Hh),Image.LANCZOS)
out=Image.new('RGB',(m.width+p.width+60,Hh+90),'white'); out.paste(m,(20,70)); out.paste(p,(m.width+40,70))
dr=ImageDraw.Draw(out); F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',34)
dr.text((20,15),'Mockup',fill=(30,30,30),font=F); dr.text((m.width+40,15),'Rev D stitch-out preview (back panel)',fill=(30,30,30),font=F)
for f_ in glob.glob('out/01_back-scene/*MOCKUP-vs-*'): os.remove(f_)
out.save('out/01_back-scene/HAKI_jacket_01_back-scene_MOCKUP-vs-RevD.jpg',quality=90)
# DST preview render
import pyembroidery as pe
pt=pe.read('out/01_back-scene/HAKI_jacket_01_back-scene_DRAFT.pes'); ex=pt.extents(); s=0.4
im=Image.new('RGB',(int((ex[2]-ex[0])*s)+20,int((ex[3]-ex[1])*s)+20),(215,194,156)); dd=ImageDraw.Draw(im)
cols=[t.hex_color() for t in pt.threadlist]; ci=0; prev=None
for x,y,cmd in pt.stitches:
    k=cmd&pe.COMMAND_MASK; P=((x-ex[0])*s+10,(y-ex[1])*s+10)
    if k==pe.STITCH:
        if prev: dd.line([prev,P],fill=cols[min(ci,len(cols)-1)],width=1)
        prev=P
    elif k==pe.COLOR_CHANGE: ci+=1; prev=None
    else: prev=None if k==pe.TRIM else P
im.save('out/01_back-scene/HAKI_jacket_01_back-scene_DRAFT_preview.png')
shutil.rmtree('out/pkg', ignore_errors=True); os.makedirs('out/pkg/elements')
for e in ('01_back-scene','02_chest-branch','03_chest-pine','04_lower-bamboo'):
    shutil.copytree(f'out/{e}', f'out/pkg/elements/{e}', ignore=shutil.ignore_patterns('summary.json'))
shutil.copy('out/HAKI_plum-pine-jacket_TECHPACK_RevD.pdf','out/pkg/')
for z in glob.glob('out/*_files.zip'): os.remove(z)
subprocess.run('cd out/pkg && zip -qr ../HAKI_plum-pine-jacket_TECHPACK_RevD_files.zip .', shell=True)
print('finished')
