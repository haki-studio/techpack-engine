"""Build a variant's full tech pack: families/<family>/variants/<slug>.yaml -> families/<family>/out/<slug>/

  out/<slug>/<slug>_techpack_<rev>.pdf   merged + recompressed (LESSONS D2)
  out/<slug>/pages/<code>[_n].png        every page rendered (look at them — LESSONS D1)
"""
import io, os, sys
import cairosvg
from pypdf import PdfReader, PdfWriter
from .spec import Spec, SpecError, val


def family_dir_of(variant_path):
    d = os.path.dirname(os.path.abspath(variant_path))
    if os.path.basename(d) == "variants": d = os.path.dirname(d)
    if not os.path.exists(os.path.join(d, "family.yaml")):
        raise SpecError(f"{variant_path}: no family.yaml found (variants live in families/<family>/variants/)")
    return d


def page_set(spec):
    fam = val(spec.tree.get("family"))
    if fam == "tee":
        from . import tee_pages
        return tee_pages.pages(spec)
    raise SpecError(f"family '{fam}' has no page set yet (see docs/FAMILIES.md)")


def shrink(src, dst, maxpx=3000, q=82):
    w = PdfWriter(clone_from=src)
    for page in w.pages:
        for img in page.images:
            im = img.image
            if max(im.size) > maxpx: im.thumbnail((maxpx, maxpx))
            img.replace(im.convert("RGB"), quality=q)
    w.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    w.write(dst)


def build(variant_path, out_root=None, png=True, family_dir=None, fam_override=None):
    fdir = family_dir or family_dir_of(variant_path)
    spec = Spec(fdir, variant_path, fam_override=fam_override)
    out = os.path.join(out_root or os.path.join(fdir, "out"), spec.slug)
    os.makedirs(os.path.join(out, "pages"), exist_ok=True)
    w = PdfWriter(); listing = []
    for code, title, svgs in page_set(spec):
        for i, svg in enumerate(svgs):
            name = code if len(svgs) == 1 else f"{code}_{i + 1}"
            buf = io.BytesIO(); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=buf)
            w.append(PdfReader(io.BytesIO(buf.getvalue())))
            if png:
                p = os.path.join(out, "pages", f"{name}.png")
                cairosvg.svg2png(bytestring=svg.encode(), write_to=p, output_width=2400)
                listing.append((name, title, p))
            else:
                listing.append((name, title, None))
    rev = str(val(spec.var.get("rev"), "RevA")).replace(" ", "")
    raw = os.path.join(out, f"{spec.slug}_techpack_{rev}_raw.pdf"); final = os.path.join(out, f"{spec.slug}_techpack_{rev}.pdf")
    with open(raw, "wb") as fh: w.write(fh)
    shrink(raw, final); os.remove(raw)
    return dict(spec=spec, pdf=final, pages=listing, out=out)


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: python3 scripts/family_build.py families/tee/variants/<slug>.yaml [more.yaml ...]"); return 2
    for v in argv:
        try:
            r = build(v)
        except SpecError as e:
            print(f"ERROR in {v}:\n  {e}"); return 1
        n = len(r["spec"].proposed())
        print(f"{r['spec'].name}: {len(r['pages'])} pages -> {r['pdf']} ({os.path.getsize(r['pdf']) / 1e6:.1f} MB)")
        print(f"  page PNGs: {os.path.join(r['out'], 'pages')}  ·  {n} values still [proposed — confirm] (page F1)")
    return 0
