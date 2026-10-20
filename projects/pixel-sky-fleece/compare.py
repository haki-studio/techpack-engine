"""out/compare_<element>.png: mockup crop vs stitch preview (DST live view) at the SAME scale + zoomed regions;
out/compare_jacquard.png: mockup vs the jacquard cell maps drawn back into the mockup view + zooms + agreement table."""
import json, pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import mockmap as MM, dstlive, jacquard as JQ, pixels as PX

SKY_HEX = "#80AEF7"
COLS = {"yellow": "#F6E23A", "gold": "#D9A521", "black": "#231F1E"}
try: FONT = ImageFont.truetype("DejaVuSans-Bold.ttf", 22); FS = ImageFont.truetype("DejaVuSans.ttf", 17)
except Exception: FONT = FS = ImageFont.load_default()

def mock_crop(b, ppm):
    """garment-mm box on the FRONT -> mockup crop resampled to ppm px/mm"""
    px0, py0 = MM.Pinv(b[0], b[1]); px1, py1 = MM.Pinv(b[2], b[3])
    im = Image.fromarray(MM.img().astype(np.uint8)).crop((int(px0), int(py0), int(px1), int(py1)))
    return im.resize((int((b[2] - b[0]) * ppm), int((b[3] - b[1]) * ppm)), Image.LANCZOS)

def mock_crop_px(bpx, ppm):
    im = Image.fromarray(MM.img().astype(np.uint8)).crop(tuple(int(v) for v in bpx))
    return im.resize((int((bpx[2] - bpx[0]) * MM.S * ppm), int((bpx[3] - bpx[1]) * MM.S * ppm)), Image.LANCZOS)

def live(F, b, ppm, so, org, stops):
    return dstlive.render(f"out/stitch/{F}/HK-FL-PIXSKY_{F}.dst", colours=[COLS[t] for t in stops], ppm=ppm, shell=SKY_HEX,
                          bounds=b, origin=(org[0] + so[0], org[1] + so[1]))

def label(im, s, sub=""):
    W, H = im.size; out = Image.new("RGB", (W, H + 50), "white"); out.paste(im, (0, 50)); d = ImageDraw.Draw(out)
    d.text((6, 4), s, fill=(20, 20, 20), font=FONT); d.text((6, 28), sub, fill=(90, 90, 90), font=FS); return out

def hcat(ims, gap=16):
    W = sum(i.size[0] for i in ims) + gap * (len(ims) - 1); H = max(i.size[1] for i in ims)
    out = Image.new("RGB", (W, H), "white"); x = 0
    for i in ims: out.paste(i, (x, 0)); x += i.size[0] + gap
    return out

def vcat(ims, gap=16):
    W = max(i.size[0] for i in ims); H = sum(i.size[1] for i in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (W, H), "white"); y = 0
    for i in ims: out.paste(i, (0, y)); y += i.size[1] + gap
    return out

