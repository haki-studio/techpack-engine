import pickle, sys, cairosvg, fbcore
from motifs2 import HEX
from render import geom_to_path
from PIL import Image
regs = pickle.load(open(sys.argv[1], "rb"))
if isinstance(regs, dict): regs = regs[sys.argv[3]]
x0, y0, x1, y1 = [float(v) for v in sys.argv[2].split(",")]
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{(x1-x0)*3}" height="{(y1-y0)*3}"><rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="{fbcore.FABRIC}"/>']
for r in regs: o.append(f'<path d="{geom_to_path(r["geom"])}" fill="{HEX[r["col"]]}" fill-rule="evenodd"/>')
o.append("</svg>")
cairosvg.svg2png(bytestring="".join(o).encode(), write_to=sys.argv[4], output_width=1400)
