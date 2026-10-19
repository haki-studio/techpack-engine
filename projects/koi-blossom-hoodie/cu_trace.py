"""Trace motif structure from the close-up (inputs/closeup_mockup_koi.png) — LESSONS A12 + A13.

Rev A only looked at the close-up. Rev B takes from its pixels:
  * lilies (the 2 close-up flowers): every petal = a hand-placed lanceolate guide (tip point + width, read on gridded zooms)
    clipped to the TRACED silhouette (colour mask), stacked in the close-up's overlap order; tone regions inside every
    petal = the close-up's pixels clustered into 6 thread tones (k-means, mode-filtered), max 3 tones per petal
    (dark base -> ice/cream tip, cream edge highlights where the close-up has them); centre = traced deep-blue throat +
    traced cream anther knots (+ a few mid-blue stamen lines drawn from the throat to the knots).
  * koi (the 4 close-up koi): traced silhouette; red patches = traced red pixels (crisp, simplified to angular shapes,
    the 2 largest kept); fins = silhouette minus the opened body, tail = silhouette beyond the peduncle; grey shading =
    traced grey pixels on the body; eye position traced.
  * floating petals: the traced silhouettes of the 14 free petals in the close-up (shape library).
Everything is stored in close-up px with each motif's reference frame (flower centre + radius, koi head + tail tip);
scene.py maps a template onto its MOCKUP position (cu_register: positions from the mockup, structure from the close-up).
Output: trace/templates.pkl + out/trace_closeup.png (traced objects drawn over the close-up).
usage: python3 cu_trace.py"""
import pickle, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from shapely.geometry import Polygon, Point, box, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity

IM = np.array(Image.open("inputs/closeup_mockup_koi.png").convert("RGB")).astype(float)
H, W = IM.shape[:2]
SM = ndi.gaussian_filter(IM, (1.5, 1.5, 0))
LUM = SM.mean(2)
MASK = ndi.binary_fill_holes(ndi.binary_opening((LUM > 75) | ((SM[..., 2] - SM[..., 0]) > 55), iterations=2))

def mask_poly(m, ox=0, oy=0, simp=0.8, min_area=6.0, smooth=1.2):
    """binary mask -> shapely (union of row runs), simplified; pixel (i, j) covers [j, j+1] x [i, i+1]"""
    boxes = []
    for i in np.nonzero(m.any(1))[0]:
        row = m[i]; d = np.diff(np.r_[0, row.astype(int), 0]); st = np.nonzero(d == 1)[0]; en = np.nonzero(d == -1)[0]
        boxes += [box(ox + a, oy + i, ox + b, oy + i + 1) for a, b in zip(st, en)]
    if not boxes: return Polygon()
    g = unary_union(boxes).buffer(0.6, join_style=2).buffer(-0.6, join_style=2).simplify(max(simp, 1.05)).buffer(0)
    if smooth: g = g.buffer(smooth, join_style=1).buffer(-2 * smooth, join_style=1).buffer(smooth, join_style=1)   # pixel stairs -> smooth edge
    return unary_union([p for p in (g.geoms if hasattr(g, "geoms") else [g]) if p.area >= min_area]) if not g.is_empty else g

def polys(g): return [p for p in (g.geoms if hasattr(g, "geoms") else [g]) if p.geom_type == "Polygon" and not p.is_empty]

def clean_labels(cls, valid, min_px=40, passes=3):
    """long-and-short tone regions, not speckle: every class island under min_px pixels (or thinner than 3 px) is
    given to the surrounding tones (nearest valid pixel), repeated until stable"""
    cls = cls.copy()
    for _ in range(passes):
        bad = np.zeros_like(valid)
        for k in np.unique(cls[valid]):
            m = (cls == k) & valid
            lab, n = ndi.label(m)
            if n == 0: continue
            sz = ndi.sum(m, lab, range(1, n + 1))
            small = np.isin(lab, 1 + np.nonzero(sz < min_px)[0])
            thin = m & ~ndi.binary_dilation(ndi.binary_erosion(m, iterations=1), iterations=1)
            bad |= small | (thin & ~ndi.binary_opening(m, iterations=1))
        if not bad.any(): break
        src = valid & ~bad
        idx = ndi.distance_transform_edt(~src, return_distances=False, return_indices=True)
        cls = np.where(valid, cls[idx[0], idx[1]], cls)
    return cls

