"""red-then-green for discont.flow_check (fix round 4): a stripe crossing the seam at 90 deg has straight edges by design
and is NOT a cut; a pasted band end that runs across the stripes IS a cut. Run: ./py.sh -m pytest -q test_discont_flow.py"""
import numpy as np
import discont as DC

PPM = DC.PPM
ds = np.arange(0, 140, 1 / PPM)

def stripes_across(H, W, period_mm=5.0):
    """tone stripes that run along the depth axis (they cross the seam at 90 deg): constant-position edges"""
    x = np.arange(W) / PPM
    return np.tile((1 + (x // period_mm) % 3).astype(int), (H, 1))

def test_stripe_edges_running_with_the_flow_are_not_cuts():
    U = stripes_across(len(ds), 400)
    cuts = DC.straight_cuts(U, ds)
    assert cuts, "the old detector flags every straight stripe edge"          # red under the old rule
    assert all(not DC.flow_check(U, ds, c)[0] for c in cuts if c[0] == "across")

def test_band_pasted_across_the_stripes_is_a_cut():
    U = stripes_across(len(ds), 600, period_mm=30.0)                     # wide bands: a shifted band end runs >= 12 mm with one tone pair
    r = int(60 * PPM)
    U[r:] = np.roll(U[r:], int(15 * PPM), axis=1)                        # a band shifted 15 mm: its end is a cut line
    cuts = [c for c in DC.straight_cuts(U, ds) if c[0] == "parallel" and abs(c[1] - 60) < 1.0]
    assert cuts
    assert all(DC.flow_check(U, ds, c)[0] for c in cuts)

def test_straight_line_across_curved_stripes_is_a_cut():
    H, W = len(ds), 400
    yy, xx = np.mgrid[0:H, 0:W] / PPM
    U = (1 + ((yy + 0.3 * xx) // 5) % 3).astype(int)                     # stripes slanted ~17 deg off the seam
    c = W // 2
    U[:, c:] = (1 + ((yy[:, c:] + 0.3 * xx[:, c:] + 2.5) // 5) % 3).astype(int)   # a vertical cut: tones jump at x = c
    cand = ("across", 30.0, c / PPM, c / PPM)
    assert DC.flow_check(U, ds, cand)[0]
