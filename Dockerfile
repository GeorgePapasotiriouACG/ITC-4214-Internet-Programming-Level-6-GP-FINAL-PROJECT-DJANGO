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

# System packages needed to compile psycopg2-binary and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime image ────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app

# Runtime system libraries only (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the application source code
COPY . .

# Create non-root user for security (never run Django as root in production)
RUN addgroup --system trendmart && adduser --system --ingroup trendmart trendmart
RUN mkdir -p /app/media /app/staticfiles /app/logs && \
    chown -R trendmart:trendmart /app

USER trendmart

# NOTE: We do NOT run collectstatic at build time because:
# 1. No .env file is available during Docker build (it's in .dockerignore)
# 2. DEBUG defaults to True without .env, which tries to load debug_toolbar
# 3. collectstatic is run by start.sh at runtime instead (with proper env vars)

# Expose port — actual binding is done by Gunicorn at runtime
EXPOSE 8000

# Health check — Docker will mark the container unhealthy if this fails
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

# Start command — start.sh handles migrations, collectstatic, data seeding, and gunicorn
CMD ["bash", "start.sh"]
