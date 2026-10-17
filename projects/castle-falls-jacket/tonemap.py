"""Lab helpers + mockup tone clustering for the tonal trace."""
import numpy as np
_M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
def lab(a):
    a = np.asarray(a, float) / 255.0; lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    X = lin @ _M.T / np.array([0.95047, 1, 1.08883]); f = np.where(X > 0.008856, np.cbrt(X), 7.787 * X + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
def lab2rgb(L):
    L = np.asarray(L, float); fy = (L[..., 0] + 16) / 116; fx = fy + L[..., 1] / 500; fz = fy - L[..., 2] / 200
    f = lambda t: np.where(t ** 3 > 0.008856, t ** 3, (t - 16 / 116) / 7.787)
    X = np.stack([f(fx) * 0.95047, f(fy), f(fz) * 1.08883], -1)
    lin = X @ np.linalg.inv(_M).T; c = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)
    return (np.clip(c, 0, 1) * 255).astype(int)
def hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
