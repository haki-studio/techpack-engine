"""STUB svg2dst engine — same CLI and result.json as scripts/svg2dst.py (docs/SVG2DST.md), crude stitches.

Exists only so the PLM "SVG → DST" window and the worker can be built and tested before S1 lands.
It rasterises the SVG, splits it by colour (max 12) and fills each colour with plain back-and-forth rows.
No underlay, no satin, no pull compensation, no thread-book matching. The hard gate `engine_real` is
always False, so every stub result reads "not OK" on the page. No Anthropic API.

  python3 services/svg2dst/stub_engine.py --svg in.svg --width-mm 90 --fabric twill --hoop 300x300 --out out/ --no-api
"""
import argparse, io, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from contract import CONTRACT, NEEDLES, InputError, check_inputs, check_svg_text, parse_hoop  # noqa: E402

PPM = 5.0                 # raster pixels per mm (0.2 mm)
MAX_STITCH_MM = 3.5       # fill stitch length
TRIM_GAP_MM = 3.0         # a jump longer than this gets a trim
SMALL_AREA_MM2 = 4.0      # a colour smaller than this becomes a question
ROW_MM = {"twill": 0.40, "denim": 0.40, "jersey": 0.45, "fleece": 0.45, "pique": 0.45, "sherpa": 0.55}


def machine_minutes(stitches, trims, colour_changes):
    try:
        sys.path.insert(0, os.path.join(ROOT, "engine"))
        import factory
        return factory.machine_hours(stitches, factory.load(), trims=trims, colour_changes=colour_changes) * 60
    except Exception:  # factory.py not importable (stub run outside the repo) -> same formula, 750 spm
        return (stitches / 750 * 60 + trims * 6.0 + colour_changes * 4.0) / 60


def rasterise(svg_text, width_mm):
    import cairosvg
    from PIL import Image
    png = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), output_width=int(round(width_mm * PPM)), unsafe=False)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def palette(img, max_colours=NEEDLES):
    """(labels HxW int array, -1 = bare; colours [(r,g,b)]).

    Palette = the most frequent fully-opaque colours (anti-aliased edge pixels are rare blends, so a
    frequency floor drops them), capped at max_colours; every opaque pixel then takes the nearest one.
    More real colours than needles is left to the threads_le_needles gate, never merged silently —
    except that the stub caps at max_colours and says so in a warning."""
    import numpy as np
    a = np.asarray(img).astype(int)
    opaque = a[..., 3] >= 128
    if not opaque.any(): raise InputError("the SVG renders nothing visible (no filled shapes at this size)")
    key = a[..., 0] * 65536 + a[..., 1] * 256 + a[..., 2]
    # interior = opaque and the same colour as all 4 neighbours: an anti-aliased blend is a 1-px band,
    # so it never has an interior pixel, while a real shape >= ~0.6 mm across always does.
    k = np.pad(key, 1, constant_values=-1); al = np.pad(a[..., 3], 1)
    inner = (a[..., 3] == 255)
    for dy, dx in ((0, 1), (2, 1), (1, 0), (1, 2)):
        inner &= (k[dy:dy + key.shape[0], dx:dx + key.shape[1]] == key) & (al[dy:dy + key.shape[0], dx:dx + key.shape[1]] == 255)
    px = key[inner] if inner.any() else key[opaque]
    keys, counts = np.unique(px, return_counts=True)
    order = np.argsort(-counts)
    floor = 3
    cand = [int(keys[i]) for i in order if counts[i] >= floor] or [int(keys[order[0]])]
    over = len(cand) > max_colours
    cols = np.array([((k >> 16) & 255, (k >> 8) & 255, k & 255) for k in cand[:max_colours]])
    rgb = a[..., :3]
    d = ((rgb[..., None, :] - cols[None, None, :, :]) ** 2).sum(-1)
    lab = d.argmin(-1); lab[~opaque] = -1
    used = [int(i) for i in np.unique(lab) if i >= 0]
    out = np.full(lab.shape, -1, int)
    for new, old in enumerate(used): out[lab == old] = new
    return out, [tuple(int(v) for v in cols[i]) for i in used], over


