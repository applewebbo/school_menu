# import os
import os
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# # Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# Application definition

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.import_export",
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
    "cookiebanner",
    "crispy_tailwind",
    "crispy_forms",
    "dbbackup",
    "debug_toolbar",
    # "django_q",
    "django_social_share",
    "heroicons",
    "import_export",
    "neapolitan",
    "template_partials",
    # INTERNAL APPS
    "users",
    "school_menu",
    "contacts",
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
    "debug_toolbar.middleware.DebugToolbarMiddleware",
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
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

ACCOUNT_FORMS = {"signup": "users.forms.MyCustomSignupForm"}

SITE_ID = 1

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

LOGIN_REDIRECT_URL = "school_menu:index"
ACCOUNT_LOGOUT_REDIRECT_URL = "school_menu:index"

# DJANGO CRISPY FORMS
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# DJANGO_ANYMAIL
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
DEFAULT_FROM_EMAIL = "info@mg.webbografico.com"
ADMIN_EMAIL = env("ADMIN_EMAIL")

ANYMAIL = {
    "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),
    "MAILGUN_API_URL": env("MAILGUN_API_URL"),
    "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN"),
}

# DBBACKUP
DBBACKUP_STORAGE = "storages.backends.dropbox.DropBoxStorage"
DBBACKUP_STORAGE_OPTIONS = {
    "oauth2_access_token": env("DROPBOX_OAUTH2_ACCESS_TOKEN"),
    "oauth2_refresh_token": env("DROPBOX_OAUTH2_REFRESH_TOKEN"),
    "app_secret": env("DROPBOX_APP_SECRET"),
    "app_key": env("DROPBOX_APP_KEY"),
}

# DJANGO_Q
# Q_CLUSTER = {
#     "name": "DjangORM",
#     "workers": 4,
#     "timeout": 90,
#     "retry": 120,
#     "queue_limit": 50,
#     "bulk": 10,
#     "orm": "default",
# }

# UNFOLD

UNFOLD = {
    "SITE_HEADER": "Menu Scolastico",
    "COLORS": {
        "primary": {
            50: "#E9FBF0",
            100: "#CFF7DE",
            200: "#9FEFBC",
            300: "#6FE69B",
            400: "#40DE7A",
            500: "#22C55E",
            600: "#1B9D4B",
            700: "#147538",
            800: "#0D4E25",
            900: "#072713",
            950: "#04160A",
        },
    },
}

# COOKIEBANNER


COOKIEBANNER = {
    "title": _("Impostazioni cookie"),
    "header_text": _(
        "Questo sito utilizza cookie tecnici per garantire la corretta funzionalità del sito. Inoltre monitora in maniera anonima il traffico e il comportamento degli utenti in ottica di miglioramento delle funzionalità. Consulta le nostre policy cliccando sui link in fondo.",
    ),
    "groups": [
        {
            "id": "essential",
            "name": _("Essenziali"),
            "description": _(
                "Questi cookie sono essenziali per il corretto funzionamento del sito."
            ),
            "cookies": [
                {
                    "pattern": "cookiebanner",
                    "description": _(
                        "Registra le preferenze rispetto agli altri cookie."
                    ),
                },
                {
                    "pattern": "csrftoken",
                    "description": _(
                        "Previene attacchi di tipo cross-site request forgery."
                    ),
                },
                {
                    "pattern": "sessionid",
                    "description": _(
                        "Registra la sessione utente e permette ad esempio il login."
                    ),
                },
            ],
        },
        {
            "id": "analytics",
            "name": _("Analisi Utilizzo"),
            "description": _(
                "Questi cookie registrano i dati relativi al comportamento degli utenti sul sito in maniera anonima."
            ),
            "optional": True,
            "cookies": [
                {
                    "pattern": "_pk_.*",
                    "description": _(
                        "Registra i dati anonimi di utilizzo tramite piattaforma Matomo."
                    ),
                },
            ],
        },
    ],
}
