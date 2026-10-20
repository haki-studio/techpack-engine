import numpy as np, sys
from PIL import Image
a=np.array(Image.open('inputs/front.png').convert('RGB')).astype(float)
r,g,b=a[...,0],a[...,1],a[...,2]
blue=(b-r>60).astype(float); black=(r+g+b<200).astype(float)
def purity(m, p, ox, oy):
    H,W=m.shape; ys=np.arange(oy,H-p,p); xs=np.arange(ox,W-p,p); tot=0; n=0
    for y in ys:
        for x in xs:
            c=m[int(round(y))+1:int(round(y+p))-1, int(round(x))+1:int(round(x+p))-1]
            if c.size==0: continue
            f=c.mean(); tot+=max(f,1-f); n+=1
    return tot/n
def fit(m, lo, hi):
    best=None
    for p in np.arange(lo,hi,0.05):
        for ox in np.arange(0,p,p/8):
            for oy in np.arange(0,p,p/8):
                s=purity(m,p,ox,oy)
                if best is None or s>best[0]: best=(s,p,ox,oy)
    return best
print('cloud L', fit(blue[930:1080,330:700],7,10))
print('cloud R', fit(blue[930:1080,780:1060],7,10))
print('bird', fit(black[620:800,445:650],3.5,5.5))
