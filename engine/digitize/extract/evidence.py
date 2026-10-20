"""Evidence (ENGINE_PLAN M1): what the reference pixels say, kept as EVIDENCE, never as geometry to sew.

  ev = evidence.build(ref, palette, ppm=4.0)       # ref = register.reference(...) (input pixels only, LESSONS A14)
  ev.tone            (H, W) int: index into ev.keys, nearest palette tone (CIEDE2000) after a light blur + mode filter
  ev.keys / ev.hex   the palette (run.yaml threads.palette), in order
  ev.rgb             (H, W, 3) the reference resampled to the evidence grid
  ev.mask(poly)      bool raster of a garment-mm polygon on the evidence grid
  ev.polys(mask)     connected components of a mask -> shapely polygons (garment mm)
  ev.field_angle(g)  the thread direction the reference shows inside geometry g: structure tensor summed over g ->
                     (angle deg, coherence 0..1). Threads run ACROSS the luminance gradient.

The tone trace says WHICH thread a pixel looks like; zones decide what a part is (rule 1: parts, not colours), and the
splitters decide its shape and direction. Nothing here becomes a stitch object directly (that was the Rev B blob bug,
LESSONS A16)."""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi


def hex_rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_lab(rgb):
    from skimage.color import rgb2lab
    return rgb2lab(np.clip(np.asarray(rgb, float) / 255.0, 0, 1))


def delta_e(lab_a, lab_b):
    from skimage.color import deltaE_ciede2000
    return deltaE_ciede2000(lab_a, lab_b)


class Evidence:
    def __init__(self, ref, palette, ppm=4.0, smooth_mm=0.35, mode_mm=0.6):
        self.bounds = tuple(ref["bounds"]); self.ppm = float(ppm); x0, y0, x1, y1 = self.bounds
        self.W, self.H = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
        rp = float(ref["ppm"]); f = rp / ppm
        rgb = np.asarray(ref["rgb"], float)
        if abs(f - round(f)) < 1e-6 and f >= 1:
            k = int(round(f)); h, w = self.H * k, self.W * k
            self.rgb = rgb[:h, :w].reshape(self.H, k, self.W, k, 3).mean(axis=(1, 3))
        else:
            self.rgb = np.asarray(Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).resize((self.W, self.H), Image.LANCZOS), float)
        self.keys = list(palette); self.hex = [palette[k] for k in self.keys]
        lab_p = to_lab(np.array([[hex_rgb(h) for h in self.hex]]))[0]
        sm = ndi.gaussian_filter(self.rgb, (smooth_mm * ppm, smooth_mm * ppm, 0)) if smooth_mm else self.rgb
        lab = to_lab(sm).reshape(-1, 3)
        d = np.stack([delta_e(lab, np.broadcast_to(lab_p[i], lab.shape)) for i in range(len(self.keys))], -1)
        t = d.argmin(-1).reshape(self.H, self.W)
        if mode_mm:                                                  # majority filter: speckle -> the local tone
            r = max(1, int(round(mode_mm * ppm)))
            cnt = np.stack([ndi.uniform_filter((t == i).astype(np.float32), 2 * r + 1) for i in range(len(self.keys))], -1)
            t = cnt.argmax(-1)
        self.tone = t.astype(np.int16); self.lab_palette = lab_p
        # structure tensor products from the full-resolution grey, block-averaged to the evidence grid
        g = np.asarray(ref["grey"], float); gy, gx = np.gradient(ndi.gaussian_filter(g, 0.6))
        k = max(1, int(round(f)))
        def blk(a):
            h, w = self.H * k, self.W * k; a = a[:h, :w]
            if a.shape != (h, w): a = np.pad(a, ((0, h - a.shape[0]), (0, w - a.shape[1])))
            return a.reshape(self.H, k, self.W, k).mean(axis=(1, 3))
        self.Jxx, self.Jyy, self.Jxy = blk(gx * gx), blk(gy * gy), blk(gx * gy)
        cw = ref.get("closeup_weight")
        self.closeup_weight = blk(np.asarray(cw, float)) if cw is not None else None

    # ------------------------------------------------------------ grids
    def to_px(self, x, y): return ((np.asarray(x) - self.bounds[0]) * self.ppm, (np.asarray(y) - self.bounds[1]) * self.ppm)
    def to_mm(self, px, py): return (px / self.ppm + self.bounds[0], py / self.ppm + self.bounds[1])

    def mask(self, g):
        im = Image.new("L", (self.W, self.H), 0); d = ImageDraw.Draw(im)
        for p in ([g] if g.geom_type == "Polygon" else [q for q in getattr(g, "geoms", []) if q.geom_type == "Polygon"]):
            T = lambda cs: [tuple(v) for v in np.stack(self.to_px(*np.asarray(cs).T), -1)]
            d.polygon(T(p.exterior.coords), fill=255)
            for r in p.interiors: d.polygon(T(r.coords), fill=0)
        return np.asarray(im) > 127

    def polys(self, mask, min_mm2=0.0, simplify=0.15):
        """connected components -> polygons (even-odd nesting of the marching-squares contours), garment mm"""
        from skimage import measure
        from shapely.geometry import Polygon
        lab, n = ndi.label(mask); out = []
        for i, s in enumerate(ndi.find_objects(lab), 1):
            if s is None: continue
            m = np.pad(lab[s] == i, 1)
            if m.sum() < min_mm2 * self.ppm ** 2: continue
            g = Polygon()
            for c in measure.find_contours(m.astype(np.float32), 0.5):
                if len(c) < 4: continue
                xs = (c[:, 1] + s[1].start - 1 + 0.5) / self.ppm + self.bounds[0]
                ys = (c[:, 0] + s[0].start - 1 + 0.5) / self.ppm + self.bounds[1]
                p = Polygon(np.c_[xs, ys]).buffer(0)
                if not p.is_empty: g = g.symmetric_difference(p)
            g = g.simplify(simplify).buffer(0) if simplify else g.buffer(0)
            if not g.is_empty and g.area >= min_mm2: out.append(g)
        return out

    def field_angle(self, g=None, mask=None):
        m = self.mask(g) if mask is None else mask
        if not m.any(): return None, 0.0
        jxx, jyy, jxy = self.Jxx[m].sum(), self.Jyy[m].sum(), self.Jxy[m].sum()
        tr = jxx + jyy; coh = math.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / max(tr, 1e-9)
        a_grad = 0.5 * math.atan2(2 * jxy, jxx - jyy)
        return (math.degrees(a_grad) + 90.0) % 180.0, coh

    def mean_rgb(self, mask):
        return tuple(float(v) for v in self.rgb[mask].mean(axis=0)) if mask.any() else None

    def tone_png(self, path, scale=2):
        cols = np.array([hex_rgb(h) for h in self.hex], np.uint8)
        Image.fromarray(cols[self.tone]).resize((self.W * scale, self.H * scale), Image.NEAREST).save(path)
        return path


def build(ref, palette, ppm=4.0, smooth_mm=0.35, mode_mm=0.6):
    return Evidence(ref, palette, ppm, smooth_mm, mode_mm)
