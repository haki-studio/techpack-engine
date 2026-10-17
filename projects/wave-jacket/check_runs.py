"""which size/piece stitch files are complete + newer than their art (run before make_current)"""
import os, json
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]; PS = ["BK", "FR", "FL", "SR", "SL"]
todo = []
for s in SIZES:
    a = f"art_{s}.pkl"; ta = os.path.getmtime(a) if os.path.exists(a) else None
    row = []
    for P in PS:
        rp = f"out/01_wave/{s}/result_{P}.json"; ok = False
        if ta and os.path.exists(rp):
            r = json.load(open(rp)); f_ = r.get("full", {}).get("file", "") + ".dst"
            ok = os.path.exists(f_) and os.path.getmtime(f_) > ta and (r.get("hoopings") is not None)
        row.append("ok" if ok else "--")
        if not ok: todo.append((s, P))
    print(s, "art" if ta else "NOART", row)
print("TODO", " ".join(f"{s}:{P}" for s, P in todo))
