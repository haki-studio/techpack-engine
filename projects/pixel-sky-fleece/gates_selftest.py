"""Red-then-green for the fix-round gates (prove-the-guard): each gate must go RED on a planted defect of its own class
and GREEN on the shipped files. Writes out/stitch/gates_selftest.json; exit 1 if any guard fails to fire.
  colour  : yellow <-> gold swapped on E2's stops (the PR #28 defect: a gold sparkle sewn yellow) -> colour rows fail
  A15     : the last stop's stitches erased from E2's masks (a motif left bare)                 -> uncovered rows
  A16     : one part's angle undeclared ("auto")                                                 -> angle_coherence row"""
import json, sys
import gates_fl as G

def main():
    green = G.run(["E2"], write=False)["E2"]
    out = dict(green=dict(colour_fail=sum(not r["ok"] for r in green["colour"]), uncovered=len(green["uncovered"]),
                          coherence=len(green["coherence"])))
    r = G.run(["E2"], mutate="swap_threads", write=False)["E2"]; out["colour_red"] = sum(not c["ok"] for c in r["colour"])
    r = G.run(["E2"], mutate="drop_stop", write=False)["E2"]; out["a15_red"] = len(r["uncovered"])
    r = G.run(["E2"], mutate="auto_angle", write=False)["E2"]; out["a16_red"] = len(r["coherence"])
    ok = (out["green"]["colour_fail"] == 0 and out["green"]["uncovered"] == 0 and out["green"]["coherence"] == 0
          and out["colour_red"] > 0 and out["a15_red"] > 0 and out["a16_red"] > 0)
    out["ok"] = ok; json.dump(out, open("out/stitch/gates_selftest.json", "w"), indent=1); print(out)
    return 0 if ok else 1

if __name__ == "__main__": sys.exit(main())
