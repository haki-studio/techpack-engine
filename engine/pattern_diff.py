"""pattern_diff — read a pattern (DXF, or a vector 1:1 PDF), check its scale on BOTH axes, walk the seam pairs a TD
maps, and diff it against the last signed pattern / the signed POM (TD design §4 "Pattern version").

The TD only maps pieces + edges and judges; every number comes from here.

  pat = pattern_diff.read("factory_rev2.dxf")            # or .pdf; never a photo
  print(pattern_diff.piece_table(pat))                    # piece / edge index / length — what the TD maps from
  rep = pattern_diff.run(pat, mapping, signed=read("rev1.dxf"))
  rep.lines()                                             # "can't diff: need vector PDF or DXF" when the scale fails

Scale check:
  DXF  the drawing unit must be stated ($INSUNITS mm / cm / in, or a "Units:" piece text; both stated and different =
       refused) AND a horizontal and a vertical 100 mm reference, each next to a "100 mm" label, must be drawn: a file
       that claims cm but is drawn in mm reads its ruler as 1000 mm and is refused. pattern_out.write_dxf draws them.
  PDF  a scale box (a side of 100 mm) AND a vertical 100 mm ruler, each next to a "100 mm" label.
  Both: each axis must measure 100 ± 0.5 mm (a plot at 97 % fails before any seam is walked), candidates on one axis
  must agree (else "ambiguous"), and inside that band every length is CORRECTED per axis by 100 / measured — a 1.004
  y-scale would otherwise put 4 mm on a 1000 mm seam, more than the 3 mm fault this tool must catch.
Edges: each piece's sew line (AAMA layer 14; dashed in a PDF) — else its cut line (layer 1), reported as "cut line
(includes seam allowance)" — split at corners (turn > 12°; a TD sums edges with a list). Edge 0 starts at the first corner.

mapping (json from the TD):
  {"pieces": {"front": {"name": "F01"} | {"index": 0}, ...},
   "seams":  [{"name": "side seam", "a": ["front", 2], "b": ["back", [4, 5]], "ease_mm": 0, "tol_mm": 2}],
   "curves": [{"name": "front crotch", "piece": "front", "edge": 0}],               # depth + length of a crotch curve
   "poms":   [{"name": "front rise", "piece": "front", "edge": 0, "target_mm": 265, "tol_mm": 3, "source": "..."}]}
  an edge is an index or a list of indices (summed in order).
"""
import math, re
from shapely.geometry import Polygon, Point

MM = {1: 25.4, 4: 1.0, 5: 10.0, 6: 1000.0}           # $INSUNITS -> mm
UNIT_MM = {"mm": 1.0, "cm": 10.0, "in": 25.4}
CORNER_DEG = 12.0          # Drum Island underarm (armhole -> side) turns 15.7°; over-splitting is fixed by summing edges, merging is not
SCALE_TOL = 0.5
MIN_PIECE_MM2 = 300.0      # a closed outline smaller than this is a mark, not a piece
CANT = "can't diff: need vector PDF or DXF"


class CantDiff(ValueError):
    """the scale or the units could not be verified — no number from this file can be trusted"""


class RPiece:
    def __init__(self, label, sew, cut, size=None):
        self.label, self.sew, self.cut, self.size = label, sew, cut, size
        self.line = "sew line" if sew else "cut line (includes seam allowance)"
        self.edges = split_edges(sew or cut)


class Pattern:
    def __init__(self, path, kind, pieces, scale, notes):
        self.path, self.kind, self.pieces, self.scale, self.notes = path, kind, pieces, scale, notes


def alen(p): return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(p, p[1:]))


def _clean(pts):
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-6: out.append((float(p[0]), float(p[1])))
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-6: out.pop()
    return out


def split_edges(pts, deg=CORNER_DEG):
    """closed polyline -> [edge pts] split at corners (direction change > deg); edge 0 starts at the first corner"""
    pts = _clean(pts); n = len(pts)
    def turn(i):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        a1 = math.atan2(b[1] - a[1], b[0] - a[0]); a2 = math.atan2(c[1] - b[1], c[0] - b[0])
        return abs((math.degrees(a2 - a1) + 180) % 360 - 180)
    corners = [i for i in range(n) if turn(i) > deg]
    if not corners: return [pts + [pts[0]]]
    edges = []
    for k, c in enumerate(corners):
        d = corners[(k + 1) % len(corners)]
        idx = list(range(c, d + 1)) if d > c else list(range(c, n)) + list(range(0, d + 1))
        edges.append([pts[i] for i in idx])
    return edges


