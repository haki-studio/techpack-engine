"""Garment views with the embroidery in place (stitch render on the technical flat, size M by default).
Front view: FR + FL on the front panels, the FRONT half of each sleeve warped onto the flat sleeve; back view: BK + the BACK
half of each sleeve. Flat coords (techflat): y from the HPS line, x + = viewer's right.
  front: viewer's left sleeve = wearer's right sleeve SR (front half = S01 x > 0); viewer's right = SL (front half = S02 x < 0)
  back:  viewer's left = SL (back half = S02 x > 0); viewer's right = SR (back half = S01 x < 0)
usage: views.front_view(art, ppm) / views.back_view(art, ppm) -> (PIL RGB, bbox in flat mm)"""
import cfcore
import io, math
import numpy as np
import cairosvg
from PIL import Image, ImageDraw, ImageFilter
from shapely import affinity
import techflat as TF, stitchrender as SR, keepout as KO

def _flat_png(body, b, ppm):
    W, H = b[2] - b[0], b[3] - b[1]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{b[0]} {b[1]} {W} {H}" width="{int(W*ppm)}" height="{int(H*ppm)}">'
           f'<rect x="{b[0]}" y="{b[1]}" width="{W}" height="{H}" fill="#fff"/>{body}</svg>')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")

def _layer(vis, b, ppm, dx=0.0, dy=0.0):
    rr = SR.Renderer(b[0], b[1], b[2], b[3], ppm)
    for r in vis: rr.region(dict(r, geom=affinity.translate(r["geom"], dx, dy)))
    im = rr.image(); a = im.split()[3]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(a.point(lambda v: int(v * 0.5))); sh = sh.filter(ImageFilter.GaussianBlur(1.2))
    base = Image.new("RGBA", im.size, (0, 0, 0, 0)); base.paste(sh, (1, 2))
    return Image.alpha_composite(base, im)

def _persp_coeffs(src, dst):
    """coefficients for PIL PERSPECTIVE mapping output (dst) points to input (src) points"""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()

