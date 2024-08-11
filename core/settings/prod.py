from .common import *  # noqa

SECRET_KEY = env("SECRET_KEY")

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env("ALLOWED_HOSTS").split(",")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": "5432",
    }
}

NO_RELOAD = env("NO_RELOAD", default=False)

# DBBACKUP
DBBACKUP_FILENAME_TEMPLATE = "MenuAppCloud-{datetime}.{extension}"
