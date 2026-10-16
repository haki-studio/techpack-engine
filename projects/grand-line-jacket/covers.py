"""cover_front.png / cover_back.png: technical flat (size M) with the stitch render of the front scene in place."""
import glcore
import pickle, cairosvg, io
from PIL import Image, ImageFilter
from shapely import affinity
import techflat as TF, stitchrender as SR
F = TF.Flat("M"); b = TF.bounds_front(F); ppm = 3.0
D = pickle.load(open("front_M.pkl", "rb"))
def flat_png(body):
    TF.K = 1.0 / ppm * 2.2
    W, H = b[2]-b[0]+20, b[3]-b[1]+20
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{b[0]-10} {b[1]-10} {W} {H}" width="{int(W*ppm)}" height="{int(H*ppm)}"><rect x="{b[0]-10}" y="{b[1]-10}" width="{W}" height="{H}" fill="#fff"/>{body}</svg>'
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")
def emb_layer(vis, dy):
    rr = SR.Renderer(b[0]-10, b[1]-10, b[2]+10, b[3]+10, ppm)
    for r in vis: rr.region(dict(r, geom=affinity.translate(r["geom"], 0, dy)))
    im = rr.image(); a = im.split()[3]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(a.point(lambda v: int(v*0.5))); sh = sh.filter(ImageFilter.GaussianBlur(1.2))
    base = Image.new("RGBA", im.size, (0, 0, 0, 0)); base.paste(sh, (1, 2))
    return Image.alpha_composite(base, im)
TF.SH = glcore.FABRIC
fr = flat_png(TF.draw_front(F)); fr = Image.alpha_composite(fr, emb_layer(D["FR"] + D["FL"], F.fnd))
fr.convert("RGB").save("cover_front.png")
flat_png(TF.draw_back(F)).convert("RGB").save("cover_back.png"); print(fr.size)