def _sleeve_layer(F, art, P, view, side, b, ppm, size="M"):
    """the visible half of sleeve P rendered in pattern coords, then warped onto the flat sleeve on `side` (+1 viewer's right)"""
    g, mt = KO.pieces(size); h, Lu, W, Ww = mt["cap_h"], mt["Lu"], mt["W"], mt["Ww"]
    front_half_pos = (P == "SR")                      # S01 front half is x > 0, S02 front half is x < 0
    pos = front_half_pos if view == "front" else not front_half_pos
    vis = [r for r in art[P] if (r["geom"].centroid.x > 0) == pos]
    sb = (0, -h, W, Lu) if pos else (-W, -h, 0, Lu); sp_ = 4.0
    rr = SR.Renderer(sb[0], sb[1], sb[2], sb[3], sp_)
    for r in vis: rr.region(r)
    im = rr.image()
    Wp, Hp = im.size
    def pix(x, y): return ((x - sb[0]) * sp_, (y - sb[1]) * sp_)
    from scipy.ndimage import map_coordinates
    from shapely.geometry import LineString
    xs = 1 if pos else -1
    sl = KO.panel(size, P)
    ytab = np.linspace(-h, Lu, 200)
    def half(y):
        seg = sl.intersection(LineString([(-600, y), (600, y)]))
        if seg.is_empty: return 1.0
        bb = seg.bounds; return bb[2] if xs > 0 else -bb[0]
    xmax = np.array([max(1.0, half(y)) for y in ytab])
    sgn = 1 if side > 0 else -1
    spt = np.array([sgn * F.sp[0], F.sp[1]]); ua = np.array([sgn * F.ua[0], F.ua[1]])
    co = np.array([sgn * F.cuff_seam_out[0], F.cuff_seam_out[1]]); ci = np.array([sgn * F.cuff_seam_in[0], F.cuff_seam_in[1]])
    fr = h / (h + Lu)
    Wo, Ho = int((b[2] - b[0]) * ppm), int((b[3] - b[1]) * ppm)
    poly = F.sleeve(side); pb = poly.bounds
    c0, c1 = int((pb[0] - b[0]) * ppm), int((pb[2] - b[0]) * ppm); r0, r1 = int((pb[1] - b[1]) * ppm), int((pb[3] - b[1]) * ppm)
    cc, rr_ = np.meshgrid(np.arange(c0, c1), np.arange(r0, r1))
    X = b[0] + (cc + 0.5) / ppm; Y = b[1] + (rr_ + 0.5) / ppm
    d = co - spt; v = ((X - spt[0]) * d[0] + (Y - spt[1]) * d[1]) / (d @ d)
    v = np.clip(v, 0, 1)
    ox, oy = spt[0] + d[0] * v, spt[1] + d[1] * v
    t_ = np.clip(v / fr, 0, 1)
    ix = np.where(v < fr, spt[0] + (ua[0] - spt[0]) * t_, ua[0] + (ci[0] - ua[0]) * (v - fr) / (1 - fr))
    iy = np.where(v < fr, spt[1] + (ua[1] - spt[1]) * t_, ua[1] + (ci[1] - ua[1]) * (v - fr) / (1 - fr))
    ex, ey = ix - ox, iy - oy; u = np.clip(((X - ox) * ex + (Y - oy) * ey) / np.maximum(ex * ex + ey * ey, 1e-6), 0, 1)
    py_ = -h + v * (h + Lu); pxm = xs * u * np.interp(py_, ytab, xmax)
    src_c = (pxm - sb[0]) * sp_; src_r = (py_ - sb[1]) * sp_
    a = np.asarray(im).astype(np.float32); outa = np.zeros((Ho, Wo, 4), np.float32)
    for k in range(4):
        outa[r0:r1, c0:c1, k] = map_coordinates(a[..., k], [src_r, src_c], order=1, mode="constant")
    out = Image.fromarray(outa.clip(0, 255).astype(np.uint8), "RGBA")
    m = Image.new("L", (Wo, Ho), 0)
    ImageDraw.Draw(m).polygon([((x - b[0]) * ppm, (y - b[1]) * ppm) for x, y in poly.exterior.coords], fill=255)
    out.putalpha(Image.fromarray(np.minimum(np.array(out.split()[3]), np.array(m))))
    return out

def front_view(art, ppm=2.0, pieces=None):
    F = TF.Flat("M"); b = TF.bounds_front(F); b = (b[0] - 10, b[1] - 10, b[2] + 10, b[3] + 10)
    TF.K = 1.0 / ppm * 2.2; TF.SH = cfcore.FABRIC
    base = _flat_png(TF.draw_front(F), b, ppm)
    pcs = pieces or cfcore.PIECES
    body = [r for P in ("FR", "FL") if P in pcs for r in art[P]]
    base = Image.alpha_composite(base, _layer(body, b, ppm, 0, F.fnd))
    for P, side in (("SR", -1), ("SL", 1)):
        if P in pcs: base = Image.alpha_composite(base, _sleeve_layer(F, art, P, "front", side, b, ppm))
    return base.convert("RGB"), b

def back_view(art, ppm=2.0, pieces=None):
    F = TF.Flat("M"); b = TF.bounds_front(F); b = (b[0] - 10, b[1] - 10, b[2] + 10, b[3] + 10)
    TF.K = 1.0 / ppm * 2.2; TF.SH = cfcore.FABRIC
    base = _flat_png(TF.draw_back(F), b, ppm)
    pcs = pieces or cfcore.PIECES
    if "BK" in pcs: base = Image.alpha_composite(base, _layer(art["BK"], b, ppm, 0, F.bnd))
    for P, side in (("SL", -1), ("SR", 1)):
        if P in pcs: base = Image.alpha_composite(base, _sleeve_layer(F, art, P, "back", side, b, ppm))
    return base.convert("RGB"), b

if __name__ == "__main__":
    import pickle, sys
    size = sys.argv[1] if len(sys.argv) > 1 else "M"
    art = pickle.load(open(f"art_{size}.pkl", "rb"))
    fv, _ = front_view(art, 2.0); fv.save("cover_front.png")
    bv, _ = back_view(art, 2.0); bv.save("cover_back.png")
    print(fv.size, bv.size)