# ----------------------------------------------------------------------------- DXF
def read_dxf(path):
    import ezdxf
    doc = ezdxf.readfile(path)
    notes = []
    ins = doc.header.get("$INSUNITS", 0)
    unit = MM.get(ins)
    raw = []          # (label, size, {layer: [pts]}, units_text)
    msp = doc.modelspace()
    def collect(ents, into):
        for e in ents:
            t = e.dxftype(); lay = e.dxf.layer
            if t in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in (e.get_points("xy") if t == "LWPOLYLINE" else [v.dxf.location for v in e.vertices])]
                closed = e.closed if t == "LWPOLYLINE" else e.is_closed
                into["poly"].append((lay, pts, closed))
            elif t == "LINE":
                into["poly"].append((lay, [(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])], False))
            elif t in ("TEXT", "MTEXT"):
                txt = e.dxf.text if t == "TEXT" else e.text
                into["text"].append((txt, (e.dxf.insert[0], e.dxf.insert[1])))
    loose = {"poly": [], "text": []}
    for e in msp:
        if e.dxftype() == "INSERT":
            g = {"poly": [], "text": []}
            collect(e.virtual_entities(), g)
            raw.append(g)
        else:
            collect([e], loose)
    if loose["poly"]: raw.append(loose)
    pieces, rulers, texts = [], [], []
    for g in raw:
        texts += g["text"]
        label = next((re.sub(r"^Piece Name:\s*", "", t) for t, _ in g["text"] if t.startswith("Piece Name")), None)
        size = next((t.split(":", 1)[1].strip() for t, _ in g["text"] if t.startswith("Size:")), None)
        cuts = [p for lay, p, c in g["poly"] if c and lay == "1"]
        sews = [p for lay, p, c in g["poly"] if c and lay == "14"]
        others = [p for lay, p, c in g["poly"] if lay not in ("1", "14", "7")]     # 7 = grain line, never a ruler
        rulers += [p for p in others]
        if g is loose and not cuts:                       # a plain drawing: every big closed polyline is a piece
            cuts = [p for lay, p, c in g["poly"] if c and Polygon(p).area > MIN_PIECE_MM2]
        for i, c in enumerate(sorted(cuts, key=lambda p: -Polygon(p).area)):
            cp = Polygon(c)
            sew = next((s for s in sews if cp.buffer(0.5).contains(Polygon(s))), None)
            pieces.append(RPiece(label if len(cuts) == 1 else f"{label or 'piece'} #{i + 1}", sew, c, size))
    u = {m.group(1).lower() for t, _ in texts for m in [re.search(r"Units:\s*(mm|cm|in)\b", t, re.I)] if m}
    if len(u) > 1: raise CantDiff(f"{CANT} — the file states more than one unit: {sorted(u)}")
    if u and unit is not None and UNIT_MM[next(iter(u))] != unit:
        raise CantDiff(f"{CANT} — $INSUNITS says {unit:g} mm per unit but the piece text says 'Units: {next(iter(u))}'")
    if unit is None and u:
        unit = UNIT_MM[u.pop()]; notes.append("units from the piece text")
    if unit is None: raise CantDiff(f"{CANT} — {path}: the drawing unit is not stated ($INSUNITS or 'Units:' text)")
    scale = {"x": None, "y": None, "unit_mm": unit}
    for p in pieces:
        p.sew = [(x * unit, y * unit) for x, y in p.sew] if p.sew else None
        p.cut = [(x * unit, y * unit) for x, y in p.cut]
        p.edges = split_edges(p.sew or p.cut)
    sx, sy = _scale([[(x * unit, y * unit) for x, y in r] for r in rulers],
                    [(t, (q[0] * unit, q[1] * unit)) for t, q in texts], path)
    scale["x"], scale["y"] = sx, sy
    scale["fx"], scale["fy"] = _correct(pieces, sx, sy)
    return Pattern(path, "dxf", pieces, scale, notes)


# ----------------------------------------------------------------------------- vector PDF
def _bez(p0, p1, p2, p3, n=12):
    return [((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0],
             (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1])
            for t in (i / n for i in range(1, n + 1))]


def _mul(m, n):
    a, b, c, d, e, f = m; A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F)