def element(F, title):
    pl = json.load(open("out/art/placements.json"))["files"]; art = pickle.load(open("out/art/art.pkl", "rb"))
    rbj = json.load(open(f"out/stitch/{F}/readback.json")); plan = json.load(open(f"out/stitch/{F}/plan.json"))
    G = json.load(open("out/stitch/gates_fl.json"))[F]
    so, org = pl[F]["svg_origin"], rbj["origin"]; stops = [s["thread"] for s in plan["stops"]]
    x0, y0, x1, y1 = pl[F]["art_bounds"]; b = (x0 - 8, y0 - 8, x1 + 8, y1 + 8); ppm = min(6.0, 1500 / (b[2] - b[0]))
    st = live(F, b, ppm, so, org, stops)
    sub = f"{G['stitches']:,} stitches · {G['trims']} trims · {G['stops']} stops · A14 motifs {G['motifs_pass']}/{G['motifs_n']} (min IoU {min(m['iou'] for m in G['motifs']):.2f})"
    if F != "E3":
        mk = mock_crop(b, ppm); top = hcat([label(mk, f"MOCKUP {title}", "inputs/front.png (low-res AI render, 0.6 mm/px)"),
                                            label(st, f"STITCH PREVIEW {F} (DST read-back)", sub)])
        motifs = sorted(art[F], key=lambda a: -a[1].area)[:4]
        zooms = []
        for col, geom, ref in motifs:
            g = geom.bounds; zb = (g[0] - 4, g[1] - 4, g[2] + 4, g[3] + 4); zp = min(14.0, 420 / (zb[2] - zb[0]))
            zooms.append(hcat([label(mock_crop(zb, zp), "mockup", f"{col}"), label(live(F, zb, zp, so, org, stops), "stitches", f"{zb[2]-zb[0]:.0f} mm wide")], 6))
        out = vcat([top, hcat(zooms, 24)])
    else:
        # sleeve: motifs were moved onto the sleeve pattern one by one (centroids via mockmap.sleeve_to_img), so the render
        # crop is shown at the same mm scale next to the file; zooms pair each motif with its own render pixels
        bpx = (1225, 650, 1340, 890); mk = mock_crop_px(bpx, ppm)
        top = hcat([label(mk, f"MOCKUP {title}", "sleeve front half as seen (foreshortened)"), label(st, f"STITCH PREVIEW {F} (sleeve pattern coords)", sub)])
        zooms = []
        for col, geom, ref in art[F]:
            g = geom.bounds; zb = (g[0] - 4, g[1] - 4, g[2] + 4, g[3] + 4); zp = min(14.0, 420 / (zb[2] - zb[0]))
            zooms.append(label(live(F, zb, zp, so, org, stops), "stitches", col))
        out = vcat([top, hcat(zooms, 24)])
    out.save(f"out/compare_{F}.png"); return out

def jacquard_sheet():
    import jq_view
    v = jq_view.render("A"); v.save("out/jacquard/view_front_A.png")
    a = Image.fromarray(MM.img().astype(np.uint8))
    # agreement on the traced (visible, non-detail) front pixels: sky/cream class of the render vs the drawn map
    lab = PX.labels(); arr = np.array(v); vis = MM.visible_body()
    H, Wd = lab.shape; yy, xx = np.mgrid[0:H, 0:Wd]
    mi = Image.new("L", (Wd, H), 0); ImageDraw.Draw(mi).polygon([tuple(p) for p in vis.exterior.coords], fill=255)
    inside = np.array(mi) > 0
    m = inside & np.isin(lab, [PX.SKY, PX.CREAM]) & (yy > 380) & (yy < MM.HEMY - 20)
    drawn_sky = (arr[..., 2].astype(int) - arr[..., 0].astype(int)) > 60
    agree = float(((lab == PX.SKY) == drawn_sky)[m].mean())
    band = m & (yy > 860) & (yy < 1180)
    agree_band = float(((lab == PX.SKY) == drawn_sky)[band].mean())
    full = hcat([label(a.resize((900, 900)), "MOCKUP", "inputs/front.png"),
                 label(v.resize((900, 900)), "JACQUARD CELL MAPS (option A: bird knitted) drawn back into the mockup view",
                       f"pixel agreement sky/cream: {agree*100:.1f} % whole visible front, {agree_band*100:.1f} % in the cloud band")])
    zs = []
    for bpx in ((330, 880, 730, 1140), (745, 880, 1130, 1140), (430, 600, 700, 830), (10, 860, 350, 1300)):
        w = bpx[2] - bpx[0]; k = 560 / w
        zs.append(vcat([a.crop(bpx).resize((560, int((bpx[3] - bpx[1]) * k))), v.crop(bpx).resize((560, int((bpx[3] - bpx[1]) * k)), Image.NEAREST)], 6))
    out = vcat([full, label(hcat(zs, 18), "ZOOMS (top: mockup, bottom: cell map) — left band, right band, bird, right sleeve", "2.5 mm cells; clouds in 2 x 2 blocks")])
    out.save("out/compare_jacquard.png")
    json.dump(dict(agree_front=round(agree, 4), agree_band=round(agree_band, 4)), open("out/jacquard/agreement.json", "w"))
    return agree, agree_band

if __name__ == "__main__":
    import sys
    for F, t in (("E1", "sparkles, wearer's right front"), ("E2", "sparkles, wearer's left front"), ("E3", "sparkles, wearer's left sleeve"),
                 ("E1B", "bird + sparkles, wearer's right front")):
        element(F, t); print(F, "ok")
    if "nojq" not in sys.argv: print("jacquard agreement", jacquard_sheet())
