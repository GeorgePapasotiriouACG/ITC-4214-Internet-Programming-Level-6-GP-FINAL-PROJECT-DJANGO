# =============================================================================
# Procfile — TrendMart E-Commerce Platform
# Author:  George Papasotiriou
# Used by: Heroku, Render, Railway, and any Procfile-compatible platform.
#
# 'web' is the main HTTP process. The platform injects $PORT automatically.
# gunicorn.conf.py (same directory) controls worker count, timeouts, etc.
# =============================================================================

# Run Django via Gunicorn with the config file in the project root.
# collectstatic is run before startup to ensure CSS/JS are fresh.
web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn eshop.wsgi:application --config gunicorn.conf.py
