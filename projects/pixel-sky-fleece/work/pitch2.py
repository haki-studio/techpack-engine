import numpy as np
from PIL import Image
a=np.array(Image.open('inputs/front.png').convert('RGB')).astype(float)
r,g,b=a[...,0],a[...,1],a[...,2]
blue=(b-r>60).astype(float); black=(r+g+b<200).astype(float)
def edges(m, axis):
    d=np.abs(np.diff(m,axis=axis)); pos=np.argwhere(d>0.5)
    return pos[:,axis]+0.5
def curve(m, lo, hi, axis):
    e=edges(m,axis); out=[]
    for p in np.arange(lo,hi,0.02):
        z=np.exp(2j*np.pi*e/p).mean(); out.append((abs(z),p,(np.angle(z)/(2*np.pi)*p)%p))
    return sorted(out)[::-1][:5]
for nm,m,lo,hi in [('cloudL',blue[930:1080,330:700],5,12),('cloudR',blue[930:1080,780:1060],5,12),('bird',black[620:800,445:650],3,9)]:
    print(nm,'x',[(round(s,3),round(p,2),round(o,2)) for s,p,o in curve(m,lo,hi,1)])
    print(nm,'y',[(round(s,3),round(p,2),round(o,2)) for s,p,o in curve(m,lo,hi,0)])
