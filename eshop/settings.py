from pathlib import Path
# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         eshop/settings.py
# Description:  Django project settings for TrendMart. Configures installed
#               apps, database (SQLite for dev), static/media file handling,
#               authentication backends, session settings, security headers,
#               and optional integrations (OpenRouter AI, Stripe, email, OAuth,
#               Redis cache, Django Channels WebSockets, Sitemap/SEO).
#
# SECURITY NOTE: All secrets are loaded from the .env file via python-dotenv.
#               Never hardcode API keys or passwords here.
#               Copy .env.example to .env and fill in your real values.
# =============================================================================

import os
from dotenv import load_dotenv  # Loads variables from .env into os.environ

# ── Load .env file ────────────────────────────────────────────────────────────
# Looks for .env in the project root (BASE_DIR). Variables already set in the
# real environment take precedence (override=False is the default).
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# ── Core Django settings ──────────────────────────────────────────────────────
# SECRET_KEY is loaded from .env.  A safe development fallback is provided so
# the project runs immediately after a fresh git clone without any setup.
# NEVER use the fallback value in production — set a real key in your .env file.
_DEV_SECRET = 'django-insecure-trendmart-dev-fallback-qa1(#pr3sj!dim5*&j4aw)g%d_j20svl'
SECRET_KEY = os.environ.get('SECRET_KEY', _DEV_SECRET)

# DEBUG defaults to True for the dev fallback; set DEBUG=False in .env for prod
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# In production set ALLOWED_HOSTS=trendmart.com,www.trendmart.com in .env
_hosts = os.environ.get('ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',')]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Sitemap generation for SEO — exposes /sitemap.xml to Google/Bing crawlers
    'django.contrib.sitemaps',
    'shop',
    # Django Channels enables WebSockets for real-time stock updates.
    # Install with: pip install channels channels-redis
    # Uncomment when channels is installed:
    # 'channels',
]

# ── AI Assistant: OpenRouter API ─────────────────────────────────────────────
# OpenRouter proxies many LLMs (GPT-4o, Claude, Gemini, etc.)
# via a single OpenAI-compatible endpoint. Docs: https://openrouter.ai/docs
# Set OPENROUTER_API_KEY in your .env file — never hardcode it here.
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
# The model to use — openai/gpt-4o-mini is fast, cheap, and highly capable.
# Other options: "anthropic/claude-3-haiku", "google/gemini-flash-1.5"
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'openai/gpt-4o-mini')

# Legacy OPENAI_ settings kept for backward compat (now proxied via OpenRouter)
OPENAI_API_KEY = OPENROUTER_API_KEY
OPENAI_MODEL = OPENROUTER_MODEL

# ── Optional: Stripe Payments ─────────────────────────────────────────────────
# Get keys at: https://dashboard.stripe.com/apikeys
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# ── Optional: Google OAuth2 (Social Login) ────────────────────────────────────
# Install: pip install django-allauth
# Configure at: https://console.cloud.google.com/apis/credentials
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_COOKIE_AGE = 86400 * 30

# ── Security headers ──────────────────────────────────────────────────────────
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# ── Cache Framework ───────────────────────────────────────────────────────────
# Uses Redis in production (ultra-fast, shared across workers).
# Falls back to LocMemCache in development — no extra setup needed.
# To switch to Redis: set REDIS_URL env var and pip install django-redis
REDIS_URL = os.environ.get('REDIS_URL', '')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            },
            'TIMEOUT': 300,  # 5 minutes default cache TTL
        }
    }
    # Store Django sessions in Redis too (survives server restarts)
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Development default: in-process memory cache (no dependencies)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'trendmart-cache',
        }
    }

# ── Django Channels (WebSockets) ──────────────────────────────────────────────
# Enables real-time features: live stock warnings, order status push, chat.
# Install: pip install channels channels-redis
# Then uncomment 'channels' in INSTALLED_APPS and ASGI_APPLICATION below.
#
# ASGI_APPLICATION = 'eshop.asgi.application'
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {'hosts': [REDIS_URL or 'redis://127.0.0.1:6379']},
#     },
# }

# ── Image Optimization ────────────────────────────────────────────────────────
# WebP conversion is handled in Product.save() via Pillow.
# Set this to False to disable auto-conversion (e.g. during bulk imports).
WEBP_CONVERSION_ENABLED = True
# Quality 0-100: 85 gives excellent quality at ~60% smaller file size vs JPEG
WEBP_QUALITY = 85

# ── Sitemap / SEO ─────────────────────────────────────────────────────────────
# django.contrib.sitemaps is already in INSTALLED_APPS.
# Sitemap URLs are registered in eshop/urls.py.
SITE_NAME = 'TrendMart'
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'localhost:8000')

# ── Email: order confirmations & alerts ───────────────────────────────────────
# In development, emails are printed to the console.
# In production set EMAIL_BACKEND to SMTP and configure your provider.
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'apikey')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'TrendMart <noreply@trendmart.com>')
