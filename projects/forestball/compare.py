"""Side-by-side fidelity sheets: out/compare_back.png, out/compare_front.png — mockup crop (Lanczos x4) vs stitch-out
preview of the same area at the same scale, whole element + 4 zoomed regions each (Rev B, fidelity first)."""
import pickle, sys
import fbcore
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import stitchrender as SR
import back as B, front as F

def label(im, s):
    d = ImageDraw.Draw(im)
    try: fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    except Exception: fnt = None
    d.rectangle([0, 0, im.width, 36], fill=(255, 255, 255)); d.text((8, 4), s, fill=(20, 20, 20), font=fnt)
    return im

def pair(mock, crop_px, P, vis, h=520):
    x0, y0, x1, y1 = crop_px
    m = mock.crop(crop_px).resize(((x1-x0)*4, (y1-y0)*4), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.2, 60))
    a = P(x0, y0); b = P(x1, y1)
    bx = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
    ppm = h / (bx[3] - bx[1])
    r = SR.render(vis, bx, ppm, base=fbcore.FABRIC)
    m = m.resize((int(m.width * h / m.height), h))
    r = r.resize((m.width, h))
    out = Image.new("RGB", (m.width * 2 + 12, h + 40), (255, 255, 255))
    out.paste(m, (0, 40)); out.paste(r, (m.width + 12, 40))
    return out

def sheet(name, mock_path, P, vis, whole, zooms, labels):
    mock = Image.open(mock_path).convert("RGB")
    tiles = [label(pair(mock, whole, P, vis, 900), "whole element: mockup (left) vs stitch preview (right), same scale")]
    for z, lb in zip(zooms, labels):
        tiles.append(label(pair(mock, z, P, vis, 440), lb))
    W = max(t.width for t in tiles); H = sum(t.height + 10 for t in tiles)
    out = Image.new("RGB", (W, H), (255, 255, 255)); y = 0
    for t in tiles: out.paste(t, (0, y)); y += t.height + 10
    out.thumbnail((2400, 4800)); out.save(f"out/compare_{name}.png"); print("wrote", f"out/compare_{name}.png", out.size)

if __name__ == "__main__":
    if "back" in sys.argv or len(sys.argv) == 1:
        V = pickle.load(open("back_vis.pkl", "rb"))["back"]
        sheet("back", "inputs/back.png", B.P, V, (95, 90, 640, 700),
              [(150, 230, 330, 360), (380, 470, 600, 610), (200, 560, 400, 700), (480, 100, 660, 260)],
              ["zoom: mossy main limb + leaf sprays", "zoom: mossy bank + stream + licensed placeholder", "zoom: stream, rocks, grass bottom-left",
               "zoom: top-right sprays + light rays"])
    if "front" in sys.argv or len(sys.argv) == 1:
        Fv = pickle.load(open("front_vis.pkl", "rb")); V = Fv["02R"] + Fv["02L"]
        sheet("front", "inputs/front.png", F.P, V, (95, 90, 650, 470),
              [(110, 110, 270, 450), (240, 190, 380, 360), (390, 180, 640, 330), (420, 330, 650, 470)],
              ["zoom: hanging moss ropes (02R)", "zoom: main limb + sprays at the zip (02R)", "zoom: 02L upper twig + sprays", "zoom: 02L limb end + sprays"])
