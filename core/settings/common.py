# import os
import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# # Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# # SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = env("SECRET_KEY")

# # SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = env("DEBUG")

# ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3RD PARTY DEPENDENCIES
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_extensions",
    "import_export",
    # INTERNAL APPS
    "users",
    "school_menu",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# # Database
# # https://docs.djangoproject.com/en/4.0/ref/settings/#databases

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "it-it"

TIME_ZONE = "Europe/Rome"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "/static/"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

AUTH_USER_MODEL = "users.User"

# DJANGO-ALLAUTH

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# ACCOUNT_ADAPTER => default
# ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS => default
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
# ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL => default
# ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL => default
# ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS => default
# ACCOUNT_EMAIL_CONFIRMATION_HMAC => default
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "ORGANIZE IT! - "
ACCOUNT_DEFAULT_HTTP_PROTOCOL = env("ACCOUNT_DEFAULT_HTTP_PROTOCOL")
# ACCOUNT_EMAIL_CONFIRMATION_COOLDOWN => default
# ACCOUNT_EMAIL_MAX_LENGTH => default
# ACCOUNT_MAX_EMAIL_ADDRESSES => default
# ACCOUNT_FORMS => default
# ACCOUNT_LOGIN_ATTEMPTS_LIMIT => default
# ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT => default
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
# ACCOUNT_LOGOUT_ON_GET => default
# ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE => default
# ACCOUNT_LOGIN_ON_PASSWORD_RESET => default
# ACCOUNT_LOGOUT_REDIRECT_URL => default
# ACCOUNT_PASSWORD_INPUT_RENDER_VALUE => default
ACCOUNT_PRESERVE_USERNAME_CASING = False
# ACCOUNT_PREVENT_ENUMERATION => default
# ACCOUNT_RATE_LIMITS => default
ACCOUNT_SESSION_REMEMBER = True
# ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE => default
# ACCOUNT_SIGNUP_FORM_CLASS => default
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
# ACCOUNT_SIGNUP_REDIRECT_URL => default
# ACCOUNT_TEMPLATE_EXTENSION => default
# ACCOUNT_USERNAME_BLACKLIST => default
# ACCOUNT_UNIQUE_EMAIL => default
# ACCOUNT_USER_DISPLAY =>  default
# ACCOUNT_USER_MODEL_EMAIL_FIELD => default
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# ACCOUNT_USERNAME_MIN_LENGTH => default
ACCOUNT_USERNAME_REQUIRED = False
# ACCOUNT_USERNAME_VALIDATORS => default
# SOCIALACCOUNT_* => default
