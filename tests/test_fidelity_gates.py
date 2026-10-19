"""LESSONS A14/A15 gates, proven red-then-green on the two Grand Line Rev E2 failures (founder, 19 Oct 2026):
hem islets drawn as flattened equal-dome rows (height capped at 0.30 x width) and a bare sea column by the zip."""
import numpy as np, qa

PPM = 4.0
def canvas(w=200, h=120): return np.zeros((int(h*PPM), int(w*PPM)), bool)
def disc(m, cx, cy, r):
    y, x = np.ogrid[:m.shape[0], :m.shape[1]]; m |= (x/PPM - cx)**2 + (y/PPM - cy)**2 <= r*r; return m
def mockup_islet(m, cx, base):                       # compact cloud: taller tiered centre, flat base
    for dx, r in ((-9, 4.5), (-3, 6.5), (3, 7.5), (9, 5.0)): disc(m, cx + dx, base - r*0.9, r)
    return m
def flattened(m, cx, base, w=26.0):                  # Rev E2 stand-in: equal domes, h = 0.30 w
    h = 0.30*w; r = h/2
    for x in np.arange(cx - w/2 + r, cx + w/2 - r + 0.01, r*1.2): disc(m, x, base - r, r)
    return m

def test_flattened_standin_fails_traced_passes():
    ref = mockup_islet(canvas(), 100, 80)
    bad = qa.motif_match(ref, flattened(canvas(), 100, 80), PPM)
    assert len(bad) == 1 and not bad[0]["ok"], bad            # RED: the generated pancake is caught
    good_out = mockup_islet(canvas(), 100.4, 80.3)            # traced: same silhouette, sub-mm registration error
    good = qa.motif_match(ref, good_out, PPM)
    assert good[0]["ok"], good                                 # GREEN: a real trace passes
    missing = qa.motif_match(ref, canvas(), PPM)
    assert not missing[0]["ok"] and missing[0]["iou"] == 0     # a dropped motif fails too

def test_bare_column_found():
    ref = canvas(); ref[int(20*PPM):int(110*PPM), int(10*PPM):int(190*PPM)] = True        # the sea
    out = ref.copy(); out[int(20*PPM):int(110*PPM), int(95*PPM):int(115*PPM)] = False      # 20 mm bare column
    for row in range(int(20*PPM), int(110*PPM), int(2*PPM)): out[row, :] = False           # normal 0.25 mm row gaps
    gaps = qa.uncovered(ref, out, PPM)
    assert gaps and abs(gaps[0]["w_mm"] - 20) < 1.5 and gaps[0]["h_mm"] > 80, gaps         # RED: column flagged
    full = ref.copy()
    for row in range(int(20*PPM), int(110*PPM), int(2*PPM)): full[row, :] = False
    assert qa.uncovered(ref, full, PPM) == []                                               # GREEN: row gaps alone pass
