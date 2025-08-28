#!/bin/sh

set -eu
export PYTHONWARNINGS="ignore::SyntaxWarning"

echo "Checking migrations..."
python manage.py makemigrations

echo "Migrating database..."
python manage.py migrate

echo "Building production css files..."
python manage.py tailwind build

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting overmind..."
overmind start -r all
