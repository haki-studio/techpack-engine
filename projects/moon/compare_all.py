"""compare_<element>.png for every element: mockup crop (x4 Lanczos) | our stitch preview (size M art), same scale,
plus zoomed detail rows."""
import pickle
import moonpal, compare as C, tracedart as TA, scene
A = scene.art_for_size("M"); G = scene.graded_art()
f = TA.back_pt
def mmbox(px):
    a = f(px[0], px[1]); b = f(px[2], px[3]); return (a[0], a[1], b[0], b[1])
vis = A["back"] + A["moonbox"]
C.sheet("01_moon", TA.BACK, (232, 221, 462, 451), vis, mmbox((232, 221, 462, 451)), ppm=3,
        zooms=[(mmbox((262, 250, 312, 300)), (262, 250, 312, 300)), (mmbox((400, 280, 450, 330)), (400, 280, 450, 330))])
C.sheet("01_back", TA.BACK, (100, 290, 625, 697), vis, mmbox((100, 290, 625, 697)), ppm=2,
        zooms=[(mmbox((110, 300, 300, 370)), (110, 300, 300, 370)), (mmbox((420, 410, 610, 475)), (420, 410, 610, 475))])
C.sheet("01_pole", TA.BACK, (228, 428, 446, 697), vis, mmbox((228, 428, 446, 697)), ppm=3,
        zooms=[(mmbox((240, 490, 340, 595)), (240, 490, 340, 595)), (mmbox((340, 440, 440, 620)), (340, 440, 440, 620))])
ff = lambda px, py: (TA.FX(px), TA.FYm(py))
def fbox(px): a = ff(px[0], px[1]); b = ff(px[2], px[3]); return (a[0], a[1], b[0], b[1])
fvis = A["F03L"] + A["F03R"] + G["02R"] + G["02L"]
C.sheet("02_chest", TA.FRONT, (135, 250, 615, 400), fvis, fbox((135, 250, 615, 400)), ppm=2)
C.sheet("03_front", TA.FRONT, (135, 470, 615, 680), fvis, fbox((135, 470, 615, 680)), ppm=2)
pf = TA.front_pole_f
a = pf(455, 470); b = pf(640, 682)
C.sheet("03_pole", TA.FRONT, (455, 470, 640, 682), fvis, (float(a[0]), float(a[1]), float(b[0]), float(b[1])), ppm=4)
print("ok")
