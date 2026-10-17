"""Cache the mockup warped into every piece's mm space at 3 px/mm (size M, with bleed past the side seams) -> warps_M.pkl"""
import cfcore, pickle
import mockmap as MM, keepout as KO
W = {}
for P in cfcore.PIECES:
    b = KO.panel("M", P).bounds
    b = {"BK": (b[0]-25, b[1]-5, b[2]+25, b[3]+5), "FL": (b[0]-5, b[1]-5, b[2]+25, b[3]+5),
         "FR": (b[0]-25, b[1]-5, b[2]+5, b[3]+5)}.get(P, (b[0]-5, b[1]-5, b[2]+5, b[3]+5))
    W[P] = (b, MM.warp(P, b, 3.0, up=4)); print(P, W[P][1].shape, flush=True)
pickle.dump(W, open("warps_M.pkl", "wb"))