def read_pdf(path):
    """vector paths from every page (pypdf content streams; cm/q/Q, m l c v y h re, dash state), in mm"""
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    rd = PdfReader(path); K = 25.4 / 72
    pieces, rulers, texts = [], [], []
    for pno, pg in enumerate(rd.pages, 1):
        ops = ContentStream(pg.get_contents(), rd).operations
        ctm = (1, 0, 0, 1, 0, 0); stack = []; dashed = False; paths = []; sub = []; cur = None; start = None
        def T(x, y):
            a, b, c, d, e, f = ctm; return ((a * x + c * y + e) * K, (b * x + d * y + f) * K)
        def close_sub(closed):
            nonlocal sub
            if len(sub) > 1: paths.append((sub, closed))
            sub = []
        page_paths = []
        for args, op in ops:
            op = op.decode() if isinstance(op, bytes) else op
            if op == "q": stack.append((ctm, dashed))
            elif op == "Q": ctm, dashed = stack.pop() if stack else (ctm, dashed)
            elif op == "cm": ctm = _mul(tuple(float(x) for x in args), ctm)
            elif op == "d": dashed = len(args[0]) > 0
            elif op == "m": close_sub(False); cur = (float(args[0]), float(args[1])); start = cur; sub = [T(*cur)]
            elif op == "l": cur = (float(args[0]), float(args[1])); sub.append(T(*cur))
            elif op in ("c", "v", "y"):
                a = [float(x) for x in args]
                if op == "c": p1, p2, p3 = (a[0], a[1]), (a[2], a[3]), (a[4], a[5])
                elif op == "v": p1, p2, p3 = cur, (a[0], a[1]), (a[2], a[3])
                else: p1, p2, p3 = (a[0], a[1]), (a[2], a[3]), (a[2], a[3])
                sub += [T(*q) for q in _bez(cur, p1, p2, p3)]; cur = p3
            elif op == "h":
                close_sub(True); cur = start
            elif op == "re":
                close_sub(False); x, y, w, h = (float(v) for v in args)
                paths.append(([T(x, y), T(x + w, y), T(x + w, y + h), T(x, y + h)], True))
            elif op in ("S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"):
                close_sub(op in ("s", "b", "b*"))
                if op != "n": page_paths += [(p, c, dashed, op) for p, c in paths]
                paths = []
        ptexts = []
        def vt(text, cm, tm, *_):
            if text.strip():
                x, y = tm[4], tm[5]; a, b, c, d, e, f = cm
                ptexts.append((text.strip(), ((a * x + c * y + e) * K, (b * x + d * y + f) * K)))
        pg.extract_text(visitor_text=vt)
        texts.extend(ptexts)
        def is_scale_box(p):
            c = _ruler_candidates([p], ptexts); return len(p) == 4 and bool(c["x"] or c["y"])
        closed = [(p, d) for p, c, d, op in page_paths if op not in ("f", "F", "f*") and (c or math.hypot(p[0][0] - p[-1][0], p[0][1] - p[-1][1]) < 0.2) and len(p) > 2]
        big = [(p, d) for p, d in closed if Polygon(p).buffer(0).area > MIN_PIECE_MM2 and not is_scale_box(p)]
        cuts = [p for p, d in big if not d]; sews = [p for p, d in big if d]
        here = []                                          # pieces of THIS page (each page has its own origin)
        for c in sorted(cuts, key=lambda p: -Polygon(p).buffer(0).area):
            cp = Polygon(c).buffer(0.5)
            if any(Polygon(q.cut).buffer(0.5).contains(Polygon(c).buffer(0)) for q in here): continue   # a line inside a piece
            sew = next((s for s in sews if cp.contains(Polygon(s).buffer(0))), None)
            here.append(RPiece(f"page{pno}" + (f".{len(here) + 1}" if here else ""), sew, c))
        pieces += here
        rulers += [p for p, c, d, _ in page_paths if len(p) <= 4]
    sx, sy = _scale(rulers, texts, path)
    fx, fy = _correct(pieces, sx, sy)
    return Pattern(path, "pdf", pieces, {"x": sx, "y": sy, "fx": fx, "fy": fy, "unit_mm": 1.0}, [])


def _seg_dist(q, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]; L2 = ax * ax + ay * ay or 1e-9
    t = max(0.0, min(1.0, ((q[0] - a[0]) * ax + (q[1] - a[1]) * ay) / L2))
    return math.hypot(q[0] - a[0] - t * ax, q[1] - a[1] - t * ay)


