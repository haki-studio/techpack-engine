import numpy as np
from PIL import Image
from scipy import ndimage as ndi
for n in ('right','left'):
    a=np.array(Image.open(f'inputs/closeups/closeup_front_{n}.png').convert('RGB')).astype(float)
    l=a.mean(2)
    # horizon: row with max vertical gradient in central columns between y 400..900
    g=np.abs(np.diff(ndi.gaussian_filter(l,2),axis=0))[:, 300:800].mean(1)
    y=np.argmax(g[400:900])+400
    # stars: gold blobs in sky above horizon-60
    sky=(l>150)&(a[...,0]>a[...,2]+20)
    sky[y-40:]=False
    lab,k=ndi.label(sky); cs=ndi.center_of_mass(sky,lab,range(1,k+1)); sz=ndi.sum(sky,lab,range(1,k+1))
    st=[(round(c[1]),round(c[0]),int(s)) for c,s in zip(cs,sz) if s>8]
    # sun: brightest blob near horizon
    sun=np.unravel_index(np.argmax(ndi.gaussian_filter(l,8)[y-80:y+5]), l[y-80:y+5].shape)
    print(n,'horizon',y,'sun',(sun[1],sun[0]+y-80),'stars',len(st)); print(sorted(st,key=lambda s:-s[2])[:60])
