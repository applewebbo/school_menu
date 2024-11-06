#!/bin/sh

set -eu

echo "Migrating database..."
python manage.py migrate

echo "Building production css files..."
python manage.py tailwind build

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting gunicorn..."
gunicorn core.wsgi:application --bind=0.0.0.0:80
