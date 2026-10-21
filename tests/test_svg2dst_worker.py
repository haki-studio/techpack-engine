"""S2: the svg2dst worker (services/svg2dst) + the stub engine honour docs/SVG2DST.md. No Anthropic API."""
import base64, json, os, subprocess, sys, threading, urllib.error, urllib.request
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVC = os.path.join(ROOT, "services", "svg2dst")
sys.path.insert(0, SVC)
import contract, server  # noqa: E402

SECRET = "s" * 40
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120"><rect x="5" y="5" width="120" height="60" fill="#1b2a4a"/>'
       '<circle cx="160" cy="60" r="35" fill="#e94f37"/><circle cx="20" cy="110" r="1.5" fill="#f4d35e"/></svg>')
REQ = dict(svg=SVG, file_name="a.svg", width_mm=90, fabric="twill", hoop="300x300", answers={})
STUB_ENV = dict(os.environ, SVG2DST_ALLOW_STUB="true")


@pytest.mark.parametrize("svg,needle", [
    ('<svg><image href="http://169.254.169.254/latest/meta-data"/></svg>', "outside file"),
    ('<svg><image xlink:href="file:///etc/passwd"/></svg>', "outside file"),
    ('<svg><rect style="fill:url(https://x.test/p.svg#g)"/></svg>', "outside file"),
    ('<!DOCTYPE svg [<!ENTITY a "aaaa">]><svg>&a;</svg>', "DOCTYPE"),
    ('<html>not svg</html>', "not an SVG"),
])
def test_svg_refusals(svg, needle):
    with pytest.raises(contract.InputError, match=needle): contract.check_svg_text(svg)


def test_svg_allows_internal_refs_and_data_uris():
    contract.check_svg_text('<svg><use href="#a"/><rect fill="url(#g)"/><image href="data:image/png;base64,AAAA"/></svg>')


@pytest.mark.parametrize("w,fab,hoop", [(0, "twill", "300x300"), (90, "silk", "300x300"), (90, "twill", "big"), ("x", "twill", "300x300")])
def test_input_refusals(w, fab, hoop):
    with pytest.raises(contract.InputError): contract.check_inputs(w, fab, hoop, {})


def test_stub_round_trip_and_question_loop():
    r = server.convert(dict(REQ), env=STUB_ENV)
    res = contract.check_result(r["result"])
    assert res["engine"] == "stub" and res["ok"] is False                       # the stub can never read OK
    assert {g["id"]: g["pass"] for g in res["gates"]}["engine_real"] is False
    assert [t["hex"] for t in res["threads"]] == ["#1b2a4a", "#e94f37", "#f4d35e"]
    assert res["stats"]["stitches"] > 500 and res["stats"]["colour_changes"] == 2
    assert base64.b64decode(r["files"]["dst"])[:3] == b"LA:"                    # a DST header
    assert base64.b64decode(r["files"]["pes"])[:4] == b"#PES"
    assert base64.b64decode(r["files"]["preview_png"])[:4] == b"\x89PNG"
    q = [q["id"] for q in res["questions"]]
    assert q == ["small_f4d35e"]
    r2 = server.convert(dict(REQ, answers={"small_f4d35e": "drop"}), env=STUB_ENV)["result"]
    assert r2["questions"] == [] and [t["hex"] for t in r2["threads"]] == ["#1b2a4a", "#e94f37"]


def test_stub_fits_hoop_gate():
    res = server.convert(dict(REQ, width_mm=350), env=STUB_ENV)["result"]
    assert {g["id"]: g["pass"] for g in res["gates"]}["fits_hoop"] is False


def test_no_engine_is_503(monkeypatch):
    monkeypatch.setattr(server, "REAL_CLI", "/nonexistent/svg2dst.py")
    with pytest.raises(server.EngineError) as e: server.convert(dict(REQ), env={k: v for k, v in os.environ.items() if k != "SVG2DST_ALLOW_STUB"})
    assert e.value.status == 503


def test_real_cli_wins_over_stub(tmp_path, monkeypatch):
    real = tmp_path / "svg2dst.py"; real.write_text("")
    monkeypatch.setattr(server, "REAL_CLI", str(real))
    assert server.engine_cli(STUB_ENV) == (str(real), "svg2dst")


def test_engine_never_sees_the_secret(tmp_path, monkeypatch):
    spy = tmp_path / "spy.py"
    spy.write_text("import os, sys\nprint(sorted(os.environ.items()))\nsys.exit(1)\n")
    monkeypatch.setattr(server, "REAL_CLI", str(spy))
    with pytest.raises(server.EngineError) as e: server.convert(dict(REQ), env=dict(STUB_ENV, SVG2DST_SHARED_SECRET=SECRET))
    assert e.value.status == 500 and "PATH" in e.value.log_tail and SECRET not in e.value.log_tail


@pytest.fixture
def http():
    srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(SECRET, threading.BoundedSemaphore(1), env=STUB_ENV))
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def call(base, body, token=SECRET):
    req = urllib.request.Request(base + "/v1/convert", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())


def test_http_auth_and_errors(http):
    assert call(http, REQ, token=None)[0] == 401
    assert call(http, REQ, token="s" * 39)[0] == 401
    assert call(http, REQ, token=SECRET + "x")[0] == 401
    st, body = call(http, dict(REQ, svg='<svg><image href="https://evil.test/x.png"/></svg>'))
    assert st == 422 and "outside file" in body["error"]
    st, body = call(http, REQ)
    assert st == 200 and body["result"]["engine"] == "stub" and body["files"]["dst"]
    with urllib.request.urlopen(http + "/healthz", timeout=5) as r: assert json.loads(r.read()) == {"ok": True, "engine": "stub"}


def test_server_refuses_to_start_without_secret():
    p = subprocess.run([sys.executable, os.path.join(SVC, "server.py")], env={"PATH": os.environ["PATH"]}, capture_output=True, text=True, timeout=30)
    assert p.returncode != 0 and "SVG2DST_SHARED_SECRET" in p.stderr
