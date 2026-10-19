"""Fidelity gates on the SHIPPED size-M DSTs (LESSONS A14 / A15), per motif family -> out/qa_fidelity.json (+ printed tables).
  islets : mockup-traced islet silhouettes (scene META islet_ref)        vs DST cream/sand/pale stitches at those islets
  banks  : close-up cloud silhouette inside the keep-outs (bank_ref_*.npz) vs DST cloud-thread stitches
  stars  : mockup star pixels (bright gold in the sky)                    vs DST gold/pale stitches in the sky
  sea    : qa.uncovered(design sea, DST coverage): design = mockup sea pixels, zip-shadow band (A15) filled from the row,
           minus clouds / islets / keep-outs; every bare gap >= 25 mm2 is listed with its explanation.
usage: python3 qa_fidelity.py [size]"""
import glcore, json, sys, math, pickle
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely import wkt
from shapely.geometry import box
import pyembroidery as pe
import qa, mockmap as MM, front as F
from motifs2 import HEX

size = sys.argv[1] if len(sys.argv) > 1 else "M"
PPM = 4.0
META = pickle.load(open("scene.pkl", "rb"))["meta"]
HZ = META["horizon"]
BBX = {"FR": (-300.0, -40.0, -5.0, 480.0), "FL": (5.0, -40.0, 300.0, 480.0)}
KEY = {v.upper(): k for k, v in HEX.items() if k.startswith("gl_")}
CLOUD = {"gl_pale", "gl_cream", "gl_sand", "gl_sagelt", "gl_sage", "gl_slate", "gl_shadow"}
SEA = {"gl_deep", "gl_teal", "gl_tealt", "gl_foam"}

def grid(P):
    x0, y0, x1, y1 = BBX[P]; return x0, y0, int((x1 - x0)*PPM), int((y1 - y0)*PPM)

def dst_labels(P):
    """colour key per pixel of the shipped DST (thread 0.45 mm), later stitches on top"""
    r = json.load(open(f"out/01_front-scene/{size}/result_{P}.json"))["full"]
    pat = pe.read(r["file"] + ".dst"); cols = [s["col"] for s in r["per_stop"]]; ox, oy = r["origin"]
    x0, y0, W, H = grid(P); keys = sorted(set(cols)); idx = {k: i + 1 for i, k in enumerate(keys)}
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); lw = max(1, int(math.ceil(0.45*PPM)))
    ci = 0; prev = None
    for x, y, c in pat.stitches:
        k = c & pe.COMMAND_MASK; q = ((x/10 + ox - x0)*PPM, (y/10 + oy - y0)*PPM)
        if k == pe.STITCH:
            if prev is not None: d.line([prev, q], fill=idx[cols[min(ci, len(cols)-1)]], width=lw)
            prev = q
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k in (pe.TRIM, pe.JUMP): prev = None
    a = np.array(im); return a, {i: k for k, i in idx.items()}

def raster(geoms, P):
    x0, y0, W, H = grid(P); im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    for g in geoms:
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.geom_type != "Polygon" or p.is_empty: continue
            d.polygon([((x - x0)*PPM, (y - y0)*PPM) for x, y in p.exterior.coords], fill=255)
            for h in p.interiors: d.polygon([((x - x0)*PPM, (y - y0)*PPM) for x, y in h.coords], fill=0)
    return np.array(im) > 0

def mock_rgb(P):
    x0, y0, W, H = grid(P); return np.array(MM.warp(BBX[P], PPM)).astype(np.float32)

def bank_ref(P):
    z = np.load(f"out/bank_ref_{P}.npz"); m = z["mask"]; bx0, by0, bp = float(z["x0"]), float(z["y0"]), float(z["ppm"])
    x0, y0, W, H = grid(P)
    XX, YY = np.meshgrid(x0 + (np.arange(W) + .5)/PPM, y0 + (np.arange(H) + .5)/PPM)
    c = ((XX - bx0)*bp).astype(int); r = ((YY - by0)*bp).astype(int)
    ok = (r >= 0) & (c >= 0) & (r < m.shape[0]) & (c < m.shape[1])
    out = np.zeros((H, W), bool); out[ok] = m[r[ok], c[ok]]; return out

