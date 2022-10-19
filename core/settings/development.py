from .common import *

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

SECRET_KEY = "r)s&++&c9l(zg1x4lxnba21^vwj%_6(1^1la$3k5^0&$d#%)93"

ALLOWED_HOSTS = []
