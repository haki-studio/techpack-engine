import rbcore, numpy as np, sys, refmask, qa_gates as Q, pickle, shapely
from PIL import Image
T=np.load('trace_M.npz'); PPM=4
RAW=refmask.from_inputs('F'); REF=refmask.reference(RAW,PPM,'F')
A=pickle.load(open('art_M.pkl','rb'))
bb=tuple(T['bbF'])
fams={'cream':["rb_cream","rb_white"],'red':["rb_red","rb_crimson"],'black':["rb_black"]}
out=[]
for spec in sys.argv[2:]:
    fam,x,y=spec.split(','); x=float(x);y=float(y)
    r0=int((y-12-bb[1])*PPM); c0=int((x-12-bb[0])*PPM); h=w=int(24*PPM)
    xs=bb[0]+(c0+np.arange(w)+0.5)/PPM; ys=bb[1]+(r0+np.arange(h)+0.5)/PPM; X,Y=np.meshgrid(xs,ys)
    from shapely.ops import unary_union
    from shapely.geometry import box
    bx=box(x-12,y-12,x+12,y+12)
    g=unary_union([r['geom'] for P in ('FL','FR') for r in A[P] if r['col'] in fams[fam] and r['geom'].intersects(bx)])
    b=shapely.contains_xy(g,X,Y); a=REF[fam][r0:r0+h,c0:c0+w]
    print(spec,'ref px',a.sum(),'art px',b.sum(),'iou',(a&b).sum()/(a|b).sum())
    im=np.zeros((h,w,3),np.uint8); im[a]=(0,160,255); im[b]=(255,80,80); im[a&b]=(255,255,255)
    out.append(np.kron(im,np.ones((4,4,1),np.uint8)))
Image.fromarray(np.concatenate(out,1)).save(sys.argv[1])
