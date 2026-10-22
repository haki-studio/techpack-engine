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
REAL = server.REAL_CLI


@pytest.fixture(autouse=True)
def stub_only(monkeypatch):
    """S1 put the real CLI at scripts/svg2dst.py and it always wins: the stub tests (and the HTTP fixture, whose handler
    calls convert) pin it off; a test that wants an engine sets REAL_CLI itself."""
    monkeypatch.setattr(server, "REAL_CLI", "/nonexistent/svg2dst.py")


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


# ---- review round 1 (6afea3a0) -------------------------------------------------------------------------------

@pytest.fixture
def listener():
    """A local HTTP server that counts every request it gets: any fetch by the renderer shows up here."""
    import http.server
    hits = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path); self.send_response(200); self.send_header("Content-Type", "image/svg+xml"); self.end_headers()
            self.wfile.write(b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>')
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", hits
    srv.shutdown()


def remote_payloads(base):
    nested = base64.b64encode(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><image xlink:href="{base}/nested.png" width="5" height="5"/></svg>'.encode()).decode()
    head = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 20 20">'
    return [
        head + f'<image xlink:href="{base}/href.png" width="10" height="10"/><rect width="5" height="5"/></svg>',
        head + f'<style>@import "{base}/import.css";</style><rect width="5" height="5"/></svg>',
        head + f'<rect width="5" height="5" style="fill:url({base}/u.svg#g)"/></svg>',
        head + f'<rect width="5" height="5" style="fill:u\\72l({base}/esc.svg#g)"/></svg>',
        head + f'<image xlink:href="data:image/svg+xml;base64,{nested}" width="10" height="10"/></svg>',
    ]


def test_renderer_fetches_nothing_remote(listener):
    """The real SSRF defence is cairosvg>=2.7 with unsafe=False (CVE-2023-27586); the regex is only a second layer."""
    import stub_engine
    base, hits = listener
    for svg in remote_payloads(base):
        try: stub_engine.rasterise(svg, 20)
        except Exception: pass   # a refusal to render is fine; a fetch is not
    assert hits == []


def test_listener_can_see_a_fetch(listener):
    """Control for the test above: with unsafe=True the same payloads DO reach the listener, so zero hits means something."""
    import cairosvg
    base, hits = listener
    for svg in remote_payloads(base)[:2]:
        try: cairosvg.svg2png(bytestring=svg.encode(), output_width=20, unsafe=True)
        except Exception: pass
    assert hits, "the listener saw nothing even with unsafe=True; the no-fetch test proves nothing"


def test_cairosvg_pinned_to_a_safe_version():
    import cairosvg, re as _re
    req = open(os.path.join(ROOT, "requirements.txt")).read()
    assert _re.search(r"^cairosvg\s*>=\s*2\.7\.1", req, _re.M), "requirements.txt must pin cairosvg>=2.7.1"
    major, minor = (int(x) for x in cairosvg.__version__.split(".")[:2])
    assert (major, minor) >= (2, 7)


def test_server_listens_on_ipv4_and_ipv6():
    import socket
    srv = server.DualStackServer(("::", 0), server.make_handler(SECRET, threading.BoundedSemaphore(1), env=STUB_ENV))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        for host in ("127.0.0.1", "[::1]"):
            with urllib.request.urlopen(f"http://{host}:{port}/healthz", timeout=5) as r: assert json.loads(r.read())["ok"] is True
    finally: srv.shutdown()


def test_main_uses_the_dual_stack_server():
    src = open(os.path.join(SVC, "server.py")).read()
    assert 'DualStackServer(("::", port)' in src and '"0.0.0.0"' not in src


@pytest.mark.parametrize("mut,needle", [
    (lambda r: r["threads"][0].update(hex="navy"), "hex"),
    (lambda r: r["threads"][0].update(index=0), "index"),
    (lambda r: r.pop("size_mm"), "size_mm"),
    (lambda r: r.update(warnings="x"), "warnings"),
    (lambda r: r["questions"].append(dict(id="q" * 81, text="t", options=["a"])), "question id"),
])
def test_check_result_matches_plm_contract(mut, needle):
    r = json.loads(json.dumps(server.convert(dict(REQ), env=STUB_ENV)["result"]))
    contract.check_result(json.loads(json.dumps(r)))
    mut(r)
    with pytest.raises(ValueError, match=needle): contract.check_result(r)


def test_real_engine_round_trip(monkeypatch):
    """the S1 engine behind the worker: no run.yaml, contract-valid result, a real DST, engine_real passes"""
    monkeypatch.setattr(server, "REAL_CLI", REAL)
    r = server.convert(dict(REQ), env={k: v for k, v in os.environ.items() if k != "SVG2DST_ALLOW_STUB"})
    res = contract.check_result(r["result"])
    gates = {g["id"]: g["pass"] for g in res["gates"]}
    assert res["engine"] == "svg2dst" and gates["engine_real"] is True and gates["fits_hoop"] is True
    assert len(res["threads"]) == 3 and res["stats"]["stitches"] > 500
    assert base64.b64decode(r["files"]["dst"])[:3] == b"LA:"
