"""scripts/storage.py (LESSONS E9): cleanup keeps the newest revision and every deliverable, skips running builds."""
import os, sys, json, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("storage", os.path.join(ROOT, "scripts", "storage.py"))
ST = importlib.util.module_from_spec(spec); spec.loader.exec_module(ST)

def test_superseded_keeps_newest():
    fs = ["o/X_FULL-TECHPACK_RevA.pdf", "o/X_FULL-TECHPACK_RevB.pdf", "o/X_FULL-TECHPACK_RevC.pdf",
          "o/X_RevB-F_files.zip", "o/X_RevC-G_files.zip", "o/X_EMBROIDERY-PACK_RevG.pdf", "o/pattern.dxf"]
    old = ST.superseded(fs)
    assert sorted(old) == ["o/X_FULL-TECHPACK_RevA.pdf", "o/X_FULL-TECHPACK_RevB.pdf", "o/X_RevB-F_files.zip"]

def test_plan_skips_running_and_keeps_deliverables(tmp_path, monkeypatch):
    def mk(p, n=10):
        p = tmp_path / p; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"x" * n)
    mk("projects/done/out/A_RevA.pdf"); mk("projects/done/out/A_RevB.pdf"); mk("projects/done/out/pkg/a.dst"); mk("projects/done/back.pkl")
    mk("projects/run/out/B_RevA.pdf"); mk("projects/run/out/B_RevB.pdf")
    (tmp_path / "projects/run/STATUS.json").write_text(json.dumps({"stage": "stitch"}))
    monkeypatch.setattr(ST, "ROOT", str(tmp_path))
    got = {os.path.relpath(p, tmp_path) for p, _, _ in ST.plan()}
    assert got == {"projects/done/out/A_RevA.pdf", "projects/done/out/pkg"}
    deep = {os.path.relpath(p, tmp_path) for p, _, _ in ST.plan(deep=True)}
    assert "projects/done/back.pkl" in deep and not any(p.startswith("projects/run") for p in deep)
