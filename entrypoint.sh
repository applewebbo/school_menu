#!/bin/sh

set -eu
export PYTHONWARNINGS="ignore::SyntaxWarning"

echo "Checking migrations..."
python manage.py makemigrations

echo "Migrating database..."
python manage.py migrate

echo "Creating cache table..."
python manage.py createcachetable django_cache

echo "Registering notification schedules..."
# Idempotent: keeps the four daily menu-push cron rows in Django-Q2 so a wiped or
# never-created schedule can't silently drop a whole notification slot (#267).
python manage.py setup_notification_schedules

echo "Building production css files..."
# --force is required: plain `build` reports "up to date" and skips the rebuild, so a deploy
# can ship a stylesheet missing the utility classes introduced in that very release (#242).
python manage.py tailwind build --force

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting supervisord..."
supervisord -c /app/supervisord.conf
