# svg2dst worker

The Python service behind PLM's **SVG → DST** window. PLM sends an SVG plus the finished width, fabric and
hoop. The worker runs `scripts/svg2dst.py` (the contract is in `docs/SVG2DST.md`) and sends back the DST, the
PES, a preview PNG and `result.json` (gates, threads, stitch count, trims, machine minutes, questions).
It runs on CPU only and never calls the Anthropic API.

**Until S1 merges, `scripts/svg2dst.py` does not exist.** With `SVG2DST_ALLOW_STUB=true` the worker
runs `stub_engine.py` instead. The stub follows the same contract but sews plain fill rows, and it always
fails the hard gate "Made by the real digitising engine", so the page shows **Not OK** on every stub result.
Once `scripts/svg2dst.py` is on `main` and Railway redeploys, the real engine takes over by itself.

## Security

- Every convert call needs `Authorization: Bearer $SVG2DST_SHARED_SECRET`, and the server will not start
  without a secret of at least 32 characters. `/healthz` is open, but it only returns which engine is
  installed.
- **The real defence against fetching URLs or reading local files is the renderer itself:** `cairosvg>=2.7.1`
  (pinned in requirements.txt) called with `unsafe=False`. `tests/test_svg2dst_worker.py` renders `href` /
  `@import` / `url()` payloads against a local listener and requires zero hits, so dropping either goes red.
  The engine CLI (S1) must keep `unsafe=False` too. On top of that, as a second layer, a quick text check
  refuses plain outside `href`/`url()` links and any DOCTYPE/ENTITY. It is not complete on its own (CSS
  `@import`, CSS escapes and links nested inside data: URIs get past it). Size cap: 2 MB.
- Listens on `::` with IPv4 also enabled (dual-stack), because Railway private DNS can resolve to IPv6 only.
- The engine subprocess runs with a clean environment, so it never sees the secret. Each request runs in
  its own temp dir, which is deleted afterwards. The worker keeps nothing: PLM stores the files in its
  private bucket.
- Give it a private Railway network address only. PLM calls it over `*.railway.internal`, so no public
  domain is needed.

## Deploy (founder approval needed; nothing below has been done)

In the **Haki** Railway workspace, inside the project that holds `plm`:

1. **New service from the repo:** + New → GitHub Repo → `haki-studio/techpack-engine`, branch `main`.
   Name it `svg2dst-worker`.
2. **Settings → Config-as-code:** set the path to `services/svg2dst/railway.json`. That file sets the
   Dockerfile (`services/svg2dst/Dockerfile`), the health check and the watch paths. Leave **Root Directory**
   empty, because the build context has to be the repo root.
3. **Variables on `svg2dst-worker`:**
   - `SVG2DST_SHARED_SECRET` = a new random value. Generate it with `openssl rand -hex 32`.
   - `SVG2DST_ALLOW_STUB` = `true`. Delete it once S1 is merged, so a missing engine shows as 503 and not
     as stub output.
   - Optional: `SVG2DST_TIMEOUT_S` = `240`, `SVG2DST_MAX_CONCURRENCY` = `1`.
4. **Networking:** do **not** generate a public domain. The private address is
   `svg2dst-worker.railway.internal`, and the service listens on `$PORT` (Railway sets it, default 8080).
5. **Variables on `plm`:**
   - `SVG2DST_WORKER_URL` = `http://svg2dst-worker.railway.internal:8080`
   - `SVG2DST_SHARED_SECRET` = the same value as in step 3. Use a reference variable:
     `${{svg2dst-worker.SVG2DST_SHARED_SECRET}}`.
6. Deploy both services. Check that `svg2dst-worker` logs show
   `svg2dst worker on :8080, engine=stub` (`engine=svg2dst` after S1).

The same steps as Railway MCP calls: `create-service` (repo `haki-studio/techpack-engine`, name
`svg2dst-worker`) → `update-service` (config path `services/svg2dst/railway.json`) → `set-variables` on
`svg2dst-worker` (the two variables above) → `set-variables` on `plm` (the two variables above).

## Local

```
~/.venvs/techpack/bin/python -m pytest -q tests/test_svg2dst_worker.py
SVG2DST_SHARED_SECRET=$(openssl rand -hex 32) SVG2DST_ALLOW_STUB=true ~/.venvs/techpack/bin/python services/svg2dst/server.py
```
