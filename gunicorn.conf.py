# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         gunicorn.conf.py
# Description:  Gunicorn WSGI server configuration.
#               Referenced by: Dockerfile CMD, Procfile, start.sh
#
# Render injects $PORT automatically. WEB_CONCURRENCY can be set
# in the Render dashboard to override the default worker count.
# =============================================================================

import multiprocessing
import os

# Bind to the PORT environment variable (Render injects this automatically)
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Workers: 2–4 per CPU core. Render free tier has 0.5 CPU → 2 workers is safe.
# Override via WEB_CONCURRENCY env var in the Render dashboard.
workers = int(os.environ.get('WEB_CONCURRENCY', min(multiprocessing.cpu_count() * 2 + 1, 4)))

# Threads per worker — helps with I/O-bound work (DB queries, API calls)
threads = 2

# Request timeout — Render's health check expects a response within 30s
# but we give long-running requests (AI chat, image upload) up to 120s
timeout = 120

# Graceful shutdown timeout
graceful_timeout = 30

# Log to stdout/stderr so Render captures everything in its Logs tab
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Preload the app to save memory (code is shared across forked workers)
preload_app = True
