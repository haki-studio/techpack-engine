"""Panels (ENGINE_PLAN M0/M1): one PNG that shows a run the way a digitizer judges it, side by side:
reference | part map | live view | direction heat-map | density (the part map only when a plan exists).

Titles and the legend come from bench.json `panel_labels` (str.format templates over the gate row's numbers, see
FIELDS), so a different benchmark labels its own panels; DEFAULT_LABELS reproduces the M0 baseline titles.

  imgs = panel.tiles(row, aux, cfg_b, dst, origin)        # dict(ref, live, heat, density) PIL images
  panel.compose([(img, title), ...], legend, path)"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import dstlive

DEFAULT_LABELS = {
    "ref": "12 ppm reference (mockup + {closeup} close-up, min weight {min_weight}; source detail ~{source_ppm} px/mm)",
    "part_map": "part map: {parts} parts by kind (sky blue, falls white/blue, pool cyan, zone stubs in their thread colour, washed grey); red tick = declared angle",
    "live": "live view (dstlive) - {stitches:,} stitches, {trims} trims ({trims_per_100cm2}/100 cm2 of covered area)",
    "heat": "direction (visible layer): {dir_ok}% OK, {dir_chaos}% chaotic, {n_dev} off-grain  [all stitches: {dir_all}%]",
    "density": "density mm/mm2: mean {dens_mean}, p95 {dens_p95}, {dens_flags} areas > {dens_thr} (white boxes)",
    "legend": ("heat-map: green OK, red off the reference grain > 25 deg, magenta chaotic (R < 0.55); 8 mm tiles.   density ramp: "
               "navy 1, blue 2.5 (one tatami layer), green 5, yellow 7, red 9+ mm/mm2.   "
               "crop x {x0}..{x1}, y {y0}..{y1} mm ({piece}, size {size}, garment mm).   {label}  {date}"),
}


def fields(row, cfg_b):
    d, de, tr = row["direction"], row["density"], row["trims"]; c = cfg_b["crop"]
    return dict(closeup=cfg_b.get("closeup", ""), min_weight=row["crop_min_closeup_weight"], source_ppm=row.get("source_ppm_median", "?"),
                stitches=row["stitches_in_crop"], trims=tr["trims"], trims_per_100cm2=tr["per_100cm2"], dir_ok=d["pct_ok"],
                dir_chaos=d["pct_chaos"], n_dev=d["n_dev"], dir_all=d["pct_ok_all_stitches"], dens_mean=de["mean"], dens_p95=de["p95"],
                dens_flags=de["flags"], dens_thr=de["threshold"], x0=c[0], y0=c[1], x1=c[2], y1=c[3], piece=cfg_b.get("piece", ""),
                size=cfg_b.get("size", ""), label=row.get("label", ""), date=row.get("date", ""), parts=row.get("parts", {}).get("n", "?"))


def labels(row, cfg_b):
    L = dict(DEFAULT_LABELS, **cfg_b.get("panel_labels", {})); f = fields(row, cfg_b)
    return {k: v.format(**f) for k, v in L.items()}


def _font(n):
    try: return ImageFont.load_default(size=n)
    except TypeError: return ImageFont.load_default()


RAMP = [(0.0, (22, 24, 34)), (1.0, (40, 60, 110)), (2.5, (40, 120, 170)), (5.0, (70, 190, 120)), (7.0, (240, 220, 60)), (9.0, (230, 40, 40))]


def ramp(v):
    v = np.asarray(v, float); out = np.zeros(v.shape + (3,))
    xs = [a for a, _ in RAMP]
    for c in range(3): out[..., c] = np.interp(v, xs, [col[c] for _, col in RAMP])
    return out.astype(np.uint8)


def tiles(row, aux, cfg_b, dst, origin):
    P = float(cfg_b["panel_ppm"]); crop = tuple(cfg_b["crop"]); x0, y0, x1, y1 = crop
    W, H = int(round((x1 - x0) * P)), int(round((y1 - y0) * P))
    ref = Image.fromarray(aux["ref"]["rgb"].astype(np.uint8)).resize((W, H), Image.LANCZOS)
    live = dstlive.render(dst, aux["cols"], ppm=P * 2, shell=cfg_b["shell"], bounds=crop, origin=origin).resize((W, H), Image.LANCZOS)
    heat = live.convert("RGBA"); ov = Image.new("RGBA", heat.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov); T = aux["dm"]["tile_mm"]
    def tile(c, col):
        cx, cy = c; d.rectangle([(cx - T / 2) * P, (cy - T / 2) * P, (cx + T / 2) * P - 1, (cy + T / 2) * P - 1], fill=col, outline=col[:3] + (200,))
    for c in aux["dm"]["ok_tiles"]: tile(c, (40, 200, 60, 70))
    for r in aux["dm"]["fail_dev"]: tile(r["at_mm"], (230, 30, 30, 130))
    for r in aux["dm"]["fail_chaos"]: tile(r["at_mm"], (230, 0, 230, 130))
    heat = Image.alpha_composite(heat, ov).convert("RGB")
    den = Image.fromarray(ramp(aux["dens"]["grid"])).resize((W, H), Image.NEAREST); dd = ImageDraw.Draw(den)
    for f in aux["dens"]["flags"]:
        cx, cy = f["at_mm"][0] - x0, f["at_mm"][1] - y0
        dd.rectangle([(cx - f["w_mm"] / 2) * P, (cy - f["h_mm"] / 2) * P, (cx + f["w_mm"] / 2) * P, (cy + f["h_mm"] / 2) * P], outline=(255, 255, 255), width=2)
    return dict(ref=ref, live=live, heat=heat, density=den)


def compose(cols, legend, path, quantize=True):
    W = max(im.width for im, _ in cols); H = max(im.height for im, _ in cols)
    import textwrap
    wrap = max(30, int(W / 8.2)); lines = [textwrap.wrap(t, wrap) for _, t in cols]
    pad, foot = 12, 40; top = 14 + 18 * max(len(l) for l in lines); n = len(cols)
    im = Image.new("RGB", (n * W + (n + 1) * pad, H + top + foot), (245, 245, 242)); D = ImageDraw.Draw(im); f = _font(15)
    for i, ((p, _), ls) in enumerate(zip(cols, lines)):
        X = pad + i * (W + pad); im.paste(p, (X, top))
        for j, t in enumerate(ls): D.text((X, 7 + 18 * j), t, fill=(20, 20, 20), font=f)
    D.text((pad, H + top + 12), legend, fill=(60, 60, 60), font=_font(13))
    if quantize: im = im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    im.save(path, optimize=True)
    return path
