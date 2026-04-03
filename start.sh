#!/usr/bin/env bash

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
gunicorn eshop.wsgi:application --bind 0.0.0.0:$PORT --workers 2
