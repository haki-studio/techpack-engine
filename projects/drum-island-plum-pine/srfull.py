import pickle, time, sys
import stitchrender as SR
import back2 as B
from PIL import Image, ImageDraw
d=pickle.load(open('back2_vis.pkl','rb'))
ppm=float(sys.argv[1]) if len(sys.argv)>1 else 4
t=time.time()
x0,y0,x1,y1=-305,-25,305,590
img=SR.render(d['back'], (x0,y0,x1,y1), ppm)
# mask to the panel shape
mask=Image.new("L", img.size, 0); dr=ImageDraw.Draw(mask)
dr.polygon([((x-x0)*ppm,(y-y0)*ppm) for x,y in B.PANEL.exterior.coords], fill=255)
bg=Image.new("RGB", img.size, (255,255,255)); bg.paste(img,(0,0),mask)
dr=ImageDraw.Draw(bg); dr.line([((x-x0)*ppm,(y-y0)*ppm) for x,y in B.PANEL.exterior.coords], fill=(90,70,50), width=2)
bg.save(f'sr_back_{int(ppm)}.png'); print('back', time.time()-t, bg.size)
