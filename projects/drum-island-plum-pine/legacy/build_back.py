import os, sys, pickle, importlib
S = float(sys.argv[1]); tag = sys.argv[2]
os.environ['BACK_S'] = str(S)
import back, render
from shapely.geometry import box
clip = box(0, 0, back.W_A, back.H_A)
vis = back.build(clip)
pickle.dump({"vis": vis, "W": back.W_A, "H": back.H_A, "S": S}, open(f'back_{tag}.pkl', 'wb'))
stack = [(f"{z:03d}", col, g) for z, col, g, role in vis]
svg = render.stack_svg(stack, back.W_A, back.H_A, bg='#D9C4A0')
render.png(svg, f'back_{tag}_prev.png', 1700)
print(tag, back.W_A, back.H_A, len(vis))
