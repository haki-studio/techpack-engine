import sys; sys.argv=['x']
import glcore
src=open('scene.py').read().split('# ---------------------------------------------------------------- banks: broad')[0]
exec(src)
for C in BANKS: print([round(v) for v in C.bounds], round(C.area))