def _ruler_candidates(paths, texts, near=15.0):
    """{'x': [lengths], 'y': [lengths]} in mm: horizontal / vertical segments of 100 ± 5 mm (a box side or a line) within
    `near` mm of a text saying '100 mm'. Every candidate is kept, so an ambiguous drawing can be refused."""
    labels = [q for t, q in texts if re.search(r"\b100\s*mm\b", t)]
    out = {"x": [], "y": []}
    if not labels: return out
    for p in paths:
        segs = list(zip(p, p[1:] + ([p[0]] if len(p) == 4 else [])))
        for a, b in segs:
            dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1]); L = math.hypot(dx, dy)
            if not 95 <= L <= 105: continue
            if not any(_seg_dist(q, a, b) < near for q in labels): continue
            ax = "x" if dy < 0.02 * L else ("y" if dx < 0.02 * L else None)
            if ax: out[ax].append(L)
    return out


def _scale(paths, texts, path):
    """measure the 100 mm references on BOTH axes; refuse when one is missing, ambiguous or off by more than SCALE_TOL;
    otherwise return per-axis correction factors (100 / measured) so a residual scale error never reaches a seam"""
    c = _ruler_candidates(paths, texts)
    if not c["x"] or not c["y"]:
        raise CantDiff(f"{CANT} — {path}: need scale check on both axes: a 100 mm reference next to a '100 mm' label "
                       f"on x AND on y (found x: {len(c['x'])}, y: {len(c['y'])})")
    res = {}
    for ax in ("x", "y"):
        v = c[ax]
        if max(v) - min(v) > 0.05:
            raise CantDiff(f"{CANT} — ambiguous scale reference on {ax}: " + " / ".join(f"{x:.2f}" for x in sorted(set(round(x, 2) for x in v)))
                           + " mm next to a '100 mm' label (a piece edge or grain line beside the ruler?)")
        m = sum(v) / len(v)
        if abs(m - 100) > SCALE_TOL:
            raise CantDiff(f"{CANT} — scale check failed: the 100 mm reference measures {m:.1f} mm on {ax} (printed / exported scaled?)")
        res[ax] = m
    return res["x"], res["y"]


def _correct(pieces, sx, sy):
    fx, fy = 100.0 / sx, 100.0 / sy
    for p in pieces:
        p.sew = [(x * fx, y * fy) for x, y in p.sew] if p.sew else None
        p.cut = [(x * fx, y * fy) for x, y in p.cut]
        p.edges = split_edges(p.sew or p.cut)
    return fx, fy


def read(path):
    p = path.lower()
    if p.endswith(".dxf"): return read_dxf(path)
    if p.endswith(".pdf"): return read_pdf(path)
    raise CantDiff(f"{CANT} — {path} is not a DXF or a vector PDF (a photo gives shape go/no-go only, never numbers)")


# ----------------------------------------------------------------------------- the diff
def piece_table(pat):
    out = []
    for i, p in enumerate(pat.pieces):
        out.append(f"[{i}] {p.label}" + (f" size {p.size}" if p.size else "") + f" · {p.line}")
        for j, e in enumerate(p.edges):
            out.append(f"    edge {j}: {alen(e):.1f} mm  ({e[0][0]:.0f},{e[0][1]:.0f}) → ({e[-1][0]:.0f},{e[-1][1]:.0f})")
    return "\n".join(out)


def _piece(pat, ref):
    if "index" in ref:
        if ref["index"] >= len(pat.pieces): raise KeyError(f"piece index {ref['index']} not in the file ({len(pat.pieces)} pieces)")
        return pat.pieces[ref["index"]]
    hits = [p for p in pat.pieces if p.label and p.label.split()[0] == ref["name"]]
    if len(hits) != 1: raise KeyError(f"piece '{ref['name']}': {len(hits)} matches in {pat.path}")
    return hits[0]


def edge_pts(pat, mapping, piece, edge):
    pc = _piece(pat, mapping["pieces"][piece])
    idx = edge if isinstance(edge, list) else [edge]
    pts = []
    for i in idx:
        if i >= len(pc.edges): raise KeyError(f"{piece} has {len(pc.edges)} edges, not edge {i}")
        pts += pc.edges[i] if not pts else pc.edges[i][1:]
    return pc, pts


