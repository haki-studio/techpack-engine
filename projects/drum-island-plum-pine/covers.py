import pickle, cairosvg, io
from PIL import Image, ImageFilter
from shapely import affinity
import techflat as TF, stitchrender as SR
F = TF.Flat("M"); b = TF.bounds_front(F); ppm = 3.0
d = pickle.load(open('back2_vis.pkl', 'rb')); V = pickle.load(open('front_vis.pkl', 'rb'))
def flat_png(body):
    TF.K = 1.0 / ppm * 2.2
    W, H = b[2]-b[0]+20, b[3]-b[1]+20
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{b[0]-10} {b[1]-10} {W} {H}" width="{int(W*ppm)}" height="{int(H*ppm)}"><rect x="{b[0]-10}" y="{b[1]-10}" width="{W}" height="{H}" fill="#fff"/>{body}</svg>'
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")
def emb_layer(vis, dy):
    rr = SR.Renderer(b[0]-10, b[1]-10, b[2]+10, b[3]+10, ppm)
    for r in vis: rr.region(dict(r, geom=affinity.translate(r["geom"], 0, dy)))
    im = rr.image(); a = im.split()[3]
    sh = Image.new("RGBA", im.size, (40, 28, 18, 0)); sh.putalpha(a.point(lambda v: int(v*0.5))); sh = sh.filter(ImageFilter.GaussianBlur(1.2))
    base = Image.new("RGBA", im.size, (0, 0, 0, 0)); base.paste(sh, (1, 2))
    return Image.alpha_composite(base, im)
TFs = TF
fr = flat_png(TF.draw_front(F)); fr = Image.alpha_composite(fr, emb_layer([r for k in V for r in V[k]], F.fnd))
# re-draw zip + collar on top so the embroidery tucks under them
top = flat_png("")
fr.convert("RGB").save("cover_front.png")
bk = flat_png(TF.draw_back(F)); bk = Image.alpha_composite(bk, emb_layer(d["back"], F.bnd))
bk.convert("RGB").save("cover_back.png"); print(fr.size)