def kmeans(X, k, it=25, seed=0):
    rng = np.random.default_rng(seed); C = X[rng.choice(len(X), k, replace=False)]
    for _ in range(it):
        lab = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(2), 1)
        C = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
    return C, lab

def lanceolate(c, tip, w, n=30, wmax_at=0.42):
    """guide outline from the flower centre to the tip: pointed lanceolate petal, max half-width w/2 at wmax_at"""
    c = np.array(c, float); t = np.array(tip, float); d = t - c; L = np.hypot(*d); u = d / L; nv = np.array([-u[1], u[0]])
    s = np.linspace(0, 1, n)
    hw = w / 2 * np.where(s < wmax_at, np.clip(np.sin(np.pi / 2 * s / wmax_at), 0, 1) ** 0.7, np.clip(np.cos(np.pi / 2 * np.clip(s - wmax_at, 0, None) / (1 - wmax_at)), 0, 1) ** 0.9)
    hw[0] = w * 0.12
    top = [c + u * L * si + nv * h for si, h in zip(s, hw)]; bot = [c + u * L * si - nv * h for si, h in zip(s, hw)]
    return Polygon(top + bot[::-1]).buffer(0)

# ------------------------------------------------------------------ tones (6 clusters over all flower pixels, ordered dark -> light)
TONE_KEYS = ["kb_navy", "kb_cobalt", "kb_royal", "kb_blue", "kb_sky", "kb_ice", "kb_white"]

# guides read on gridded 2x zooms of the close-up: (name, tip px, width px, z)   z: higher = in front
FLOWERS = {
 "cu_lily0": dict(c=(95, 415), R=185.0, petals=[
     ("back_up",   (118, 232), 46, 0), ("left_up", (-12, 330), 58, 1), ("left_down", (-25, 470), 62, 2),
     ("right",     (282, 413), 58, 3), ("low_right", (182, 537), 72, 4), ("up", (176, 298), 74, 5)]),
 "cu_lily1": dict(c=(250, 680), R=125.0, petals=[
     ("up_left",   (105, 598), 42, 0), ("up", (228, 558), 56, 1), ("left", (108, 712), 52, 2), ("down", (222, 803), 48, 3),
     ("low_right", (378, 790), 58, 4), ("up_right", (357, 640), 58, 5)]),
}

