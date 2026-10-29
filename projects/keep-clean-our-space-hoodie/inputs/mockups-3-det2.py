import numpy as np, json
from PIL import Image, ImageDraw
from scipy import ndimage as nd
im=np.array(Image.open('/mnt/c/Users/devin/Desktop/HakiStop/Designs/Playtime/Keep Clean Our Space/Mockups 3.png').convert('RGB')).astype(float)
g=im.mean(2); bg=nd.median_filter(g,size=21)
dark=nd.binary_fill_holes(nd.binary_closing(g<90,iterations=6))
lab,n=nd.label(dark); sz=nd.sum(dark,lab,range(1,n+1)); gm=np.isin(lab,np.argsort(sz)[-2:]+1)
gm=nd.binary_erosion(gm,iterations=4)
sat=im.max(2)-im.min(2)
seed=(g>150)&(g-bg>70)&gm&(sat<70)
reg=(g-bg>35)&gm
l2,n2=nd.label(reg)
ids=np.unique(l2[seed]); ids=ids[ids>0]
objs=nd.find_objects(l2)
out=[]
for i in ids:
    s=objs[i-1]; h=s[0].stop-s[0].start; w=s[1].stop-s[1].start
    if max(h,w)>22: continue
    m=l2[s]==i; cy,cx=nd.center_of_mass(m)
    out.append(dict(x=round(cx+s[1].start,1),y=round(cy+s[0].start,1),w=int(w),h=int(h),area=int(m.sum()),peak=int(g[s][m].max())))
json.dump(out,open('stars.json','w'))
print(len(out)); import collections; print(collections.Counter(max(o['w'],o['h']) for o in out))
o=Image.fromarray(im.astype(np.uint8)); d=ImageDraw.Draw(o)
for s in out: d.ellipse((s['x']-9,s['y']-9,s['x']+9,s['y']+9),outline=(255,0,0) if max(s['w'],s['h'])>=6 else (0,255,0),width=2)
o.save('ov.png')
o.crop((50,30,1180,1220)).save('ovf.png'); o.crop((1200,30,2350,1220)).save('ovb.png')
