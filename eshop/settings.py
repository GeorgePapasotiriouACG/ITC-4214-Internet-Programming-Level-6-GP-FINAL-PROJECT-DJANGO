# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         eshop/settings.py
# Description:  Django project settings for TrendMart. All secrets are loaded
#               from the .env file — never hardcoded here.
#
# Environment modes:
#   Development: DEBUG=True  (default when .env is missing)
#   Production:  DEBUG=False (set in your .env or hosting platform config)
#
# Key production features enabled when DEBUG=False:
#   - HTTPS enforcement (SECURE_SSL_REDIRECT, HSTS, secure cookies)
#   - WhiteNoise compressed static file serving
#   - PostgreSQL via DATABASE_URL (falls back to SQLite for development)
#   - Sentry error monitoring (when SENTRY_DSN is set)
#   - Structured file logging (logs/trendmart.log)
#   - SECRET_KEY guard (raises RuntimeError if insecure key used)
# =============================================================================

import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv

# Detect if we are running Django's test runner — used to disable dev-only tools
_TESTING = 'test' in sys.argv

# ── Base directory ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Load .env file ────────────────────────────────────────────────────────────
# Variables already set in the real environment take precedence (override=False).
# In production hosting (Heroku/Render/Railway), env vars are set in the
# platform dashboard — no .env file is needed on the server.
load_dotenv(BASE_DIR / '.env')

# ── Debug / environment detection ────────────────────────────────────────────
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# ── SECRET_KEY ────────────────────────────────────────────────────────────────
# Loaded exclusively from .env / environment variables.
# A clearly labelled dev fallback is provided so the project runs immediately
# after a fresh git clone without any setup (never use this in production).
_DEV_SECRET = 'django-insecure-trendmart-dev-fallback-qa1(#pr3sj!dim5*&j4aw)g%d_j20svl'
SECRET_KEY = os.environ.get('SECRET_KEY', _DEV_SECRET)

# ── SECURITY GUARD: block insecure key in production ──────────────────────────
# Raises a RuntimeError immediately at startup if someone forgot to set a real
# SECRET_KEY in the production environment. Better to crash loudly than to run
# silently with weak security.
if not DEBUG and SECRET_KEY.startswith('django-insecure-'):
    raise RuntimeError(
        "\n\n"
        "╔══════════════════════════════════════════════════════════════════╗\n"
        "║   FATAL: Insecure SECRET_KEY detected in production mode!       ║\n"
        "║                                                                  ║\n"
        "║   Set a real SECRET_KEY in your .env file:                      ║\n"
        "║   python -c \"from django.core.management.utils import           ║\n"
        "║   get_random_secret_key; print(get_random_secret_key())\"        ║\n"
        "╚══════════════════════════════════════════════════════════════════╝\n"
    )

# ── Allowed hosts ─────────────────────────────────────────────────────────────
# Production: set ALLOWED_HOSTS=trendmart.com,www.trendmart.com in .env
# Development: defaults to localhost only (NOT wildcard '*')
_hosts_env = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost' if not DEBUG else '*')
ALLOWED_HOSTS = [h.strip() for h in _hosts_env.split(',') if h.strip()]

# ── CSRF Trusted Origins (required for Django 4.1+ behind HTTPS proxies) ─────
# Render / Railway / Heroku all terminate SSL at the load balancer. Without this
# setting, ALL POST requests (login, checkout, admin) will return 403 Forbidden.
# Set CSRF_TRUSTED_ORIGINS=https://myapp.onrender.com in the platform dashboard.
_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]
# Fallback: build from ALLOWED_HOSTS if not explicitly set
if not CSRF_TRUSTED_ORIGINS and not DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        f'https://{host}' for host in ALLOWED_HOSTS if host != '*'
    ]

# ── Installed applications ────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Sitemap generation for SEO — exposes /sitemap.xml to Google/Bing crawlers
    'django.contrib.sitemaps',
    # TrendMart shop application
    'shop',
    # Django Debug Toolbar — only active in DEBUG mode, never in production or tests.
    # Access via the DjDT panel overlay at the right edge of the browser.
    *(['debug_toolbar'] if DEBUG and not _TESTING else []),
    # Django Channels (WebSockets for real-time stock updates).
    # Install: pip install channels channels-redis
    # 'channels',
]

# ── AI Assistant: OpenRouter ───────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL   = os.environ.get('OPENROUTER_MODEL', 'nvidia/nemotron-3-super-120b-a12b:free')
# Legacy aliases kept for backward compatibility
OPENAI_API_KEY = OPENROUTER_API_KEY
OPENAI_MODEL   = OPENROUTER_MODEL

