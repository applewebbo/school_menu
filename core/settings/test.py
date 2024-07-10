import logging

from .common import *  # noqa

SECRET_KEY = "my-test-secret-key"  # nosec
NO_RELOAD = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)


EMAIL_BACKEND = "django.core.mail.backends.locmemp.EmailBackend"


logging.disable()
