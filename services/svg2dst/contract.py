"""The svg2dst/1 contract (docs/SVG2DST.md): the input vocabulary and the result.json check.

Shared by the worker (server.py) and the stub engine, so both refuse the same inputs. No Anthropic API.
"""
import re

CONTRACT = "svg2dst/1"
FABRICS = ("twill", "denim", "jersey", "fleece", "pique", "sherpa")
HOOP_RE = re.compile(r"^(\d{2,3})x(\d{2,3})$")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
WIDTH_MIN_MM, WIDTH_MAX_MM = 5.0, 700.0
MAX_SVG_BYTES = 2 * 1024 * 1024
MAX_ANSWERS = 100
NEEDLES = 12

# A reference that makes the renderer reach outside the file: a remote URL (SSRF from inside our network)
# or a local path (reads the container's disk). cairosvg follows both. Only same-file refs ("#id") and
# inline data: URIs are allowed.
_REF_RE = re.compile(r"""(?:xlink:href|href|src)\s*=\s*["']\s*([^"'\s>]+)|url\(\s*["']?\s*([^"')\s]+)""", re.I)


class InputError(ValueError):
    """The request is wrong in a way the operator can fix; the message is safe to show."""


def parse_hoop(hoop):
    m = HOOP_RE.match(str(hoop or "").strip())
    if not m: raise InputError(f"hoop must look like 300x300 (mm), got {hoop!r}")
    w, h = int(m.group(1)), int(m.group(2))
    if not (20 <= w <= 800 and 20 <= h <= 800): raise InputError(f"hoop {w}x{h} mm is out of range")
    return w, h


def check_svg_text(svg):
    if not isinstance(svg, str) or not svg.strip(): raise InputError("svg is empty")
    if len(svg.encode("utf-8")) > MAX_SVG_BYTES: raise InputError(f"svg is larger than {MAX_SVG_BYTES // 1024} KB")
    if "<svg" not in svg[:200000].lower(): raise InputError("that file is not an SVG (no <svg> element)")
    # DOCTYPE/ENTITY = XML entity expansion (billion laughs) and XXE. Design tools do not need it.
    if re.search(r"<!DOCTYPE|<!ENTITY", svg, re.I): raise InputError("SVG files with a DOCTYPE or ENTITY are refused; re-export without it")
    for m in _REF_RE.finditer(svg):
        ref = (m.group(1) or m.group(2) or "").strip()
        if not ref or ref.startswith("#") or ref.lower().startswith("data:"): continue
        raise InputError(f"the SVG links to an outside file ({ref[:80]}); embed images or remove the link")


def check_inputs(width_mm, fabric, hoop, answers):
    try: w = float(width_mm)
    except (TypeError, ValueError): raise InputError("width_mm must be a number")
    if not (WIDTH_MIN_MM <= w <= WIDTH_MAX_MM): raise InputError(f"width_mm must be between {WIDTH_MIN_MM:g} and {WIDTH_MAX_MM:g}")
    if fabric not in FABRICS: raise InputError(f"fabric must be one of {', '.join(FABRICS)}")
    parse_hoop(hoop)
    answers = answers or {}
    if not isinstance(answers, dict) or len(answers) > MAX_ANSWERS: raise InputError("answers must be an object of question id -> option")
    for k, v in answers.items():
        if not isinstance(k, str) or not isinstance(v, str) or len(k) > 80 or len(v) > 200:
            raise InputError("answers must map a question id to one of its options (strings)")
    return w, fabric, hoop, answers


def check_result(r):
    """Raise ValueError if result.json does not follow svg2dst/1. Returns r."""
    def need(cond, what):
        if not cond: raise ValueError(f"result.json: {what}")
    need(isinstance(r, dict), "not an object")
    need(r.get("contract") == CONTRACT, f"contract must be {CONTRACT!r}")
    need(r.get("engine") in ("svg2dst", "stub"), "engine must be svg2dst or stub")
    need(isinstance(r.get("ok"), bool), "ok must be a boolean")
    s = r.get("stats") or {}
    for k in ("stitches", "trims", "colour_changes", "machine_minutes", "max_stitch_mm"):
        need(isinstance(s.get(k), (int, float)) and not isinstance(s.get(k), bool), f"stats.{k} must be a number")
    need(isinstance(s.get("jumps", 0), (int, float)) and not isinstance(s.get("jumps", 0), bool), "stats.jumps must be a number")
    z = r.get("size_mm") or {}
    need(all(isinstance(z.get(k), (int, float)) and not isinstance(z.get(k), bool) for k in ("w", "h")), "size_mm needs w and h numbers")
    need(isinstance(r.get("threads"), list), "threads must be a list")
    for t in r["threads"]:
        need(isinstance(t, dict) and isinstance(t.get("hex"), str) and _HEX.match(t["hex"]), "each thread needs a #rrggbb hex")
        need(isinstance(t.get("index"), int) and not isinstance(t.get("index"), bool) and t["index"] >= 1, "thread index must be an int >= 1")
    need(isinstance(r.get("warnings", []), list) and all(isinstance(w, str) for w in r.get("warnings", [])), "warnings must be a list of strings")
    need(isinstance(r.get("gates"), list), "gates must be a list")
    for g in r["gates"]:
        need(isinstance(g, dict) and isinstance(g.get("id"), str) and isinstance(g.get("pass"), bool) and isinstance(g.get("hard"), bool),
             "each gate needs id, pass (bool), hard (bool)")
    need(isinstance(r.get("questions"), list), "questions must be a list")
    for q in r["questions"]:
        need(isinstance(q, dict) and isinstance(q.get("id"), str) and isinstance(q.get("text"), str)
             and isinstance(q.get("options"), list) and q["options"], "each question needs id, text, options")
        need(len(q["id"]) <= 80 and all(isinstance(o, str) and 0 < len(o) <= 200 for o in q["options"]),
             "question id <= 80 chars, options 1..200 chars")
    need(r["ok"] == all(g["pass"] for g in r["gates"] if g["hard"]), "ok must equal 'every hard gate passed'")
    f = r.get("files") or {}
    for k in ("dst", "pes", "preview"): need(isinstance(f.get(k), str), f"files.{k} missing")
    return r