def run():
    res = {}
    art = pickle.load(open(f"front_{size}.pkl", "rb"))
    for P in ("FR", "FL"):
        side = "R" if P == "FR" else "L"
        lab, keys = dst_labels(P); x0, y0, W, H = grid(P)
        is_ = lambda S: np.isin(lab, [i for i, k in keys.items() if k in S])
        YY = y0 + (np.arange(H)[:, None] + .5)/PPM + np.zeros((1, W)); XX = x0 + (np.arange(W)[None, :] + .5)/PPM + np.zeros((H, 1))
        # islets
        refs = [wkt.loads(w) for w in META["islet_ref"]]; refs = [g for g in refs if (g.centroid.x < 0) == (side == "R")]
        cg = F.clip_for(size, side).buffer(-1.0)
        isl_keepout = [dict(x_mm=round(g.centroid.x, 1), y_mm=round(g.centroid.y, 1), sewable_pct=round(100*g.intersection(cg).area/g.area))
                       for g in refs if g.intersection(cg).area < 0.25*g.area]          # < 25 % outside the keep-outs: not sewn (listed)
        refs = [g for g in refs if g.intersection(cg).area >= 0.25*g.area]
        clip = raster([F.clip_for(size, side).buffer(-1.0)], P)
        ref_i = raster(refs, P) & clip                     # what may be sewn: the reference inside this size's keep-outs
        art_isl = raster([r["geom"] for r in art[P] if str(r.get("unit", "")).startswith("islet")], P)
        out_i = is_({"gl_cream", "gl_sand", "gl_pale"}) & ndi.binary_dilation(art_isl, iterations=int(1.5*PPM)) & (YY > HZ + 1.5)
        rows_i = qa.motif_match(ref_i, out_i, PPM)
        # banks
        ref_b = bank_ref(P) & clip; out_b = is_(CLOUD)
        rows_b = qa.motif_match(ref_b, out_b, PPM, min_mm2=200.0)
        # stars: the mockup is ~1 px/mm, so both sides go through the SAME operator: resampled to the mockup's pixel grid
        # (1.2 mm px), then each star = pixels above half its own peak over the sky (half-max silhouette, A14 like with like)
        m = mock_rgb(P); lum = m @ np.array([0.3, 0.59, 0.11])
        sx, sy = META["sun"]
        sungl = ((XX - sx)/75.0)**2 + ((YY - sy)/50.0)**2 < 1                     # sun + glow: own motif, not stars
        sky = (YY < HZ - 6) & ~ndi.binary_dilation(ref_b, iterations=int(3*PPM)) & clip & (np.abs(XX) > 16) & ~sungl   # zip teeth are not stars (A15)
        warm = (m[..., 0] - m[..., 2]) > 45     # star gold, not cream / sage cloud tops
        st = is_({"gl_gold", "gl_pale"}).astype(np.float32)
        k = max(1, int(round(MM.S*PPM)))
        import startrace as STR                     # the SAME observation model the star trace was fitted with
        def halfmax(a, bg):
            pk = ndi.maximum_filter(a, size=int(8*PPM)); return STR.halfmax(a, bg, PPM) & ((pk - bg) > 0.25*(np.percentile(a[sky], 99.9) - bg)) & sky
        mock_res = lambda a: STR.observe(a, PPM)
        bgm = float(np.median(lum[sky])); ref_s = halfmax(lum, bgm)
        lab_s, _ = ndi.label(ref_s); ref_s = np.isin(lab_s, np.unique(lab_s[ref_s & warm]))          # keep the gold blobs whole
        out_s = halfmax(mock_res(st), 0.0)
        rows_s = qa.motif_match(ref_s, out_s, PPM, min_mm2=2.0)
        # a bright gold blob is a STAR row when a mockup star was traced within 4 mm of it; anything else is listed (not hidden)
        tr = [s_.get("traced_at") or s_["mm"] for s_ in META.get("star_trace", [])]
        other_s = []
        for r in rows_s:
            gx, gy = r["x_mm"] + x0, r["y_mm"] + y0
            if not tr or min(math.hypot(gx - a_, gy - b_) for a_, b_ in tr) > 4.0: r["other"] = True
        other_s = [dict(r) for r in rows_s if r.get("other")]; rows_s = [r for r in rows_s if not r.get("other")]
        # sea coverage (A15)
        # the design sea = scene.SEA_DES (mockup sea pixels, welts + zip shadow masked, closed 3 mm), resampled to this grid
        des = META["sea_des"]; dg = des["mask"]
        cc = ((XX - des["x0"])*des["ppm"]).astype(int); rr = ((YY - des["y0"])*des["ppm"]).astype(int)
        okk = (rr >= 0) & (cc >= 0) & (rr < dg.shape[0]) & (cc < dg.shape[1]); design = np.zeros((H, W), bool); design[okk] = dg[rr[okk], cc[okk]]
        design &= (YY > HZ + 1.5)
        clouds = ndi.binary_dilation(is_(CLOUD) | ref_b, iterations=int(2*PPM)) | ndi.binary_dilation(raster(refs, P), iterations=int(2*PPM))
        design &= clip & ~clouds
        cover = ndi.binary_closing(lab > 0, structure=np.ones((int(3*PPM), int(3*PPM))))   # same 3 mm texture closing as the design
        gaps = qa.uncovered(design, cover, PPM)
        gapm = ndi.binary_opening(design & ~cover, structure=qa.disk(1.0, PPM)); dko = ndi.distance_transform_edt(clip) / PPM
        for g in gaps:
            gx, gy = g["x_mm"] + x0, g["y_mm"] + y0
            c0, r0 = int((g["x_mm"] - g["w_mm"]/2)*PPM), int((g["y_mm"] - g["h_mm"]/2)*PPM)
            gm_ = gapm[r0:r0 + int(g["h_mm"]*PPM) + 1, c0:c0 + int(g["w_mm"]*PPM) + 1]; dk_ = dko[r0:r0 + gm_.shape[0], c0:c0 + gm_.shape[1]]
            near_ko = float((dk_[gm_] < 3.0).mean()) if gm_.any() else 0.0
            g["x_mm"], g["y_mm"] = round(gx, 1), round(gy, 1); g["near_keepout"] = round(near_ko, 2)
            # Rev E3: only a keep-out explains a gap (dashes stop at the keep-out clearance); the glitter now lies ON the sea
            g["why"] = ("keep-out edge: dashes end at the keep-out clearance" if near_ko >= 0.6 else "UNEXPLAINED")
        for rows in (rows_i, rows_b, rows_s, other_s):
            for r in rows: r["x_mm"] = round(r["x_mm"] + x0, 1); r["y_mm"] = round(r["y_mm"] + y0, 1)
        res[P] = dict(islets=rows_i, islets_in_keepout=isl_keepout, banks=rows_b, stars=rows_s, bright_not_star=other_s, sea_gaps=gaps)
        if "debug" in sys.argv:
            v = np.zeros((H, W, 3), np.uint8); v[design] = (40, 90, 90); v[cover & design] = (90, 200, 190); v[cover & ~design] = (90, 90, 90)
            gm = ndi.binary_opening(design & ~cover, structure=np.ones((4, 4))); v[gm] = (255, 0, 0)
            v[ref_i & ~out_i] = (255, 200, 0); v[out_i & ~ref_i] = (0, 0, 255); v[out_i & ref_i] = (255, 255, 255)
            Image.fromarray(v).save(f"out/qa_debug_{P}.png")
            v2 = (np.stack([lum]*3, -1)*0.5).astype(np.uint8); v2[ref_s & ~out_s] = (255, 200, 0); v2[out_s & ~ref_s] = (0, 90, 255); v2[ref_s & out_s] = (255, 255, 255)
            Image.fromarray(v2[: int((HZ + 40 - y0)*PPM)]).save(f"out/qa_debug_stars_{P}.png")
            tiles = []
            for fam, rf, ot, rows in (("islets", ref_i, out_i, rows_i), ("stars", ref_s, out_s, rows_s)):
                for r in rows:
                    if r["ok"]: continue
                    cx_, cy_ = int((r["x_mm"] - x0)*PPM), int((r["y_mm"] - y0)*PPM); hw = int(16*PPM)
                    sl = (slice(max(0, cy_ - hw), cy_ + hw), slice(max(0, cx_ - hw), cx_ + hw))
                    t_ = np.zeros(rf[sl].shape + (3,), np.uint8) + 25; t_[rf[sl] & ~ot[sl]] = (255, 200, 0); t_[ot[sl] & ~rf[sl]] = (0, 90, 255); t_[rf[sl] & ot[sl]] = (255, 255, 255)
                    mk_ = np.array(MM.warp((x0 + sl[1].start/PPM, y0 + sl[0].start/PPM, x0 + sl[1].stop/PPM, y0 + sl[0].stop/PPM), PPM).resize(t_.shape[1::-1]))
                    tiles.append(np.concatenate([mk_, t_], 1))
            if tiles:
                wmax = max(x.shape[1] for x in tiles); tiles = [np.pad(x, ((0, 4), (0, wmax - x.shape[1]), (0, 0)), constant_values=255) for x in tiles]
                Image.fromarray(np.concatenate(tiles, 0)).resize((wmax*2, sum(x.shape[0] for x in tiles)*2), Image.NEAREST).save(f"out/qa_fail_{P}.png")
    json.dump(res, open("out/qa_fidelity.json", "w"), indent=1)
    return res

if __name__ == "__main__":
    res = run()
    for P, d in res.items():
        for fam in ("islets", "banks", "stars"):
            rows = d[fam]; bad = [r for r in rows if not r["ok"]]
            print(P, fam, f"{len(rows) - len(bad)}/{len(rows)} pass", [(r["x_mm"], r["y_mm"], r["iou"], r["w_ratio"], r["h_ratio"]) for r in bad])
        print(P, "sea gaps", [(g["x_mm"], g["y_mm"], g["area_mm2"], g["why"]) for g in d["sea_gaps"]])
