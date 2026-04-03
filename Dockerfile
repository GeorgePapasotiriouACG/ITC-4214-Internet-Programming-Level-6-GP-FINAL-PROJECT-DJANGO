# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         Dockerfile
# Description:  Multi-stage Docker build for TrendMart.
#               Stage 1 (builder): installs Python dependencies into a venv
#               Stage 2 (runtime): lean image with only the runtime venv
#               This keeps the final image small and free of build tools.
#
# Build:  docker build -t trendmart .
# Run:    docker run -p 8000:8000 --env-file .env trendmart
# =============================================================================

# ── Stage 1: Dependency builder ───────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime image ────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

RUN addgroup --system trendmart && adduser --system --ingroup trendmart trendmart
RUN mkdir -p /app/media /app/staticfiles /app/logs && chown -R trendmart:trendmart /app
USER trendmart

# Collect static files at build time
RUN python manage.py collectstatic --noinput --settings=eshop.settings || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

# ── Start ASGI server with UvicornWorker ──────────────────────────────────────
CMD ["gunicorn", "eshop.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "1"]
