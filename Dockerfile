FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 10001 appuser \
    && mkdir /data \
    && chown appuser:appuser /data

COPY . .

USER appuser

# SQLite lives on a volume so tasks survive container rebuilds.
ENV DATABASE_URL=sqlite:////data/hmcts_tasks.db \
    PORT=8000

ENV GUNICORN_CMD_ARGS="--workers 1 --threads 4 --access-logfile -"

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health', timeout=3)"

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} run:app"]
