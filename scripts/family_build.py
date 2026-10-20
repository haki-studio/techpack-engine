#!/usr/bin/env python3
"""One command: a variant yaml -> its full tech pack PDF + page PNGs.

  python3 scripts/family_build.py families/tee/variants/alabasta.yaml

Output: families/<family>/out/<slug>/<slug>_techpack_<rev>.pdf and pages/*.png. See docs/FAMILIES.md.
Uses the shared venv (~/.venvs/techpack) automatically if the current python lacks the engine deps."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    import shapely, cairosvg, yaml, pypdf  # noqa: F401
except ImportError:
    for v in (os.path.join(ROOT, ".venv"), os.path.expanduser("~/.venvs/techpack")):
        py = os.path.join(v, "bin", "python3")
        if os.path.exists(py) and os.path.realpath(sys.prefix) != os.path.realpath(v):
            os.execv(py, [py] + sys.argv)
    sys.exit("engine deps missing: run scripts/setup_wsl.sh (LESSONS E5)")
sys.path.insert(0, os.path.join(ROOT, "engine"))
from family.build import main  # noqa: E402

if __name__ == "__main__":
    args = [a if a.startswith("--") or (i and sys.argv[i].startswith("--")) else os.path.abspath(a)
            for i, a in enumerate(sys.argv[1:])]
    sys.exit(main(args))
