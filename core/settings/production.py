import os

import environ

from .common import *

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = [env("ALLOWED_HOST")]

DATABASES = {
    "default": {
        "ENGINE": 'env("DB_ENGINE")',
        "NAME": 'env("DB_NAME")',
        "USER": 'env("DB_USER")',
        "PASSWORD": 'env("DB_PASSWORD")',
        "HOST": 'env("DB_HOST")',
    }
}
