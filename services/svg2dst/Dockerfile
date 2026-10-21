# svg2dst worker (PLM "SVG -> DST" window). Build context = the techpack-engine REPO ROOT:
#   docker build -f services/svg2dst/Dockerfile .
# CPU only. No Anthropic API key is ever given to this image.
FROM python:3.12-slim

# cairosvg needs the cairo C library; fonts so <text> in an SVG renders instead of vanishing.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libcairo2 libpango-1.0-0 libpangocairo-1.0-0 fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Only what the converter needs: the engine, the CLI (once S1 lands), the factory profile, this service.
COPY engine ./engine
COPY scripts ./scripts
COPY factory.json ./factory.json
COPY services/svg2dst ./services/svg2dst

RUN useradd --create-home --uid 10001 worker && chown -R worker /app
USER worker
ENV PYTHONUNBUFFERED=1 PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:%s/healthz'%os.environ.get('PORT','8080'),timeout=4)"
CMD ["python", "services/svg2dst/server.py"]
