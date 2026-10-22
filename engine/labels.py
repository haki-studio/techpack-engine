"""Haki standard labels: the ONE main label + the care label picked from the fibre content (founder 22 Oct 2026).

Every tech pack's labels page uses these files (assets/labels/), never a factory's or an old product's label art.
  main label  = main-label-6.5x2cm-white.pdf, 65 x 20 mm, white ground, black HAKI STUDIOS logo + mark
  care label  = haki-studios-care-label-<fibre>[-white].pdf, 30 x 65 mm, front + back, stitch line at the top
Care label by fibre: 100 % cotton -> "100-cotton"; 90 % cotton / 10 % polyester -> "90-cotton-10-polyester".
Anything else returns None from care_label(): FLAG it on the pack as [MISSING] and ask Haki, never pick the nearest.
"""
import os, re, subprocess
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "labels"))
MAIN = os.path.join(ROOT, "main-label-6.5x2cm-white.pdf")
MAIN_MM = (65.0, 20.0)
CARE_MM = (30.0, 65.0)


def fibre(text):
    """'100 % cotton' / '90% cotton, 10% polyester' -> {'cotton': 100, 'polyester': 10}; only percent + fibre pairs."""
    return {m[1].lower(): int(m[0]) for m in re.findall(r"(\d+)\s*%\s*([A-Za-z]+)", text)}


def care_key(text):
    """the care-label key for a shell composition, or None when no standard care label matches (FLAG, never guess)."""
    fb = fibre(text)
    if sum(fb.values()) != 100: return None
    if fb == {"cotton": 100}: return "100-cotton"
    if fb == {"cotton": 90, "polyester": 10}: return "90-cotton-10-polyester"
    return None


def care_label(text, white=True):
    """path of the care-label PDF for this composition (white-ground version by default), or None (FLAG)."""
    k = care_key(text)
    if k is None: return None
    return os.path.join(ROOT, f"haki-studios-care-label-{k}{'-white' if white else ''}.pdf")


def files_for(text):
    """every label file a pack's zip carries for this composition: main label + the care label (.pdf both grounds + .ai)."""
    k = care_key(text)
    out = [MAIN]
    if k: out += [os.path.join(ROOT, f"haki-studios-care-label-{k}{s}") for s in ("-white.pdf", ".pdf", ".ai")]
    return out


def render(pdf, page=1, dpi=300, cache=None):
    """one PDF page -> PIL image (pdftoppm), cached in the project's out/labels_cache (out/ is gitignored)."""
    cache = cache or os.path.join("out", "labels_cache")
    os.makedirs(cache, exist_ok=True)
    stem = os.path.join(cache, f"{os.path.splitext(os.path.basename(pdf))[0]}_p{page}_{dpi}")
    if not os.path.exists(stem + ".png"):
        subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(page), "-l", str(page), "-singlefile", "-png", pdf, stem], check=True)
    return Image.open(stem + ".png").convert("RGB")
