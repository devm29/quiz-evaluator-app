# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build wheels. Keeps compilers and pip's build machinery out of the
# image that actually ships.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements.txt ./
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SQLITE_PATH=/data/db.sqlite3

RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    pip install --no-index --find-links=/wheels /wheels/*.whl

# Run as an unprivileged user. /data is a mount point for the SQLite file so
# submissions survive a container replacement.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data /app/staticfiles \
    && chown -R appuser:appuser /data /app

WORKDIR /app
COPY --chown=appuser:appuser . .

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "quiz_app_api.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--access-logfile", "-"]
