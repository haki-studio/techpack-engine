"""Documents in LESSONS D3 order: results (DST read-back) -> placement check -> element specs -> embroidery pack -> shrink.
Garment pages (T) are added when the hooded pattern exists. usage: python3 build_all.py"""
import rbcore
import subprocess, sys, os
def run(*a): print(">", *a, flush=True); subprocess.run([sys.executable, *a], check=True)
run("make_current.py"); run("emb_place.py"); run("compare.py"); run("run_spec.py"); run("pack.py")
src = f"out/HAKI_{rbcore.SHORT}_EMBROIDERY-PACK_{rbcore.REV_EMB.replace(' ', '')}.pdf"
run("shrink.py", src, src.replace(".pdf", "_small.pdf"), "3000", "82")
print("MB", round(os.path.getsize(src)/1e6, 1), "->", round(os.path.getsize(src.replace(".pdf", "_small.pdf"))/1e6, 1))
run("finish.py")
