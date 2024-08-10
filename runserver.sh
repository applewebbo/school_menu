#!/bin/sh

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py qcluster &
gunicorn core.wsgi:application --bind=0.0.0.0:80 &
