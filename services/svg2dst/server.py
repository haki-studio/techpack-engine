"""svg2dst worker — HTTP wrapper around scripts/svg2dst.py for the PLM "SVG → DST" window. CPU only, no Anthropic API.

  POST /v1/convert   Authorization: Bearer $SVG2DST_SHARED_SECRET
                     {"svg": "<svg ...>", "file_name": "x.svg", "width_mm": 90, "fabric": "twill",
                      "hoop": "300x300", "answers": {"q001": "column"}}
                  -> 200 {"result": <result.json>, "files": {"dst", "pes", "preview_png"} (base64),
                          "duration_ms", "log_tail"}
                     400 bad JSON / 401 bad secret / 413 too big / 422 input refused (engine exit 2 or our checks)
                     429 busy / 500 engine crashed / 503 no engine installed / 504 timed out
  GET  /healthz   -> {"ok": true, "engine": "svg2dst" | "stub" | null}   (no auth, says nothing else)

Environment:
  SVG2DST_SHARED_SECRET   required, >= 32 chars; the server refuses to start without it
  SVG2DST_ALLOW_STUB      "true" lets the stub engine answer while scripts/svg2dst.py does not exist (S1 not merged)
  SVG2DST_TIMEOUT_S       per-run engine timeout, default 240
  SVG2DST_MAX_CONCURRENCY parallel engine runs, default 1 (CPU bound)
  PORT                    default 8080
"""
import base64, hmac, json, os, socket, subprocess, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from contract import MAX_SVG_BYTES, InputError, check_inputs, check_result, check_svg_text  # noqa: E402

REAL_CLI = os.path.join(ROOT, "scripts", "svg2dst.py")
STUB_CLI = os.path.join(HERE, "stub_engine.py")
MAX_BODY = MAX_SVG_BYTES * 2 + 64 * 1024   # JSON-escaped SVG can grow; anything bigger is refused unread


def engine_cli(env=os.environ):
    """(path, name) of the CLI to run, or (None, None). The real one always wins when present."""
    if os.path.exists(REAL_CLI): return REAL_CLI, "svg2dst"
    if env.get("SVG2DST_ALLOW_STUB", "").strip().lower() == "true": return STUB_CLI, "stub"
    return None, None


class EngineError(Exception):
    def __init__(self, status, message, log_tail=""):
        super().__init__(message); self.status = status; self.message = message; self.log_tail = log_tail


