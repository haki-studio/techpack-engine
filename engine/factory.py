"""Factory profile + the F1 "Factory requests" page every pack carries (strike-off, frames, thread card, quote basis).

The profile lives in factory.json at the repo root. Builders read frames / needles / speed from it instead of hard-coding
360 x 360, and every pack asks the factory for what we still don't know. When the factory answers, update factory.json and
rebuild — the page shrinks to what is still open.

  prof = factory.load()
  frame = factory.largest_frame(prof)            # (w, h) mm, for split_clip(frame=...)
  svgs = factory.requests_page(style="Moon jacket", strikeoff=[...], threads=[...], pieces=[...], page="F1")
"""
import json, os
from sheet import SW, SH, INK, MUTED, RED, ORANGE, GREEN, t, header, doc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = dict(name="[proposed — confirm]", frames_mm=[[360, 360]], frames_confirmed=False, needles=15,
               needles_confirmed=False, spm=750, thread_brands=["Madeira Polyneon", "Isacord"],
               thread_card_received=False, price_basis="unknown")
DE_ASK = 3.0          # thread matches worse than this (ΔE2000) go on the lab-dip / thread-card list


def load(path=None):
    p = path or os.path.join(ROOT, "factory.json")
    prof = dict(DEFAULT)
    if os.path.exists(p): prof.update({k: v for k, v in json.load(open(p)).items() if not k.startswith("_")})
    return prof


def largest_frame(prof=None):
    """largest frame by area (w, h) in mm"""
    fr = (prof or load())["frames_mm"]
    return tuple(max(fr, key=lambda wh: wh[0] * wh[1]))


def machine_hours(stitches, prof=None, trims=0, trim_s=6.0, colour_changes=0, change_s=4.0):
    """sewing time at the factory's speed + a few seconds per trim / colour change (one head)"""
    spm = (prof or load())["spm"]
    return (stitches / spm * 60 + trims * trim_s + colour_changes * change_s) / 3600


def requests_page(style, strikeoff, threads, pieces, page="F1", prof=None):
    """One A4 page. strikeoff: [{"file", "piece", "stitches", "trims"}]  (size M — what to sew first)
    threads: [{"name", "code", "de"}]  (de = ΔE2000 of the best catalogue match to the mockup colour)
    pieces: [{"piece", "w", "h", "hoopings"}]  art size in mm and how many 360-frame hoopings it needs today"""
    prof = prof or load()
    o = header(f"{page} · Factory requests — please answer before bulk", f"{style} · what we need from the embroidery factory", page)
    y = 34
    def h2(s):
        nonlocal y; o.append(t(12, y, s, 3.2, 700)); y += 5
    def line(s, col=INK, x=16, size=2.4):
        nonlocal y; o.append(t(x, y, s, size, 400, col)); y += 3.9

    h2("1  Strike-off (sew-out) — first, before any bulk")
    line("Sew these size-M files on the real shell fabric (washed, as in bulk), with the proposed threads + backing:")
    for s in strikeoff:
        line(f"•  {s['file']}  —  {s['piece']}  ·  {s['stitches']:,} stitches  ·  {s['trims']} trims", x=20)
    line("Send back: (a) photos straight-on in daylight + one raking-light close-up per colour area, with a ruler in shot;")
    line("(b) design size measured after sewing vs the spec (width x height, mm) — tells us the pull / shrink;")
    line("(c) puckering, show-through of the fabric, thread breaks, any area you would digitise differently;")
    line("(d) actual run time per hooping and your price for it.")
    y += 2

    h2("2  Frames + machine")
    fr = ", ".join(f"{w:.0f} x {h:.0f}" for w, h in prof["frames_mm"])
    if not prof["frames_confirmed"]:
        line(f"We assumed {fr} mm frames and {prof['needles']}-needle heads [proposed — confirm]. Please list every frame size you", ORANGE)
        line("have (inner sewing field, mm), including border / jacket-back frames, and the needles per head.", ORANGE)
        big = [p for p in pieces if p.get("hoopings", 1) > 1]
        if big:
            line("These pieces need more than one hooping on our assumed frame — a larger frame removes the joins:")
            for p in big:
                line(f"•  {p['piece']}: art {p['w']:.0f} x {p['h']:.0f} mm → {p['hoopings']} hoopings today", x=20)
    else:
        line(f"Frames on file: {fr} mm; {prof['needles']} needles. Files are split for these.", GREEN)
    y += 2

    h2("3  Thread card / lab dip")
    weak = [th for th in threads if th.get("de") is not None and th["de"] > DE_ASK]
    if not prof["thread_card_received"]:
        line(f"Please send a physical thread card for {' / '.join(prof['thread_brands'])} or dip these colours on the shell:")
    if weak:
        for th in weak:
            line(f"•  {th['name']} — closest {th['code']} is ΔE {th['de']:.1f} from the design colour; propose your nearest match", RED, x=20)
    else:
        line("All proposed threads match the design within ΔE 3 — confirm against the card.", GREEN)
    y += 2

    h2("4  Quote basis")
    line("How do you price embroidery: per 1,000 stitches, per trim, per hooping, or per piece? Price the strike-off files above.")
    line("Total stitches and trims per piece are on the embroidery pages (G).", MUTED)
    return [doc(o)]
