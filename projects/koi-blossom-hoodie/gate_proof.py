"""Red-then-green proof for the Rev C gates (review item 1; skill prove-the-guard).
1. Independence: refmask.py is imported with every art-side module blocked (scene, art_size, floratrace, fishtrace,
   kb_*): it must still build all reference masks -> it cannot be reading the art.
2. Red: stand-ins of the right position + size but the wrong silhouette must FAIL motif_match
   (a fish replaced by an ellipse of the same length + area; a lily disc replaced by a round blob of the same area).
3. Green: the shipped size-M DST masks pass the same rows (fidelity.py).
usage: python3 gate_proof.py   -> prints PASS / FAIL lines, exit 1 on a failed proof"""
import sys, math
for m in ("scene", "art_size", "floratrace", "fishtrace", "kb_motifs", "kb_traced", "kb_fish", "mockref"):
    sys.modules[m] = None                       # any import of these raises ImportError
import kbcore
import numpy as np
from scipy import ndimage as ndi
import refmask as RM, qa
ok = True
for P in kbcore.PIECES:
    f = RM.flora(P); fr = RM.fish_ref(P)
    print(f"independence {P}: flora {f.sum() / RM.PPM ** 2:.0f} mm2, {len(fr)} fish references built with the art modules blocked")
import fidelity as FD
P = "FR"; fr = RM.fish_ref(P); poses = [p for p, _ in fr]; out, olum, oang, _ = FD.masks(P, poses)
XX, YY = RM.grid(P)
# red 1: fish -> ellipse with the same centre, heading, length and area
pose, m = fr[0]; a = math.radians(pose["ang"]); c = pose["c"]; L = pose["L_ref"]
u = (XX - c[0]) * math.cos(a) + (YY - c[1]) * math.sin(a); v = -(XX - c[0]) * math.sin(a) + (YY - c[1]) * math.cos(a)
b = (m.sum() / RM.PPM ** 2) / (math.pi * L / 2)
ell = (u / (L / 2)) ** 2 + (v / b) ** 2 <= 1
rr = qa.motif_match(m, ell, RM.PPM); red1 = not max(rr, key=lambda x: x["area_mm2"])["ok"]
rg = qa.motif_match(m, out["fish"] & ndi.binary_dilation(m, structure=RM.disk(4.0)), RM.PPM); green1 = max(rg, key=lambda x: x["area_mm2"])["ok"]
print(f"fish stand-in (ellipse, same length + area): {'FAIL as required' if red1 else 'PASSED (guard broken)'}  |  shipped DST: {'pass' if green1 else 'FAIL'}"
      f"  (IoU stand-in {max(rr, key=lambda x: x['area_mm2'])['iou']}, DST {max(rg, key=lambda x: x['area_mm2'])['iou']})")
ok &= red1 and green1
# red 2: lily disc -> a round blob of the same area at the same centre
name, src, cc, Rr = FD.lily_discs(P)[0]
disc = np.hypot(XX - cc[0], YY - cc[1]) < Rr; ref = RM.flora(P) & disc
blob = np.hypot(XX - cc[0], YY - cc[1]) < math.sqrt(ref.sum() / RM.PPM ** 2 / math.pi)
iou_b = (ref & blob).sum() / (ref | blob).sum(); iou_d = (ref & out["flora"] & disc).sum() / (ref | (out["flora"] & disc)).sum()
red2 = iou_b < 0.70; green2 = iou_d >= 0.70
print(f"lily stand-in (round blob, same area): IoU {iou_b:.2f} -> {'FAIL as required' if red2 else 'PASSED (guard broken)'}  |  shipped DST IoU {iou_d:.2f} -> {'pass' if green2 else 'FAIL'}")
ok &= red2 and green2
print("PROOF", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
