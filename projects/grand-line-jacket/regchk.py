import glcore, numpy as np, closereg as CR, mockmap as MM
from PIL import Image
bb=(-300,-60,300,480); ppm=2.0
mk=np.array(MM.warp(bb,ppm)).astype(float)
out=mk.copy()
for P,xs in (("FR",(-300,0)),("FL",(0,300))):
    a,v=CR.warp_mm(P,bb,ppm)
    W=a.shape[1]; X=np.arange(W)/ppm+bb[0]; m=v&((X>=xs[0])&(X<xs[1]))[None,:]
    out[m]=a[m]
Image.fromarray(np.concatenate([mk,out,(0.5*mk+0.5*out)],1).astype('uint8')).save('out/reg_check.png')
