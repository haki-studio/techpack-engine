import numpy as np, pixels as PX, mockmap as MM
lab=PX.labels()
def score(c, ox, oy, xr=(-230,230), yr=(330,430)):
    tot=n=0
    for y in np.arange(yr[0]+oy, yr[1], c):
        for x in np.arange(xr[0]+ox, xr[1], c):
            px0,py0=MM.Pinv(x,y); px1,py1=MM.Pinv(x+c,y+c)
            f,v=PX.frac(px0+0.5,py0+0.5,px1-0.5,py1-0.5,lab)
            if v<0.8: continue
            tot+=max(f[0],f[1]); n+=1
    return tot/max(n,1)
best=[]
for c in np.arange(4.6,5.8,0.1):
    b=max((score(c,ox,oy),ox,oy) for ox in np.arange(0,c,c/6) for oy in np.arange(0,c,c/6))
    best.append((round(b[0],4),round(c,2),round(b[1],2),round(b[2],2))); print(best[-1])