def fill_rows(mask, row_mm):
    """boustrophedon rows over a boolean mask -> list of runs [(x0, y, x1)] in mm, in sewing order"""
    import numpy as np
    H = mask.shape[0]; step = max(1, int(round(row_mm * PPM))); runs = []; flip = False
    for y in range(0, H, step):
        row = mask[y]
        if not row.any(): continue
        d = np.diff(np.concatenate([[0], row.astype(int), [0]]))
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        segs = [(s / PPM, y / PPM, (e - 1) / PPM) for s, e in zip(starts, ends)]
        if flip: segs = [(x1, yy, x0) for (x0, yy, x1) in reversed(segs)]
        runs += segs; flip = not flip
    return runs


def build(labels, colours, row_mm, drop):
    import pyembroidery as pe
    pat = pe.EmbPattern(); trims = 0; jumps = 0; kept = []; first = True; last = None
    for ci, rgb in enumerate(colours):
        if ci in drop: continue
        runs = fill_rows(labels == ci, row_mm)
        if not runs: continue
        if not first: pat.add_command(pe.COLOR_CHANGE)
        th = pe.EmbThread(); th.set_color(*rgb); pat.add_thread(th); kept.append(ci); first = False; last = None
        for (x0, y, x1) in runs:
            if last is not None:
                gap = math.hypot(x0 - last[0], y - last[1])
                if gap > TRIM_GAP_MM: pat.add_command(pe.TRIM); trims += 1
                if gap > MAX_STITCH_MM: pat.add_stitch_absolute(pe.JUMP, x0 * 10, y * 10); jumps += 1
            n = max(1, int(math.ceil(abs(x1 - x0) / MAX_STITCH_MM)))
            for k in range(n + 1): pat.add_stitch_absolute(pe.STITCH, (x0 + (x1 - x0) * k / n) * 10, y * 10)
            last = (x1, y)
        pat.add_command(pe.TRIM); trims += 1
    pat.add_command(pe.END)
    return pat, kept, trims, jumps


def readback(dst_path):
    import pyembroidery as pe
    p = pe.read(dst_path); n = 0; mx = 0.0; prev = None
    for x, y, cmd in p.stitches:
        c = cmd & pe.COMMAND_MASK
        if c == pe.STITCH:
            n += 1
            if prev is not None: mx = max(mx, math.hypot(x - prev[0], y - prev[1]) / 10)
            prev = (x, y)
        elif c in (pe.JUMP, pe.TRIM, pe.COLOR_CHANGE): prev = (x, y) if c == pe.JUMP else prev
    return n, round(mx, 2)


