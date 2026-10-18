import numpy as np
from PIL import Image
from scipy.cluster.vq import kmeans2
for n,box in (('right',(0,200,960,920)),('left',(330,170,1122,760))):
    a=np.array(Image.open(f'inputs/closeups/closeup_front_{n}.png').convert('RGB')).astype(float)[box[1]:box[3],box[0]:box[2]].reshape(-1,3)
    l=a@[0.3,0.59,0.11]; a=a[l>55]
    c,lab=kmeans2(a[::7],8,minit='++',seed=2); cnt=np.bincount(lab,minlength=8); o=np.argsort(-(c@[0.3,0.59,0.11]))
    print(n,' '.join('#%02X%02X%02X:%d'%(*c[i].astype(int),cnt[i]) for i in o))
