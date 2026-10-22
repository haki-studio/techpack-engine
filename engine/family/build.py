"""Build a variant's full tech pack: families/<family>/variants/<slug>.yaml -> families/<family>/out/<slug>/

  out/<slug>/<slug>_techpack_<rev>.pdf   merged + recompressed (LESSONS D2)
  out/<slug>/pages/<code>[_n].png        every page rendered (look at them — LESSONS D1)
  with td=<event>.json (TD rows, engine/td): pages named in the rows carry the "TD: ..." notes, and
  out/<slug>/<slug>_td_comment_sheet_<td rev>.pdf + pages/C1*.png is the factory comment sheet
"""
import io, os, sys
import cairosvg
from pypdf import PdfReader, PdfWriter
from .spec import Spec, SpecError, val


def family_dir_of(variant_path):
    d = os.path.dirname(os.path.abspath(variant_path))
    if os.path.basename(d) == "variants": d = os.path.dirname(d)
    if not os.path.exists(os.path.join(d, "family.yaml")):
        raise SpecError(f"{variant_path}: no family.yaml found (keep variants in families/<family>/variants/, or pass --family families/<family>)")
    return d


def page_set(spec):
    fam = val(spec.tree.get("family"))
    if fam == "tee":
        from . import tee_pages
        return tee_pages.pages(spec)
    raise SpecError(f"family '{fam}' has no page set yet (see docs/FAMILIES.md)")


def _plain(x):
    """raw yaml with {proposed: x} / {value: x} leaves read as x"""
    if isinstance(x, dict):
        if set(x) & {"proposed", "value"} and set(x) <= {"proposed", "value", "note", "source"}:
            return _plain(x.get("value", x.get("proposed")))
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, list): return [_plain(v) for v in x]
    return x


def rev_gate(spec):
    """rev log <-> chart agreement (engine/revgate.py) for the family block log and the variant log; raises SpecError"""
    import revgate
    fam = _plain(spec.raw_family.get("revisions")); var = _plain(spec.raw_variant.get("revisions"))
    var_named = {c.get("pom") for e in var or [] for c in e.get("pom_changes") or []}
    reps = [revgate.check(fam, spec.chart, _plain(spec.raw_family.get("rev")), scope="family block (family.yaml revisions)",
                          also_named=var_named),
            revgate.check(var, spec.chart, _plain(spec.raw_variant.get("rev")), scope=f"variant {spec.slug} (revisions)",
                          require_deltas=False)]
    bad = [r for r in reps if not r.ok]
    if bad: raise SpecError("\n".join(r.summary() for r in bad))
    return reps


def shrink(src, dst, maxpx=3000, q=82):
    w = PdfWriter(clone_from=src)
    for page in w.pages:
        for img in page.images:
            im = img.image
            if max(im.size) > maxpx: im.thumbnail((maxpx, maxpx))
            img.replace(im.convert("RGB"), quality=q)
    w.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    w.write(dst)


def write_pdf(svgs, path):
    w = PdfWriter()
    for svg in svgs:
        buf = io.BytesIO(); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=buf)
        w.append(PdfReader(io.BytesIO(buf.getvalue())))
    with open(path, "wb") as fh: w.write(fh)
    return path


def build(variant_path, out_root=None, png=True, family_dir=None, fam_override=None, td=None):
    fdir = family_dir or family_dir_of(variant_path)
    spec = Spec(fdir, variant_path, fam_override=fam_override)
    revs = rev_gate(spec)                                # rev log must agree with the chart before any page is drawn
    out = os.path.join(out_root or os.path.join(fdir, "out"), spec.slug)
    os.makedirs(os.path.join(out, "pages"), exist_ok=True)
    from . import tee_pages as _TP
    import supplier_gate as SG
    sg_rows, sg_flags = _TP.supplier_report(spec)     # a colour count over the supplier's max stops the build
    bad = [r["text"] for r in sg_rows if r["status"] == SG.FAIL]
    if bad: raise SpecError("colour count over the supplier's max:\n  " + "\n  ".join(bad))
    tdi = None
    if td:
        from td import schema as TDS, render as TDR
        tdi = TDS.load(td) if isinstance(td, str) else TDS.parse(td)
    w = PdfWriter(); listing = []
    pset = page_set(spec)
    if tdi:
        codes = {c for c, _, _ in pset}
        stray = sorted({r.page for r in tdi.rows if r.page and r.page not in codes})
        if stray: raise SpecError(f"TD rows name pages this pack does not have: {', '.join(stray)} (pages: {', '.join(sorted(codes))})")
        pset = [(c, ttl, [TDR.annotate(s, tdi.page_rows(c)) for s in svgs]) for c, ttl, svgs in pset]
        from td import trace as TDT                      # numeral-trace gate: fails the build, before anything is written
        td_sheet_svgs = TDR.comment_sheet(tdi)
        td_trace = TDT.enforce(tdi, td_sheet_svgs + [s for c, _, svgs in pset if tdi.page_rows(c) for s in svgs])
    for code, title, svgs in pset:
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
    res = dict(spec=spec, pdf=final, pages=listing, out=out, rev_gate=revs, supplier=(sg_rows, sg_flags))
    if tdi:
        sheet = td_sheet_svgs; res["td_trace"] = td_trace
        res["td_sheet"] = write_pdf(sheet, os.path.join(out, f"{spec.slug}_td_comment_sheet_Rev{tdi.rev}.pdf"))
        for i, svg in enumerate(sheet):
            if png: cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(out, "pages", f"C1{'' if i == 0 else f'_{i + 1}'}.png"), output_width=2400)
    return res


def main(argv=None):
    """family_build.py [--family families/<family>] <variant.yaml> [...]
    Without --family a variant must live in families/<family>/variants/ (its family.yaml is found from there)."""
    import argparse
    ap = argparse.ArgumentParser(prog="family_build.py", description="variant yaml -> full tech pack PDF + page PNGs")
    ap.add_argument("--family", help="family folder (holds family.yaml), e.g. families/tee — needed for a variant kept elsewhere")
    ap.add_argument("--out", help="output root (default families/<family>/out)")
    ap.add_argument("--td", help="TD rows json (engine/td): notes on the pages they name + the factory comment sheet")
    ap.add_argument("variants", nargs="+")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    fdir = os.path.abspath(a.family) if a.family else None
    for v in a.variants:
        try:
            r = build(v, out_root=a.out, family_dir=fdir, td=a.td and os.path.abspath(a.td))
        except (SpecError, ValueError) as e:
            print(f"ERROR in {v}:\n  {e}"); return 1
        n = len(r["spec"].proposed())
        print(f"{r['spec'].name}: {len(r['pages'])} pages -> {r['pdf']} ({os.path.getsize(r['pdf']) / 1e6:.1f} MB)")
        for g in r["rev_gate"]: print(f"  {g.summary()}")
        print("  " + __import__("supplier_gate").summary(*r["supplier"]))
        for x in r["supplier"][0] + r["supplier"][1]:
            if x["status"] != "PASS": print(f"    {x['status']}: {x['text']}")
        print(f"  page PNGs: {os.path.join(r['out'], 'pages')}  ·  {n} values still [proposed — confirm] (page F1)")
        if r.get("td_sheet"): print(f"  TD comment sheet: {r['td_sheet']}\n  {r['td_trace'].summary()}")
    return 0
