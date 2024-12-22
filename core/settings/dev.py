from .common import *  # noqa

DEBUG = env("DEBUG", default=True)
NO_RELOAD = False

INSTALLED_APPS += [
    "anymail",
    "django_browser_reload",
    "django_extensions",
]

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS: list[str] = [
    "localhost",
]

# DJANGO-DEBUG-TOOLBAR
INTERNAL_IPS = [
    "127.0.0.1",
]
