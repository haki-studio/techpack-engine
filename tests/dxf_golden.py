"""Golden hashes of the DEFAULT-variant pattern DXFs (Drum Island block, no embroidery marks).

The DXF carries write-time stamps ($TDCREATE / $TDUPDATE, ezdxf "@ <iso time>" xdata); those are blanked before
hashing, everything else must be byte-identical. Regenerate ONLY when a default-variant change is intended:
    python3 tests/dxf_golden.py --write
"""
import os, re, sys, json, hashlib, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "fixtures", "dxf_default_golden.json")
_TD = re.compile(r"(\$TD(?:CREATE|UPDATE)\r?\n 40\r?\n)[^\r\n]*")
_AT = re.compile(r"( @ )\d{4}-\d\d-\d\dT[0-9:.+-]+")

def normalized(path):
    t = open(path, encoding="utf-8", errors="surrogateescape").read()
    return _AT.sub(r"\1<time>", _TD.sub(r"\1<time>", t))

def digest(path): return hashlib.sha256(normalized(path).encode("utf-8", "surrogateescape")).hexdigest()

def current():
    import pattern_out as PO, pattern as PT
    keep = PO.emb_marks
    PO.emb_marks = lambda size, pl=None: {}        # embroidery marks need built art (out/); geometry only here
    try:
        H = {}
        with tempfile.TemporaryDirectory() as d:
            for sz in PT.SIZES:
                p = os.path.join(d, f"{sz}.dxf"); PO.write_dxf([sz], p); H[sz] = digest(p)
            p = os.path.join(d, "ALL.dxf"); PO.write_dxf(PT.SIZES, p); H["ALL"] = digest(p)
        return H
    finally:
        PO.emb_marks = keep

if __name__ == "__main__":
    sys.path[:0] = [HERE]
    import conftest  # noqa: F401  (engine + Drum Island on sys.path, cwd = project inputs)
    H = current()
    if "--write" in sys.argv: json.dump(H, open(GOLDEN, "w"), indent=1); print("wrote", GOLDEN)
    print(json.dumps(H, indent=1))