def crotch(pts):
    """depth (vertical extent, along the grain = y) and arc length of a crotch / rise curve, mm"""
    ys = [p[1] for p in pts]; xs = [p[0] for p in pts]
    return dict(depth=max(ys) - min(ys), extension=max(xs) - min(xs), length=alen(pts))


class Report:
    def __init__(self, pat):
        self.pat, self.rows, self.flags = pat, [], []

    @property
    def ok(self): return not self.flags

    def lines(self):
        s = self.pat.scale
        head = [f"pattern_diff {self.pat.path} ({self.pat.kind}, {len(self.pat.pieces)} pieces) — scale verified on both "
                f"axes: the 100 mm references measure x {s['x']:.2f} / y {s['y']:.2f} mm -> every length corrected "
                f"x {s['fx']:.4f} / y {s['fy']:.4f}"]
        return head + self.rows + [f"FLAG {f}" for f in self.flags]


def run(pat, mapping, signed=None):
    """walk the mapped seams / curves / POMs; with `signed` (the last signed pattern, read()) also diff every mapped
    edge against it. Unsigned deltas over tolerance are FLAGs."""
    rep = Report(pat)
    for s in mapping.get("seams", []):
        pa, a = edge_pts(pat, mapping, *s["a"]); pb, b = edge_pts(pat, mapping, *s["b"])
        la, lb = alen(a), alen(b); ease = float(s.get("ease_mm", 0)); tol = float(s.get("tol_mm", 2))
        mis = la - lb - ease
        line = (f"seam {s['name']}: {s['a'][0]} {la:.1f} mm vs {s['b'][0]} {lb:.1f} mm, intended ease {ease:g} mm "
                f"-> mismatch {mis:+.1f} mm (tol ±{tol:g})" + ("" if pa.sew and pb.sew else " [cut line: includes seam allowance]"))
        rep.rows.append(line)
        if abs(mis) > tol: rep.flags.append(line)
    for c in mapping.get("curves", []):
        _, pts = edge_pts(pat, mapping, c["piece"], c["edge"]); m = crotch(pts)
        rep.rows.append(f"curve {c['name']}: depth {m['depth']:.1f} mm, extension {m['extension']:.1f} mm, length {m['length']:.1f} mm")
    for p in mapping.get("poms", []):
        _, pts = edge_pts(pat, mapping, p["piece"], p["edge"]); L = alen(pts)
        d = L - float(p["target_mm"]); tol = float(p.get("tol_mm", 3))
        line = (f"POM {p['name']}: pattern {L:.1f} mm vs signed {float(p['target_mm']):g} mm -> {d:+.1f} mm (tol ±{tol:g})"
                + (f" [{p['source']}]" if p.get("source") else ""))
        rep.rows.append(line)
        if abs(d) > tol: rep.flags.append(line)
    if signed is not None:
        done = set()
        for item in mapping.get("seams", []) + mapping.get("curves", []) + mapping.get("poms", []):
            refs = [tuple(item["a"]), tuple(item["b"])] if "a" in item else [(item["piece"], item["edge"])]
            for pc, e in refs:
                key = (pc, str(e))
                if key in done: continue
                done.add(key)
                _, new = edge_pts(pat, mapping, pc, e)
                try: _, old = edge_pts(signed, mapping, pc, e)
                except KeyError as ex:
                    rep.flags.append(f"vs signed: {pc} edge {e}: {ex}"); continue
                d = alen(new) - alen(old); tol = float(item.get("tol_mm", 2))
                line = f"vs signed: {pc} edge {e}: {alen(old):.1f} -> {alen(new):.1f} mm ({d:+.1f})"
                rep.rows.append(line)
                if abs(d) > tol: rep.flags.append(line + " — unsigned change over tolerance")
    return rep


def main(argv=None):
    import argparse, json, sys
    ap = argparse.ArgumentParser(prog="pattern_diff", description="walk mapped seams on a DXF / vector PDF pattern")
    ap.add_argument("pattern"); ap.add_argument("--map"); ap.add_argument("--signed")
    a = ap.parse_args(argv)
    try:
        pat = read(a.pattern)
        if not a.map: print(piece_table(pat)); return 0
        rep = run(pat, json.load(open(a.map)), read(a.signed) if a.signed else None)
    except CantDiff as e:
        print(e); return 2
    print("\n".join(rep.lines()))
    return 0 if rep.ok else 1
