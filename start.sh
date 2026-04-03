#!/usr/bin/env bash
<<<<<<< HEAD

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
gunicorn eshop.wsgi:application --bind 0.0.0.0:$PORT --workers 2
=======
# =============================================================================
# TrendMart — Production Start Script
# Used by: Render Docker deployment (Docker Command: bash start.sh)
#
# This script runs on every deploy:
#   1. Applies database migrations
#   2. Collects static files for WhiteNoise
#   3. Seeds sample data (idempotent — skips existing records)
#   4. Creates a superuser if none exists
#   5. Starts Gunicorn with the config file
# =============================================================================
set -e

echo "════════════════════════════════════════════════════════"
echo "  TrendMart — Starting production deploy sequence"
echo "════════════════════════════════════════════════════════"

echo ""
echo "▶ Step 1/5: Running database migrations..."
python manage.py migrate --noinput

echo ""
echo "▶ Step 2/5: Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "▶ Step 3/5: Populating sample data (idempotent)..."
python manage.py populate_data

echo ""
echo "▶ Step 4/5: Ensuring superuser exists..."
python manage.py shell -c "
from django.contrib.auth.models import User
import os
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@trendmart.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'  ✓ Superuser \"{username}\" created.')
else:
    print('  ✓ Superuser already exists, skipping.')
"

echo ""
echo "▶ Step 5/5: Starting Gunicorn..."
echo "════════════════════════════════════════════════════════"
exec gunicorn eshop.wsgi:application --config gunicorn.conf.py
>>>>>>> 4000c39 (Deployment Tweaks)
