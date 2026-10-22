"""Tofu guard (review PR #38): no CJK font is installed system-wide, so a CJK / Hangul char inside a plain SVG
<text> element renders as a missing-glyph box. CJK must go through kcdoc.auto (font outlines). Raises on any hit."""
import re
_TXT = re.compile(r"<text\b[^>]*>(.*?)</text>", re.S)
_CJK = re.compile(r"[⺀-鿿가-힯豈-﫿＀-￯]")

def hits(svg):
    return [m.group(1) for m in _TXT.finditer(svg) if _CJK.search(m.group(1))]

def check(svg, page):
    h = hits(svg)
    if h: raise SystemExit(f"TOFU on {page}: CJK in plain <text> (use kcdoc.auto): " + " | ".join(s[:80] for s in h))
    return svg
