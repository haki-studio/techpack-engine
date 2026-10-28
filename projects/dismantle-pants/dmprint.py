"""Dismantle Pants — print measurements read from the two founder reference photos (print ONLY; their elastic waist and
shape are ignored). Writes out/print.json + zoom crops used on page P1. Every value is an ESTIMATE from a photo:
pitch from an FFT of the mean luminance profile over flat leg areas, colours from the darkest 40 % / lightest 5 %
of pixels, scale from assumed garment widths (shown with the working on P1)."""
import os, json
import numpy as np
from PIL import Image

REF = {"front": "inputs/reference/print-reference-front.png", "back": "inputs/reference/print-reference-back.png"}
# leg areas with little drape: (y0, y1, x0, x1) px; vertical pitch read down a column band, horizontal across a row band
AREAS = {"vert": [(250, 1250, 300, 420)], "horiz": [(700, 950, 240, 500), (700, 950, 620, 880)]}
HIP_Y = 450          # px row used for the half-hip width (widest flat point below the pockets on both refs)


def period(p):
    p = p - p.mean(); N = 8192
    F = np.abs(np.fft.rfft(p * np.hanning(len(p)), N)); fr = np.fft.rfftfreq(N)
    ok = (fr > 1 / 40) & (fr < 1 / 8)
    return float(1 / fr[np.argmax(F * ok)])


def measure():
    out = {"pitch_px": {}, "hip_px": {}, "length_px": {}, "ground_hex": {}, "line_hex": {}}
    for n, path in REF.items():
        a = np.asarray(Image.open(path).convert("RGB")).astype(float); L = a.mean(-1)
        ps = [period(L[y0:y1, x0:x1].mean(1)) for y0, y1, x0, x1 in AREAS["vert"]]
        ps += [period(L[y0:y1, x0:x1].mean(0)) for y0, y1, x0, x1 in AREAS["horiz"]]
        out["pitch_px"][n] = [round(p, 2) for p in ps]
        m = a.max(-1) < 200
        xs = np.where(m[HIP_Y])[0]; out["hip_px"][n] = int(xs.max() - xs.min())
        rows = np.where(m.sum(1) > 50)[0]; out["length_px"][n] = int(rows.max() - rows.min())
        reg = a[800:1000, 240:520].reshape(-1, 3); l = reg.mean(1)
        g = reg[l < np.percentile(l, 40)].mean(0); ln = reg[l > np.percentile(l, 95)].mean(0)
        out["ground_hex"][n] = "#%02X%02X%02X" % tuple(int(v) for v in g)
        out["line_hex"][n] = "#%02X%02X%02X" % tuple(int(v) for v in ln)
        os.makedirs("out", exist_ok=True)
        im = Image.open(path).convert("RGB")
        im.crop((300, 800, 420, 920)).resize((600, 600), Image.LANCZOS).save(f"out/zoom_{n}.png")
        im.crop((200, 560, 560, 920)).save(f"out/crop_{n}.png")
    allp = [p for v in out["pitch_px"].values() for p in v]
    out["pitch_px_mean"] = round(float(np.mean(allp)), 2)
    out["pitch_px_range"] = [round(min(allp), 2), round(max(allp), 2)]
    hip = float(np.mean(list(out["hip_px"].values())))
    out["squares_across_half_hip"] = round(hip / out["pitch_px_mean"], 1)
    # scale anchors: the reference garment's real size is unknown -> assume a range of half-hip widths (cm)
    out["scenarios"] = []
    for label, half_hip_cm in (("HI size 32 half hip (43 in / 2)", 43 * 2.54 / 2), ("roomier wide-leg ref, half hip 58 cm", 58.0),
                               ("very wide ref, half hip 62 cm", 62.0)):
        px_per_cm = hip / half_hip_cm
        out["scenarios"].append({"anchor": label, "half_hip_cm": round(half_hip_cm, 1), "px_per_cm": round(px_per_cm, 2),
                                 "square_cm": round(out["pitch_px_mean"] / px_per_cm, 2),
                                 "implied_length_cm": round(np.mean(list(out["length_px"].values())) / px_per_cm, 1)})
    sq = [s["square_cm"] for s in out["scenarios"]]
    out["square_cm_range"] = [min(sq), max(sq)]
    # proposal: the standard 1/2 in (12.7 mm) mill repeat if it falls inside the measured range, else the range mid-point
    out["square_cm_proposed"] = 1.27 if min(sq) - 0.05 <= 1.27 <= max(sq) else round(float(np.mean(sq)), 2)
    json.dump(out, open("out/print.json", "w"), indent=1)
    return out


if __name__ == "__main__":
    print(json.dumps(measure(), indent=1))
