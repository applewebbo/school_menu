from .common import *  # noqa

DEBUG = True
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

ALLOWED_HOSTS = []

# DJANGO-DEBUG-TOOLBAR
INTERNAL_IPS = [
    "127.0.0.1",
]

INSTALLED_APPS += [
    "dbbackup",
    "django_q",
]

# DBBACKUP
DBBACKUP_STORAGE = "storages.backends.dropbox.DropBoxStorage"
DBBACKUP_STORAGE_OPTIONS = {
    "oauth2_access_token": env("DROPBOX_OAUTH2_ACCESS_TOKEN"),
    "oauth2_refresh_token": env("DROPBOX_OAUTH2_REFRESH_TOKEN"),
    "app_secret": env("DROPBOX_APP_SECRET"),
    "app_key": env("DROPBOX_APP_KEY"),
}

# DJANGO_Q
Q_CLUSTER = {
    "name": "DjangORM",
    "workers": 4,
    "timeout": 90,
    "retry": 120,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}
