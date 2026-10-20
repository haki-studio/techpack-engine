"""Default-preservation probe (engine M2-M6): dst2.make_pattern DEFAULT output on a 28-region synthetic motif (no
builder / keep_order / threads) -> sha256 of the DST + PES. Expected on main since M2: dst 84ff50ea74938675 /
pes 1ecd8f657db3f53a. Run from any checkout:

  PYTHONPATH=<checkout>/engine python3 scripts/byteid_probe.py

scripts/identity_check.sh runs this plus the M5 wb svgrun DST and the Castle crop DST."""
import hashlib, os, sys, tempfile
from shapely.geometry import Point, LineString
import dst2, tech

regs = []
cols = [("bark", "tatami", "TR"), ("slate", "satin", "LF-shade"), ("barkdk", "bean", "LF-vein")]
for i in range(7):
    for j in range(4):
        ox, oy = 30.0 * i, 25.0 * j
        k = (i + j) % 3; col, st, grp = cols[k]
        if st == "tatami": g = LineString([(ox, oy), (ox + 12, oy + 8), (ox + 22, oy + 9)]).buffer(3.5)
        elif st == "satin": g = Point(ox + 10, oy + 10).buffer(4.5)
        else: g = LineString([(ox + 2, oy + 2), (ox + 18, oy + 6)]).buffer(0.35)
        regs.append(dict(col=col, geom=g, st=st, ang="auto" if st != "bean" else None, grp=grp, layer=5 + k, z=1 + k))
assert len(regs) == 28
vis = dst2.clean_vis(regs)
stops = dst2.merge_stops(tech.stops(vis, tech.STITCH_LAYER))
pat, st = dst2.make_pattern(vis, stops, (100, 50))
d = tempfile.mkdtemp(); base = os.path.join(d, "t"); dst2.write(pat, base)
dh = hashlib.sha256(open(base + ".dst", "rb").read()).hexdigest()[:16]; ph = hashlib.sha256(open(base + ".pes", "rb").read()).hexdigest()[:16]
print(os.path.dirname(dst2.__file__), "regions", len(vis), "stitches", st["stitches"], "trims", st["trims"], "dst", dh, "pes", ph)
sys.exit(0 if (dh, ph) == ("84ff50ea74938675", "1ecd8f657db3f53a") else 1)