def trace_flowers():
    pad = 60
    # pixel tone classes over both flowers' discs
    disc = np.zeros((H, W), bool); yy, xx = np.mgrid[0:H, 0:W]
    for f in FLOWERS.values(): disc |= (xx - f["c"][0]) ** 2 + (yy - f["c"][1]) ** 2 < (f["R"] * 1.15) ** 2
    sel = disc & MASK
    C, lab = kmeans(SM[sel], 7)
    order = np.argsort(C.mean(1)); rank = np.empty(7, int); rank[order] = np.arange(7)
    cls = np.full((H, W), -1, int); cls[sel] = rank[lab]
    # mode filter (removes single-stitch speckle; keeps the long-and-short band shapes)
    onehot = np.stack([ndi.uniform_filter((cls == k).astype(float), 11) for k in range(7)], -1)
    cls_s = np.where(sel, onehot.argmax(-1), -1)
    cls_s = np.where(sel, clean_labels(cls_s, sel, 70), -1)
    # extend classes outside the image / mask by nearest (for petals the close-up crops at the left border)
    big = np.full((H + 2 * pad, W + 2 * pad), -1, int); big[pad:-pad, pad:-pad] = cls_s
    idx = ndi.distance_transform_edt(big < 0, return_distances=False, return_indices=True)
    filled = big[idx[0], idx[1]]
    out = {}
    sil_all = mask_poly(MASK)
    frame = box(0.5, 0.5, W - 0.5, H - 0.5)
    for name, f in FLOWERS.items():
        c = f["c"]; R = f["R"]
        sil = sil_all.intersection(Point(c).buffer(R * 1.12))
        guides = sorted(f["petals"], key=lambda p: p[3])
        shapes = []
        for pn, tip, w, z in guides:
            g = lanceolate(c, tip, w)
            # clip to the traced silhouette inside the image; outside the image keep the guide (close-up crops this flower)
            g = unary_union([g.intersection(sil), g.difference(frame.buffer(-3))]).buffer(1.0).buffer(-1.0)
            shapes.append((pn, tip, z, g))
        # visible part of every petal (front petals cover back ones)
        petals = []
        for i, (pn, tip, z, g) in enumerate(shapes):
            front = unary_union([s[3] for s in shapes[i + 1:]]) if i + 1 < len(shapes) else Polygon()
            vis = g.difference(front).buffer(0)
            # tone regions from the close-up pixels, max 3 tones per petal
            x0, y0, x1, y1 = [int(v) for v in vis.bounds]; x0 -= 1; y0 -= 1; x1 += 2; y1 += 2
            sub = filled[y0 + pad:y1 + pad, x0 + pad:x1 + pad]
            gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            import shapely; inside = shapely.contains_xy(vis, gx, gy)
            vals = sub[inside]
            if len(vals) == 0: continue
            cnt = np.bincount(vals, minlength=7)
            keep = sorted(np.argsort(cnt)[::-1][:3]); keep = [k for k in keep if cnt[k] > 0.04 * cnt.sum()] or [int(cnt.argmax())]
            remap = np.array([min(keep, key=lambda kk: abs(kk - k)) for k in range(7)])
            sub2 = remap[np.clip(sub, 0, 6)]
            sub2 = clean_labels(sub2, inside, 70)
            tones = []
            for k in keep:
                g2 = mask_poly(sub2 == k, x0, y0, simp=0.9, min_area=4).intersection(vis).buffer(0)
                if not g2.is_empty: tones.append((TONE_KEYS[k], g2))
            # assign slivers left uncovered by the vectorised tones to the nearest tone (petal fully covered)
            cov = unary_union([t[1] for t in tones]); rest = vis.difference(cov)
            if not rest.is_empty and tones:
                for q in polys(rest.buffer(0)):
                    j = min(range(len(tones)), key=lambda j: tones[j][1].distance(q))
                    tones[j] = (tones[j][0], tones[j][1].union(q).buffer(0))
            petals.append(dict(name=pn, tip=tip, z=z, outline=g, visible=vis, tones=tones, counts={TONE_KEYS[k]: int(cnt[k]) for k in keep}))
        # centre: deep-blue throat (dark classes near the centre), cream anther knots (lightest class near the centre)
        rr = np.hypot(xx - c[0], yy - c[1])
        throat_m = (cls_s >= 0) & (cls_s <= 1) & (rr < R * 0.20)
        throat = mask_poly(ndi.binary_closing(throat_m, iterations=2), simp=1.0).buffer(2).buffer(-2)
        throat = max(polys(throat.intersection(Point(c).buffer(R * 0.2))) or [Point(c).buffer(R * 0.08)], key=lambda p: p.area)
        if throat.area < (R * 0.08) ** 2 * math.pi: throat = throat.union(Point(c).buffer(R * 0.08)).buffer(0)
        knot_m = (cls_s >= 6) & (rr < R * 0.36) & (rr > R * 0.04)
        knots = sorted(polys(mask_poly(ndi.binary_opening(knot_m, iterations=1), simp=0.8, min_area=10)), key=lambda p: -p.area)[:6]
        out[name] = dict(c=c, R=R, petals=petals, throat=throat, knots=knots, sil=sil)
    return out, C[order]

# ------------------------------------------------------------------ koi
KOI = {"cu_koi0": ((305, 232), (170, 105)), "cu_koi1": ((445, 425), (265, 330)), "cu_koi2": ((455, 665), (310, 480)), "cu_koi3": ((645, 850), (485, 735))}