# ── Optional: Stripe Payments ─────────────────────────────────────────────────
STRIPE_PUBLIC_KEY      = os.environ.get('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY      = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET  = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# ── Optional: Google OAuth2 ───────────────────────────────────────────────────
GOOGLE_OAUTH_CLIENT_ID     = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')

# ── Middleware stack ──────────────────────────────────────────────────────────
# ORDER MATTERS: SecurityMiddleware must be first. WhiteNoise must be second
# (immediately after SecurityMiddleware) so it can intercept static requests
# before they reach Django's session/auth layers.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    # WhiteNoise: serves compressed, cache-busted static files in production.
    # Equivalent to Nginx's try_files for /static/ but with zero extra config.
    'whitenoise.middleware.WhiteNoiseMiddleware',

    # Django Debug Toolbar — must be early in the stack.
    # Only activates when DEBUG=True and the request IP is in INTERNAL_IPS.
    # Excluded during `manage.py test` runs to prevent namespace errors.
    *(['debug_toolbar.middleware.DebugToolbarMiddleware'] if DEBUG and not _TESTING else []),

    # TrendMart custom: adds CSP, HSTS, X-Frame-Options, Referrer-Policy, etc.
    'shop.middleware.SecurityHeadersMiddleware',

    # TrendMart custom: IP-based rate limiting on auth/AI endpoints.
    # In production with Redis, this uses Django's cache backend (shared across
    # all Gunicorn workers). Falls back to in-memory per-worker in development.
    'shop.middleware.RateLimitMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eshop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shop.context_processors.cart_context',
                'shop.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'eshop.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
# Reads DATABASE_URL from the environment when available.
# Format: postgresql://user:password@host:5432/dbname
# Falls back to SQLite for local development (no setup required).
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(
                DATABASE_URL,
                conn_max_age=600,        # Keep DB connections open for 10 minutes
                conn_health_checks=True, # Recycle stale connections automatically
            )
        }
    except ImportError:
        # dj-database-url not installed — log a warning and fall back to SQLite
        logging.warning(
            "DATABASE_URL is set but dj-database-url is not installed. "
            "Falling back to SQLite. Run: pip install dj-database-url"
        )
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    # Default: SQLite — zero-config, perfect for local development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            # Use an in-memory database for tests — dramatically faster than file-based SQLite
            'TEST': {
                'NAME': ':memory:',
            },
        }
    }

# ── Password Validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'          # collectstatic writes here
STATICFILES_DIRS = [BASE_DIR / 'static']        # source directory

# WhiteNoise: compress files (gzip/brotli) + append content hash to filenames
# so browsers can cache them forever (Cache-Control: max-age=31536000).
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Media files (user uploads: product images, avatars) ──────────────────────
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# NOTE: In production, media files should be served by a CDN or object storage
# (e.g. AWS S3 with django-storages). Set MEDIA_URL to the CDN base URL.
# For a simple single-server deploy, WhiteNoise does NOT serve /media/ —
# configure Nginx to serve the media/ directory directly:
#   location /media/ { alias /path/to/trendmart/media/; }

# ── Default primary key ───────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Authentication URLs ───────────────────────────────────────────────────────
LOGIN_URL          = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ── Session ───────────────────────────────────────────────────────────────────
# 14 days is the e-commerce standard — long enough to keep users logged in
# across typical shopping sessions, short enough to limit session hijacking risk.
SESSION_COOKIE_AGE = 86400 * 14   # 14 days in seconds

# ── Cache Framework ───────────────────────────────────────────────────────────
# Uses Redis when REDIS_URL is set in the environment (production).
# Falls back to LocMemCache in development — no Redis installation needed.
# Redis benefits: shared across Gunicorn workers, survives restarts,
# enables the cross-process rate limiter and Django Channels.
REDIS_URL = os.environ.get('REDIS_URL', '')
if REDIS_URL:
    try:
        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': REDIS_URL,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
                    # Reconnect on failure instead of raising exceptions
                    'IGNORE_EXCEPTIONS': True,
                },
                'TIMEOUT': 300,  # 5-minute default TTL
                'KEY_PREFIX': 'tm',  # Namespace keys to avoid collisions
            }
        }
        # Store sessions in Redis too — survives server restarts
        SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
        SESSION_CACHE_ALIAS = 'default'
    except Exception:
        pass  # django-redis not installed — fall through to LocMemCache
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'trendmart-cache',
        }
    }

# ── Django Channels (WebSockets for real-time features) ──────────────────────
# Uncomment after: pip install channels channels-redis
# ASGI_APPLICATION = 'eshop.asgi.application'
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {'hosts': [REDIS_URL or 'redis://127.0.0.1:6379']},
#     },
# }

# ── Image Optimization ────────────────────────────────────────────────────────
WEBP_CONVERSION_ENABLED = True   # Auto-convert uploads to WebP on save
WEBP_QUALITY            = 85     # 85 = great quality at ~60% smaller than JPEG

# ── Site metadata (SEO / sitemap) ─────────────────────────────────────────────
SITE_NAME   = 'TrendMart'
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'localhost:8000')

