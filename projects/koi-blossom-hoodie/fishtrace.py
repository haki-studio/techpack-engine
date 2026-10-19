"""Tetra fish traced from inputs/reference_fish.png (Rev C, review item 5) — replaces the typed polygons of kb_fish.py.

The template = the lower-middle fish of the founder's reference (clean side view, belly down, swimming left; snout and
tail-lobe tip read on the image: RF_SNOUT, RF_TAILTIP). Its pixels give everything:
  silhouette    colour distance from the reference background (own threshold, not refmask's)
  facets        every pixel coloured by its nearest fish thread (as rendered), mode-filtered, islands < 0.5 mm2 (at the stitched size) given to their neighbours,
                anti-aliased edge pixels given to the interior tone -> one polygon per facet (the reference's cel-shaded
                facets: lavender-blue flank, pale ice highlights, lavender shadow facets, cyan line, red stripe, eye)
  parts         body core = the silhouette opened by 7 % of the length; tail = beyond the peduncle; fins = the rest
  stitching     body facets: tatami at +-20 deg to the body axis (lavender) / satin (highlights, cyan, red: turning,
                along the body); tail: radial from the peduncle; fins: radial from the fin root; eye: satin dot.
place(pose, unit): the template laid onto a fish pose (centre mm, heading deg toward the head, length mm) with the belly
toward the garment's lower side — the poses come from the mockup pixels (refmask.fish_poses) at 0.82 x the mockup length.
usage: python3 fishtrace.py   -> trace/fish_template.pkl + out/fish_trace.png"""
import math, pickle, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity

RF_SNOUT, RF_TAILTIP = (740.0, 930.0), (967.0, 809.0)
FAB_GARMENT = np.array([31, 42, 64], float)            # kbcore.FABRIC
# fish threads (hex from kbcore.KB_PAL) — nearest by Lab distance
FISH_THREADS = ["kb_ice", "kb_cream", "kb_slate", "kb_cyan", "kb_red", "kb_ink", "kb_white"]

def _lab(rgb):
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

def hexrgb(h): h = h.lstrip("#"); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]

def polys(g): return [p for p in (g.geoms if hasattr(g, "geoms") else [g]) if p.geom_type == "Polygon" and not p.is_empty]

def mask_poly(m, simp=0.6):
    """bool mask (template px) -> polygon (union of row runs, lightly smoothed)"""
    from shapely.geometry import box as B
    bx = []
    for i in np.nonzero(m.any(1))[0]:
        d = np.diff(np.r_[0, m[i].astype(int), 0]); st = np.nonzero(d == 1)[0]; en = np.nonzero(d == -1)[0]
        bx += [B(a, i, b, i + 1) for a, b in zip(st, en)]
    if not bx: return Polygon()
    g = unary_union(bx).buffer(0.5, join_style=2).buffer(-0.5, join_style=2)
    return g.buffer(0.9, join_style=1).buffer(-0.9, join_style=1).simplify(simp).buffer(0)