def run(a):
    svg = open(a.svg, encoding="utf-8", errors="replace").read()
    check_svg_text(svg)
    answers = json.load(open(a.answers)) if a.answers else {}
    width, fabric, hoop, answers = check_inputs(a.width_mm, a.fabric, a.hoop, answers)
    hw, hh = parse_hoop(hoop)
    img = rasterise(svg, width)
    labels, colours, over = palette(img)
    size = (img.width / PPM, img.height / PPM)
    hexes = ["#%02x%02x%02x" % c for c in colours]
    questions, drop, warnings = [], set(), ["STUB engine: plain fill rows only (no underlay, satin or pull compensation). Do not send to the factory."]
    if over: warnings.append(f"the art has more than {NEEDLES} colours; the stub kept the {NEEDLES} largest and folded the rest into the nearest")
    for ci, hx in enumerate(hexes):
        area = float((labels == ci).sum()) / PPM ** 2
        if area >= SMALL_AREA_MM2: continue
        qid = f"small_{hx[1:]}"
        if qid in answers:
            if answers[qid] == "drop": drop.add(ci)
            continue
        questions.append(dict(id=qid, text=f"Colour {hx} covers only {area:.1f} mm² at this size, too small to stitch cleanly. Keep it or drop it?",
                              options=["keep", "drop"], default="keep"))
    unknown = sorted(set(answers) - {f"small_{h[1:]}" for h in hexes})
    if unknown: warnings.append(f"ignored answers to questions this run did not ask: {', '.join(unknown)}")
    pat, kept, trims, jumps = build(labels, colours, ROW_MM[fabric], drop)
    os.makedirs(a.out, exist_ok=True)
    import pyembroidery as pe
    dst, pes, png = (os.path.join(a.out, f) for f in (f"{a.name}.dst", f"{a.name}.pes", "preview.png"))
    pe.write_dst(pat, dst); pe.write_pes(pat, pes); pe.write_png(pat, png)
    stitches, max_st = readback(dst)
    cc = max(0, len(kept) - 1)
    fits = (size[0] <= hw and size[1] <= hh) or (size[0] <= hh and size[1] <= hw)
    gates = [
        dict(id="engine_real", label="Made by the real digitising engine (S1)", value="stub", limit="svg2dst", pass_=False, hard=True),
        dict(id="fits_hoop", label=f"Fits the {hw}x{hh} hoop", value=f"{size[0]:.0f} x {size[1]:.0f} mm", limit=f"{hw} x {hh} mm", pass_=fits, hard=True),
        dict(id="threads_le_needles", label="Thread colours fit the machine", value=str(len(kept)), limit=f"<= {NEEDLES}", pass_=len(kept) <= NEEDLES, hard=True),
        dict(id="max_stitch", label="Longest stitch", value=f"{max_st} mm", limit="<= 12.1 mm", pass_=max_st <= 12.1, hard=True),
        dict(id="has_stitches", label="File has stitches", value=str(stitches), limit="> 0", pass_=stitches > 0, hard=True),
    ]
    gates = [dict({k: v for k, v in g.items() if k != "pass_"}, **{"pass": g["pass_"]}) for g in gates]
    res = dict(contract=CONTRACT, engine="stub", engine_version="stub-0.1", ok=all(g["pass"] for g in gates if g["hard"]),
               inputs=dict(width_mm=width, fabric=fabric, hoop=hoop, answers=answers),
               size_mm=dict(w=round(size[0], 1), h=round(size[1], 1)),
               stats=dict(stitches=stitches, trims=trims, colour_changes=cc, jumps=jumps,
                          machine_minutes=round(machine_minutes(stitches, trims, cc), 1), max_stitch_mm=max_st),
               threads=[dict(index=i + 1, hex=hexes[ci], name=hexes[ci], brand=None, code=None, delta_e=None) for i, ci in enumerate(kept)],
               gates=gates, questions=questions, warnings=warnings,
               files=dict(dst=os.path.basename(dst), pes=os.path.basename(pes), preview="preview.png"))
    json.dump(res, open(os.path.join(a.out, "result.json"), "w"), indent=1)
    print(f"stub svg2dst: {stitches} stitches, {len(kept)} threads, {trims} trims, ok={res['ok']}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--svg", required=True); ap.add_argument("--width-mm", required=True, type=float)
    ap.add_argument("--fabric", required=True); ap.add_argument("--hoop", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--answers"); ap.add_argument("--name", default="design")
    ap.add_argument("--no-api", action="store_true", help="accepted for parity; this path never calls an API")
    a = ap.parse_args(argv)
    try: return run(a)
    except InputError as e:
        print(f"input refused: {e}", file=sys.stderr)
        try:
            os.makedirs(a.out, exist_ok=True); json.dump(dict(contract=CONTRACT, error=str(e)), open(os.path.join(a.out, "result.json"), "w"))
        except OSError: pass
        return 2


if __name__ == "__main__":
    sys.exit(main())
