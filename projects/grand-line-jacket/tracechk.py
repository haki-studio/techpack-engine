import glcore, pickle, numpy as np
from PIL import Image
import stitchrender as SR, closereg as CR
import closetrace as CT
from motifs2 import HEX
D=pickle.load(open('closetrace.pkl','rb'))
for P,bb in (("FR",(-300,60,-5,340)),("FL",(5,80,300,345))):
    st=SR.render(D[P]["regions"],bb,3.0,base=glcore.FABRIC)
    cx,cy,_=CT.fit(P); B=Image.open(CT.FILES[P]).convert("RGB")
    W,H=st.size; XX,YY=np.meshgrid(bb[0]+(np.arange(W)+.5)/3,bb[1]+(np.arange(H)+.5)/3)
    from scipy import ndimage as ndi
    A=np.array(B).astype(float); U=(XX-cx[0])/cx[1]; V=(YY-cy[0])/cy[1]
    w=np.stack([ndi.map_coordinates(A[...,k],[V,U],order=1,mode='constant',cval=30) for k in range(3)],-1).astype('uint8')
    o=Image.new('RGB',(W*2+10,H),'white'); o.paste(Image.fromarray(w),(0,0)); o.paste(st,(W+10,0)); o.save(f'out/trace_{P}.png')
