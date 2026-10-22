#!/usr/bin/env python3
"""TD rows json -> the factory comment sheet (PDF + PNG + plain text). Checks the json first; a bad row stops it.

  python3 scripts/td_render.py projects/<slug>/td/<event>.json [--out projects/<slug>/td/out]

For a family pack, the notes go on the pack pages too: python3 scripts/family_build.py --td <event>.json <variant.yaml>"""
import argparse, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    import cairosvg, pypdf, yaml  # noqa: F401
except ImportError:
    for v in (os.path.join(ROOT, ".venv"), os.path.expanduser("~/.venvs/techpack")):
        py = os.path.join(v, "bin", "python3")
        if os.path.exists(py) and os.path.realpath(sys.prefix) != os.path.realpath(v):
            os.execv(py, [py] + sys.argv)
    sys.exit("engine deps missing: run scripts/setup_wsl.sh (LESSONS E5)")
sys.path.insert(0, os.path.join(ROOT, "engine"))
import cairosvg  # noqa: E402
from td import schema, render  # noqa: E402
from family.build import write_pdf  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(prog="td_render.py", description=__doc__.splitlines()[0])
    ap.add_argument("td"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        td = schema.load(a.td); pages = render.comment_sheet(td); lines = render.sheet_lines(td)
    except schema.TDInputError as e:
        print(f"ERROR in {a.td}:\n  {e}"); return 1
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.td)), "out")
    os.makedirs(out, exist_ok=True)
    stem = os.path.join(out, f"{td.product}_td_comment_sheet_Rev{td.rev}")
    write_pdf(pages, stem + ".pdf")
    for i, svg in enumerate(pages):
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{stem}_{i + 1}.png", output_width=2400)
    with open(stem + ".txt", "w") as fh: fh.write("\n".join(s for _, s in lines) + "\n")
    print(f"{len(td.rows)} TD rows -> {stem}.pdf ({len(pages)} page(s)) + .txt + page PNGs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
