from .common import *  # noqa

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = []

# DJANGO-DEBUG-TOOLBAR
INTERNAL_IPS = [
    "127.0.0.1",
]