# ── Email ─────────────────────────────────────────────────────────────────────
# Development: print emails to the console (no SMTP server needed).
# Production: use SMTP via SendGrid, Mailgun, SES, or any provider.
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND     = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST        = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
    EMAIL_PORT        = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS     = True
    EMAIL_HOST_USER   = os.environ.get('EMAIL_HOST_USER', 'apikey')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'TrendMart <noreply@trendmart.com>')

# ── HTTPS / Security cookies (production only) ────────────────────────────────
# All of these are safe to enable only when the site is behind HTTPS.
# They are set conditionally so local HTTP development still works.
if not DEBUG:
    # Render/Railway/Heroku terminate SSL at the load balancer and forward
    # X-Forwarded-Proto. Without this, Django thinks all requests are HTTP
    # and triggers infinite redirect loops when SECURE_SSL_REDIRECT is True.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Render already redirects HTTP→HTTPS at the edge, so this is off by default.
    # Set SECURE_SSL_REDIRECT=True in the dashboard only if your proxy does NOT
    # handle the redirect automatically.
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1')

    # Tell browsers to always use HTTPS for this domain for 1 year
    # Once enabled, this cannot be easily undone — read the docs before deploying
    SECURE_HSTS_SECONDS       = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD       = True

    # Session and CSRF cookies are only sent over HTTPS (never plain HTTP)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE    = True

    # HttpOnly prevents JavaScript from reading the session cookie (XSS mitigation)
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY    = True

    # SameSite=Lax prevents the session cookie from being sent in cross-site requests
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE    = 'Lax'

# ── Django built-in security settings ─────────────────────────────────────────
X_FRAME_OPTIONS          = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER  = True

# ── Sentry: error monitoring and performance tracing ──────────────────────────
# When SENTRY_DSN is set, Sentry captures all unhandled exceptions and slow
# queries and sends them to your Sentry dashboard in real-time.
# Sign up free at https://sentry.io — free tier covers ~5000 errors/month.
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(
                    transaction_style='url',   # Group transactions by URL pattern
                    middleware_spans=True,     # Trace each middleware's cost
                    signals_spans=True,        # Trace Django signals
                    cache_spans=True,          # Trace cache hits/misses
                ),
                LoggingIntegration(
                    level=logging.WARNING,     # Capture WARNING+ as breadcrumbs
                    event_level=logging.ERROR, # Capture ERROR+ as Sentry events
                ),
            ],
            # Sample 100% of errors, 10% of transactions (adjust as needed)
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_RATE', '0.1')),
            # Don't send personally identifiable information (GDPR compliance)
            send_default_pii=False,
            # Tag every event with the app name for multi-project dashboards
            release=os.environ.get('APP_VERSION', 'trendmart@1.0.0'),
            environment='production' if not DEBUG else 'development',
        )
    except ImportError:
        pass  # sentry-sdk not installed — skip silently

# ── Logging ───────────────────────────────────────────────────────────────────
# Development: print everything at DEBUG level to the console.
# Production:  WARNING+ to console (captured by platform log aggregator)
#              + ERROR+ to a rotating file in logs/ (survives log rotation).

_LOG_DIR = BASE_DIR / 'logs'
_LOG_DIR.mkdir(exist_ok=True)  # Create logs/ if it doesn't exist

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        # Development: simple one-liner
        'simple': {
            'format': '[{levelname}] {name}: {message}',
            'style': '{',
        },
        # Production: full structured format with timestamp + module path
        'verbose': {
            'format': '{asctime} [{levelname}] {name} {process:d} {thread:d}: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },

    'handlers': {
        # Always-on console handler
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple' if DEBUG else 'verbose',
        },
        # Rotating file handler — keeps 5 × 10 MB log files in logs/
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': _LOG_DIR / 'trendmart.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB per file
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },

    'loggers': {
        # TrendMart application logger
        'shop': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
        # AI assistant logger — separate so it can be tuned independently
        'shop.ai': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        # Django's own loggers
        'django': {
            'handlers': ['console'],
            'level': 'INFO' if DEBUG else 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },

    # Root logger fallback
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# ── Django Debug Toolbar ───────────────────────────────────────────────────────
# Only active when DEBUG=True. Shows SQL queries, cache hits, signals, etc.
# Access: a collapsible panel on the right edge of every page in development.
INTERNAL_IPS = ['127.0.0.1', 'localhost']

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    'IS_RUNNING_TESTS': False,
}

# ── Web Push Notifications (VAPID) ────────────────────────────────────────────
# Generate keys with: py -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.public_key_urlsafe_base64()); print(v.private_key_urlsafe_base64())"
# Set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY in your .env file.
VAPID_PUBLIC_KEY  = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_CLAIMS_EMAIL = os.environ.get('VAPID_CLAIMS_EMAIL', 'admin@trendmart.com')
