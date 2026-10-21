"""Rev C seam-band redraw core (seamredraw.py): red-then-green on synthetic seams (no art pickle needed)."""
import numpy as np
import pytest
sr = pytest.importorskip("seamredraw")

PPM = sr.PPM


def stripe_img(n, rows, s0, m, width=10, code=4):
    """a slanted stripe on a side: column = s0 + m * row (rows = depth from the seam)"""
    img = -np.ones((rows, n), int)
    for r in range(rows):
        c = int(round(s0 + m * r)); img[r, max(0, c):min(n, c + width)] = code
    return img


def test_slope_is_read_from_a_slanted_stripe():
    img = stripe_img(300, 90, 100, 0.5)
    m = sr.slopes(img, 3.0)
    assert abs(np.median(m[90:130]) - 0.5) < 0.12


@pytest.mark.parametrize("mutate", [False, True])
def test_glide_continues_the_stripe_straight_and_meets_at_the_pivot(mutate):
    n, rows, m0 = 300, 90, 0.5
    A = stripe_img(n, rows, 100, m0)
    m = np.full(n, 0.0 if mutate else m0)
    dp = 5.0
    g, off = sr.glide_cols(m, rows, n, dp)
    B = np.where(off, -1, A[np.arange(rows)[:, None], g])
    rp = int(dp * PPM)
    # meets itself at the pivot row (both sides show the same columns there)
    assert (A[rp] == B[rp]).all()
    # continues STRAIGHT on B: the stripe's left edge on B at row r is s0 + m*rp - m*(r - rp) (mirror of A about the pivot)
    r = 60; left = np.nonzero(B[r] >= 0)[0].min()
    expect = 100 + m0 * rp - m0 * (r - rp)
    if mutate: assert abs(left - expect) > 5          # no glide: a mirror only, the stripe bends (red)
    else: assert abs(left - expect) <= 2


def test_cut_never_enters_the_dmin_band_and_prefers_agreement():
    R, n = 40, 50
    mis = np.ones((2 * R, n)); mis[R + 25] = 0.0                 # the pictures agree only 12.5 mm into side B
    t_mm = np.r_[-(np.arange(R)[::-1] + 0.5), np.arange(R) + 0.5] / PPM
    cost = mis.copy(); cost[np.abs(t_mm) < 8.0] += 1e3
    cut = sr.cut_path(cost, mis, R, 8.0)
    assert (np.abs(t_mm[cut]) >= 8.0).all() and (cut == R + 25).all()


def test_foam_continued_into_bare_fabric_ends_in_lobes():
    R, n = 40, 40
    t_mm = np.r_[-(np.arange(R)[::-1] + 0.5), np.arange(R) + 0.5] / PPM
    PA = -np.ones((2 * R, n), int); PA[:R + 30] = 0                # foam (code 0) on A, continued 15 mm into B
    PB = -np.ones((2 * R, n), int)                                  # B bare
    tcut = np.full(n, 12.0)
    out, runs = sr.foam_lobes(tcut, t_mm, PA, PB, 8.0)
    assert runs == 1 and out.min() < 12.0 - 1.5 and out.max() == 12.0   # scalloped, crowns at the cut