def trace_koi():
    lab, n = ndi.label(MASK); out = {}
    red_m = (SM[..., 0] > 140) & (SM[..., 1] < 110) & (SM[..., 0] - SM[..., 2] > 60)
    for name, (hd, tl) in KOI.items():
        hd_ = np.array(hd, float); tl_ = np.array(tl, float); L = np.hypot(*(hd_ - tl_)); u = (tl_ - hd_) / L
        mid = (hd_ + tl_) / 2
        comp = lab == lab[int(mid[1]), int(mid[0])]
        if not comp[int(mid[1]), int(mid[0])]: comp = lab == lab[int(hd[1] + 4 * u[1]), int(hd[0] + 4 * u[0])]
        yy, xx = np.mgrid[0:H, 0:W]
        s = ((xx - hd_[0]) * u[0] + (yy - hd_[1]) * u[1]) / L                 # 0 head .. 1 tail tip
        lat = (-(xx - hd_[0]) * u[1] + (yy - hd_[1]) * u[0]) / L
        comp &= (s > -0.05) & (s < 1.08) & (np.abs(lat) < 0.35)
        sil = mask_poly(comp, simp=0.7)
        sil = max(polys(sil), key=lambda p: p.area)
        # body = the opened silhouette in front of the peduncle; tail = beyond; fins = the rest
        r_open = max(2, int(0.06 * L))
        core = ndi.binary_opening(comp & (s < 0.72), structure=np.ones((3, 3)), iterations=r_open)
        core_l, nc = ndi.label(core)
        if nc > 1:
            sizes = ndi.sum(core, core_l, range(1, nc + 1)); core = core_l == (1 + int(np.argmax(sizes)))
        body = max(polys(mask_poly(ndi.binary_dilation(core, iterations=1) & comp, simp=0.9)), key=lambda p: p.area).buffer(1.2).buffer(-1.2)
        tail = unary_union(polys(mask_poly(comp & (s >= 0.62), simp=0.6))).difference(body.buffer(0.5)).buffer(0)
        tail = max(polys(tail), key=lambda p: p.area) if polys(tail) else Polygon()
        cand = [p for p in polys(sil.difference(body.buffer(0.4)).difference(tail.buffer(0.4)).buffer(-0.6).buffer(0.6)) if p.area > 0.0012 * L * L]
        # pieces at the head end are head, not fins: give them back to the body
        sof = lambda p: ((p.centroid.x - hd_[0]) * u[0] + (p.centroid.y - hd_[1]) * u[1]) / L
        fins = [p for p in cand if sof(p) > 0.16]
        head_bits = [p for p in cand if sof(p) <= 0.16]
        if head_bits: body = max(polys(unary_union([body] + [p.buffer(0.6) for p in head_bits]).buffer(0.8).buffer(-0.8)), key=lambda p: p.area)
        # red patches: traced red pixels, crisp angular (simplified), 2 largest
        reds = sorted(polys(mask_poly(ndi.binary_opening(red_m & comp, iterations=1), simp=2.2, min_area=20, smooth=0)), key=lambda p: -p.area)[:2]
        reds = [p.buffer(-0.5, join_style=2).buffer(0.5, join_style=2) for p in reds]
        # grey shading on the body (traced: body pixels clearly darker than the cream, not red)
        bm = comp & (s < 0.70) & ~red_m
        kc = np.where(bm, np.where(ndi.uniform_filter((LUM < 150).astype(float), 7) > 0.5, 1, 0), -1)
        kc = clean_labels(kc, bm, 60)
        grey = unary_union([p for p in polys(mask_poly(kc == 1, simp=1.0, min_area=25))]).intersection(body.buffer(-0.8)).buffer(0)
        # eye: darkest blob on the head
        eye_m = comp & (LUM < 70) & (s < 0.2)
        eye = None
        if eye_m.any():
            ys_, xs_ = np.nonzero(eye_m); eye = (float(xs_.mean()), float(ys_.mean()))
        out[name] = dict(head=hd, tail=tl, L=float(L), sil=sil, body=body, tail_g=tail, fins=fins, reds=reds, grey=grey, eye=eye)
    return out