def trace(L_mm=57.0):
    import kbcore
    im = np.array(Image.open("inputs/reference_fish.png").convert("RGB")).astype(float)
    bg = np.median(im.reshape(-1, 3), axis=0)
    m = np.sqrt(((im - bg) ** 2).sum(-1)) > 50
    m = ndi.binary_fill_holes(ndi.binary_closing(ndi.binary_opening(m, iterations=1), iterations=2))
    lab, _ = ndi.label(m); mid = (np.array(RF_SNOUT) + np.array(RF_TAILTIP)) / 2; sil = lab == lab[int(mid[1]), int(mid[0])]
    ys, xs = np.nonzero(sil); y0, y1, x0, x1 = ys.min() - 4, ys.max() + 5, xs.min() - 4, xs.max() + 5
    sil = sil[y0:y1, x0:x1]; px = im[y0:y1, x0:x1]
    Lr = math.hypot(RF_SNOUT[0] - RF_TAILTIP[0], RF_SNOUT[1] - RF_TAILTIP[1]); ppm_t = Lr / L_mm   # template px per stitched mm
    # nearest fish thread per pixel (reference render lifted to the garment fabric level)
    lifted = px                     # nearest thread to the reference colour as rendered (no lift: keeps the lavender hue)
    T = np.array([hexrgb(kbcore.KB_PAL[k][0]) for k in FISH_THREADS], float)
    d = ((_lab(lifted)[..., None, :] - _lab(T)[None, None]) ** 2).sum(-1)
    cls = d.argmin(-1)
    # eye: the darkest blob in the front 20 % of the fish; dark pixels elsewhere are edge anti-aliasing / shadow -> slate
    sn = np.array(RF_SNOUT) - [x0, y0]; tt = np.array(RF_TAILTIP) - [x0, y0]; e = (sn - tt) / Lr
    YY, XX = np.mgrid[0:sil.shape[0], 0:sil.shape[1]]
    t = ((XX - tt[0]) * e[0] + (YY - tt[1]) * e[1]) / Lr               # 0 tail tip .. 1 snout
    ink = FISH_THREADS.index("kb_ink"); sl = FISH_THREADS.index("kb_slate")
    eye_m = sil & (cls == ink) & (t > 0.80); el, en = ndi.label(eye_m)
    if en: eye_m = el == (1 + int(np.argmax(ndi.sum(eye_m, el, range(1, en + 1)))))
    cls = np.where((cls == ink) & ~eye_m, sl, cls)
    # anti-aliased edge (outer 1 px): interior tone
    edge = sil & ~ndi.binary_erosion(sil, iterations=3)          # the render's blur mixes ~3 px of background into the rim
    core_px = sil & ~edge
    idx = ndi.distance_transform_edt(~core_px, return_distances=False, return_indices=True)
    cls = np.where(edge, cls[idx[0], idx[1]], cls)
    # mode filter + small islands (< 0.5 mm2 at the stitched size) to the neighbours
    oh = np.stack([ndi.uniform_filter((cls == k).astype(float), 3) for k in range(len(FISH_THREADS))], -1)
    cls = np.where(sil, oh.argmax(-1), -1); cls = np.where(eye_m, ink, cls)
    min_px = 0.5 * ppm_t ** 2
    for _ in range(4):
        bad = np.zeros_like(sil)
        for k in range(len(FISH_THREADS)):
            mk = cls == k; l2, n2 = ndi.label(mk)
            if n2 == 0: continue
            sz = ndi.sum(mk, l2, range(1, n2 + 1)); small = np.isin(l2, 1 + np.nonzero(sz < min_px)[0])
            if k == ink: small &= ~eye_m
            bad |= small
        if not bad.any(): break
        src = sil & ~bad; idx = ndi.distance_transform_edt(~src, return_distances=False, return_indices=True)
        cls = np.where(sil, cls[idx[0], idx[1]], -1)
    # parts: body core, tail, fins
    r_open = max(2, int(0.07 * Lr))
    core = ndi.binary_opening(sil & (t > 0.20), structure=np.ones((3, 3)), iterations=r_open // 2)
    cl_, cn = ndi.label(core)
    if cn > 1: core = cl_ == (1 + int(np.argmax(ndi.sum(core, cl_, range(1, cn + 1)))))
    core = ndi.binary_dilation(core, iterations=2) & sil
    # peduncle: narrowest part of the silhouette between t 0.12 and 0.40
    lat = -(XX - tt[0]) * e[1] + (YY - tt[1]) * e[0]
    bins = np.linspace(0.10, 0.42, 17); wid = []
    for a, b in zip(bins[:-1], bins[1:]):
        s_ = sil & (t >= a) & (t < b); wid.append(np.ptp(lat[s_]) if s_.sum() > 3 else 1e9)
    t_ped = float((bins[int(np.argmin(wid))] + bins[int(np.argmin(wid)) + 1]) / 2)
    tail = sil & (t < t_ped)
    body = sil & ~tail & core
    fins = sil & ~tail & ~body
    ped_c = tt + e * Lr * t_ped
    ped_c = ped_c + np.array([-e[1], e[0]]) * float(np.median(lat[sil & (np.abs(t - t_ped) < 0.02)]))
    off = np.array([x0, y0], float)
    regs = []
    sil_poly = mask_poly(sil)
    for part, pm in (("tail", tail), ("fin", fins), ("body", body)):
        pl, pn = ndi.label(pm)
        for j in range(1, pn + 1):
            pj = pl == j
            if pj.sum() < min_px: continue
            root = None
            if part == "fin":            # fin root = the fin pixel nearest the body core centre line
                fy, fx = np.nonzero(pj); bd = ndi.distance_transform_edt(~body)
                k_ = np.argmin(bd[fy, fx]); root = (float(fx[k_]), float(fy[k_]))
            cj = cls.copy()
            if part in ("tail", "fin"):    # translucent fins over the dark render background read slate; the thread is opaque: lavender
                cj = np.where(cj == sl, FISH_THREADS.index("kb_cream"), cj)
            for k in range(len(FISH_THREADS)):
                mk = pj & (cj == k)
                if mk.sum() < min_px * (0.4 if FISH_THREADS[k] == "kb_ink" else 1): continue
                g = mask_poly(mk).intersection(sil_poly.buffer(0.3)).buffer(0)
                if g.is_empty: continue
                regs.append(dict(col=FISH_THREADS[k], geom=g, part=part, root=root, px=int(mk.sum())))
    tpl = dict(regs=regs, snout=(sn).tolist(), tail=(tt).tolist(), L=Lr, ped=ped_c.tolist(), t_ped=t_ped, sil=sil_poly,
               offset=off.tolist(), counts={FISH_THREADS[k]: int((cls == k).sum()) for k in range(len(FISH_THREADS))})
    return tpl

TPL = None
def template():
    global TPL
    if TPL is None: TPL = pickle.load(open("trace/fish_template.pkl", "rb"))
    return TPL

GRP = {"kb_cream": "FI-shade", "kb_slate": "FI-shade", "kb_ice": "FI", "kb_white": "FI-ring", "kb_cyan": "FI-line", "kb_red": "FI-red", "kb_ink": "FI-eye"}
SUB = {"kb_cream": 3.0, "kb_slate": 3.2, "kb_ice": 3.4, "kb_white": 3.5, "kb_cyan": 4.0, "kb_red": 4.1, "kb_ink": 6.0}

def place(pose, L, unit=None):
    """template regions laid onto a fish pose: centre pose['c'] (mm), heading pose['ang'] (deg, toward the head), length L"""
    tp = template(); sn, tt = np.array(tp["snout"]), np.array(tp["tail"]); Lr = tp["L"]; s = L / Lr
    e_t = (sn - tt) / Lr; a_t = math.degrees(math.atan2(e_t[1], e_t[0]))
    a = pose["ang"]; c = np.array(pose["c"], float); mid_t = (sn + tt) / 2
    # belly: the template's belly is image-down; on the garment the belly goes to the lower side as well
    n_t = np.array([-e_t[1], e_t[0]]); belly_t = 1 if n_t[1] > 0 else -1
    e = np.array([math.cos(math.radians(a)), math.sin(math.radians(a))]); n = np.array([-e[1], e[0]]); belly = 1 if n[1] >= 0 else -1
    mirror = belly != belly_t
    def X(g):
        g = affinity.translate(g, -mid_t[0], -mid_t[1]); g = affinity.rotate(g, -a_t, origin=(0, 0))   # head along +x
        if mirror: g = affinity.scale(g, 1, -1, origin=(0, 0))
        g = affinity.scale(g, s, s, origin=(0, 0)); g = affinity.rotate(g, a, origin=(0, 0))
        return affinity.translate(g, c[0], c[1])
    def XP(p): q = X(Point(p)); return (q.x, q.y)
    out = []
    for r in tp["regs"]:
        g = X(r["geom"]).buffer(0)
        if g.is_empty: continue
        col = r["col"]; grp = GRP[col]; sub = SUB[col]
        if r["part"] == "tail":
            st, ang, grp, sub = "satin", ("radial",) + XP(tp["ped"]), "FI-tail", 1.0
        elif r["part"] == "fin":
            st, ang, grp, sub = "satin", ("radial",) + XP(r["root"]), "FI-fin", 1.2
        elif col in ("kb_cream", "kb_slate"):
            st, ang = "tatami", a + (20.0 if col == "kb_cream" else -20.0)
        else:
            st, ang = "satin", "auto"
        # stitched = traced: inset by the engine's pull compensation (0.15-0.2 mm per side)
        g = g.buffer(-0.15).buffer(0) if g.area > 3 else g
        if col == "kb_ink": g = g.union(Point(g.centroid.x, g.centroid.y).buffer(0.75)).buffer(0)      # eye >= 1.5 mm
        if g.is_empty: continue
        out.append(dict(col=col, geom=g, st=st, ang=ang, grp=grp, sub=sub, unit=unit))
    sil = X(tp["sil"]).buffer(0)
    return out, sil

if __name__ == "__main__":
    import kbcore
    tp = trace(); pickle.dump(tp, open("trace/fish_template.pkl", "wb")); TPL = tp
    # overlay: reference crop | traced facets (thread colours), 4x
    im = Image.open("inputs/reference_fish.png").convert("RGB"); ox, oy = tp["offset"]; sc = 4
    W = int(tp["sil"].bounds[2] + 6); H = int(tp["sil"].bounds[3] + 6)
    a = im.crop((int(ox), int(oy), int(ox) + W, int(oy) + H)).resize((W * sc, H * sc), Image.LANCZOS)
    b = Image.new("RGB", a.size, kbcore.FABRIC); d = ImageDraw.Draw(b)
    for r in sorted(tp["regs"], key=lambda r: SUB[r["col"]]):
        for p in polys(r["geom"]):
            d.polygon([(x * sc, y * sc) for x, y in p.exterior.coords], fill=kbcore.KB_PAL[r["col"]][0], outline=(20, 20, 30))
            for h in p.interiors: d.polygon([(x * sc, y * sc) for x, y in h.coords], fill=kbcore.FABRIC)
    px, py = tp["ped"]; d.ellipse([px * sc - 5, py * sc - 5, px * sc + 5, py * sc + 5], outline="yellow", width=2)
    sh = Image.new("RGB", (a.width * 2 + 10, a.height), "white"); sh.paste(a, (0, 0)); sh.paste(b, (a.width + 10, 0)); sh.save("out/fish_trace.png")
    print("fish template: regions", len(tp["regs"]), "L px", round(tp["L"]), "peduncle t", round(tp["t_ped"], 2), tp["counts"],
          {p: sum(1 for r in tp["regs"] if r["part"] == p) for p in ("body", "tail", "fin")})