def convert(req, env=os.environ, timeout_s=None):
    """Run one conversion. req = the POST body (dict). Returns the 200 payload or raises InputError / EngineError."""
    if not isinstance(req, dict): raise InputError("body must be a JSON object")
    svg = req.get("svg"); check_svg_text(svg)
    width, fabric, hoop, answers = check_inputs(req.get("width_mm"), req.get("fabric"), req.get("hoop"), req.get("answers"))
    cli, name = engine_cli(env)
    if not cli: raise EngineError(503, "no svg2dst engine installed (scripts/svg2dst.py missing and SVG2DST_ALLOW_STUB is not true)")
    timeout_s = timeout_s or float(env.get("SVG2DST_TIMEOUT_S", "240"))
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="svg2dst-") as tmp:
        src, out = os.path.join(tmp, "in.svg"), os.path.join(tmp, "out")
        with open(src, "w", encoding="utf-8") as f: f.write(svg)
        cmd = [sys.executable, cli, "--svg", src, "--width-mm", repr(width), "--fabric", fabric, "--hoop", hoop,
               "--out", out, "--name", "design", "--no-api"]
        if answers:
            ap = os.path.join(tmp, "answers.json")
            with open(ap, "w") as f: json.dump(answers, f)
            cmd += ["--answers", ap]
        # The engine gets a clean environment: never the shared secret, never anything else of ours.
        child_env = {k: v for k, v in env.items() if k in ("PATH", "HOME", "LANG", "LC_ALL", "PYTHONPATH", "TMPDIR")}
        child_env["PYTHONPATH"] = os.pathsep.join(p for p in (os.path.join(ROOT, "engine"), child_env.get("PYTHONPATH", "")) if p)
        try:
            p = subprocess.run(cmd, cwd=ROOT, env=child_env, capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            raise EngineError(504, f"the engine took longer than {timeout_s:.0f} s")
        log_tail = ((p.stdout or "") + (p.stderr or ""))[-4000:]
        if p.returncode == 2:
            msg = (p.stderr or "").strip().splitlines()[-1:] or ["input refused"]
            raise InputError(msg[0].removeprefix("input refused: "))
        if p.returncode != 0: raise EngineError(500, f"the engine crashed (exit {p.returncode})", log_tail)
        try:
            result = check_result(json.load(open(os.path.join(out, "result.json"))))
        except (OSError, ValueError) as e:
            raise EngineError(500, f"the engine wrote no valid result.json: {e}", log_tail)
        if result["engine"] != name: raise EngineError(500, f"result says engine {result['engine']!r} but {name!r} ran", log_tail)
        files = {}
        for key, fname in (("dst", result["files"]["dst"]), ("pes", result["files"]["pes"]), ("preview_png", result["files"]["preview"])):
            fp = os.path.join(out, os.path.basename(fname))
            if not os.path.exists(fp): raise EngineError(500, f"the engine did not write {fname}", log_tail)
            files[key] = base64.b64encode(open(fp, "rb").read()).decode("ascii")
    return dict(result=result, files=files, duration_ms=int((time.time() - t0) * 1000), log_tail=log_tail)


class DualStackServer(ThreadingHTTPServer):
    """Listens on "::" with IPV6_V6ONLY off, so IPv6 and IPv4 both reach it. Railway private DNS
    (*.railway.internal) resolves to IPv6 only in legacy environments; an IPv4-only bind is unreachable."""
    address_family = socket.AF_INET6
    daemon_threads = True

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def make_handler(secret, slots, env=os.environ):
    class H(BaseHTTPRequestHandler):
        server_version = "svg2dst/1"

        def log_message(self, fmt, *args):  # one line per request, never the body
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

        def send(self, status, obj):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            if self.path == "/healthz": return self.send(200, dict(ok=True, engine=engine_cli(env)[1]))
            self.send(404, dict(error="not found"))

        def do_POST(self):
            if self.path != "/v1/convert": return self.send(404, dict(error="not found"))
            auth = self.headers.get("Authorization", "")
            given = auth[7:] if auth.startswith("Bearer ") else ""
            if not hmac.compare_digest(given.encode("utf-8"), secret.encode("utf-8")): return self.send(401, dict(error="unauthorised"))
            try: n = int(self.headers.get("Content-Length", "0"))
            except ValueError: return self.send(400, dict(error="bad Content-Length"))
            if n <= 0: return self.send(400, dict(error="empty body"))
            if n > MAX_BODY: return self.send(413, dict(error=f"request larger than {MAX_BODY // 1024} KB"))
            try: req = json.loads(self.rfile.read(n).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError): return self.send(400, dict(error="body is not JSON"))
            if not slots.acquire(timeout=20): return self.send(429, dict(error="the converter is busy; try again in a minute"))
            try: return self.send(200, convert(req, env))
            except InputError as e: return self.send(422, dict(error=str(e)))
            except EngineError as e: return self.send(e.status, dict(error=e.message, log_tail=e.log_tail))
            except Exception as e:  # noqa: BLE001 — a crash here must still answer, not hang PLM
                return self.send(500, dict(error=f"worker error: {type(e).__name__}"))
            finally: slots.release()
    return H


def main():
    secret = os.environ.get("SVG2DST_SHARED_SECRET", "")
    if len(secret) < 32: sys.exit("SVG2DST_SHARED_SECRET must be set (>= 32 characters); refusing to start an open converter")
    slots = threading.BoundedSemaphore(max(1, int(os.environ.get("SVG2DST_MAX_CONCURRENCY", "1"))))
    port = int(os.environ.get("PORT", "8080"))
    cli, name = engine_cli()
    print(f"svg2dst worker on :{port}, engine={name or 'NONE (503 on every convert)'}", flush=True)
    DualStackServer(("::", port), make_handler(secret, slots)).serve_forever()


if __name__ == "__main__":
    main()