def trace_petals(exclude):
    lab, n = ndi.label(MASK); out = []
    ex = unary_union(exclude)
    for k in range(1, n + 1):
        m = lab == k; a = m.sum()
        if a < 150 or a > 4000: continue
        ys, xs = np.nonzero(m)
        if xs.min() < 3 or ys.min() < 3 or xs.max() > W - 4 or ys.max() > H - 4: continue
        p = max(polys(mask_poly(m, simp=0.7)), key=lambda q: q.area)
        if p.intersects(ex): continue
        if p.area / max(p.convex_hull.area, 1) < 0.86: continue          # lumpy / two-petal blobs: not a clean petal template
        if ys.max() < 120 and xs.min() > 400: continue          # garment seam / topstitching at the top right
        mrr = p.minimum_rotated_rectangle; cs = np.array(mrr.exterior.coords)
        e = [np.hypot(*(cs[i + 1] - cs[i])) for i in range(2)]
        if max(e) / max(min(e), 1) < 1.6 or min(e) < 12 or p.area / max(mrr.area, 1) < 0.45: continue   # not a petal (stems, slivers)
        tone = SM[m].mean(0)
        out.append(dict(poly=p, rgb=tone.round().tolist(), L=float(max(e)), W=float(min(e))))
    return out

if __name__ == "__main__":
    fl, centres = trace_flowers(); koi = trace_koi()
    pet = trace_petals([f["sil"] for f in fl.values()] + [k["sil"].buffer(4) for k in koi.values()])
    pickle.dump(dict(flowers=fl, koi=koi, petals=pet, tone_rgb=centres.tolist(), tone_keys=TONE_KEYS), open("trace/templates.pkl", "wb"))
    # overlay sheet: close-up | traced objects (thread colours)
    import kbcore
    sc = 2; im = Image.open("inputs/closeup_mockup_koi.png").convert("RGB").resize((W * sc, H * sc), Image.LANCZOS)
    tr = Image.new("RGB", im.size, kbcore.FABRIC); d = ImageDraw.Draw(tr)
    hexc = lambda k: kbcore.KB_PAL[k][0]
    def fill(g, col, outline=None):
        for p in polys(g):
            d.polygon([(x * sc, y * sc) for x, y in p.exterior.coords], fill=col, outline=outline)
            for h in p.interiors: d.polygon([(x * sc, y * sc) for x, y in h.coords], fill=kbcore.FABRIC)
    for f in fl.values():
        for p in f["petals"]:
            for col, g in p["tones"]: fill(g, hexc(col))
            fill(Polygon(), None)
            for q in polys(p["visible"]): d.line([(x * sc, y * sc) for x, y in q.exterior.coords], fill=(10, 14, 30), width=1)
        fill(f["throat"], hexc("kb_navy"))
        for kn in f["knots"]: fill(kn, hexc("kb_white"))
    for k in koi.values():
        fill(k["tail_g"], hexc("kb_cream")); [fill(fn, hexc("kb_cream")) for fn in k["fins"]]
        fill(k["body"], hexc("kb_white")); fill(k["grey"], hexc("kb_grey"))
        for r in k["reds"]: fill(r, hexc("kb_red"))
        if k["eye"]: d.ellipse([k["eye"][0] * sc - 4, k["eye"][1] * sc - 4, k["eye"][0] * sc + 4, k["eye"][1] * sc + 4], fill=hexc("kb_ink"))
    for p in pet: fill(p["poly"], "#9DB4D6", outline="#E6ECF5")
    sheet = Image.new("RGB", (W * sc * 2 + 20, H * sc + 50), "white"); sheet.paste(im, (0, 50)); sheet.paste(tr, (W * sc + 20, 50))
    ImageDraw.Draw(sheet).text((10, 10), "Close-up (inputs/closeup_mockup_koi.png) | objects traced from its pixels (cu_trace.py): petal outlines + tone regions, throats, anther knots, koi silhouettes, red patches, fins, tails, free petals",
                               fill="black", font=ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 20))
    sheet.save("out/trace_closeup.png")
    for n_, f in fl.items(): print(n_, [(p["name"], [t[0] for t in p["tones"]]) for p in f["petals"]], "knots", len(f["knots"]), "throat", round(f["throat"].area))
    for n_, k in koi.items(): print(n_, "L", round(k["L"]), "reds", [round(r.area) for r in k["reds"]], "fins", len(k["fins"]), "tail", round(k["tail_g"].area), "body", round(k["body"].area), "eye", k["eye"])
    print("free petals", len(pet))
