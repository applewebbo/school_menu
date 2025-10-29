# import os
import os
from pathlib import Path
from warnings import filterwarnings

import environ
from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# # Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

ENVIRONMENT = env("ENVIRONMENT", default="prod")
SECRET_KEY = env("SECRET_KEY")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3RD PARTY DEPENDENCIES
    "active_link",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "anymail",
    "cookiebanner",
    "crispy_tailwind",
    "crispy_forms",
    "dbbackup",
    "debug_toolbar",
    "django_browser_reload",
    "django_q",
    "django_social_share",
    "django_tailwind_cli",
    "heroicons",
    "import_export",
    "neapolitan",
    "pwa",
    "rest_framework",
    "template_partials",
    "webpush",
    # INTERNAL APPS
    "contacts",
    "django_scheduled_backups",
    "notifications",
    "school_menu",
    "users",
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
    "django_browser_reload.middleware.BrowserReloadMiddleware",
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

LANGUAGE_CODE = "it-it"

TIME_ZONE = "Europe/Rome"

USE_I18N = True

USE_TZ = True

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
ACCOUNT_FORMS = {
    "signup": "users.forms.MyCustomSignupForm",
    "login": "users.forms.MyCustomLoginForm",
    "add_email": "users.forms.MyCustomAddEmailForm",
}
SITE_ID = 1
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGIN_METHODS = {"email"}
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

# COOKIEBANNER
COOKIEBANNER = {
    "title": _("Impostazioni cookie"),
    "header_text": _(
        "Questo sito utilizza cookie tecnici per garantire la corretta funzionalità del sito. Inoltre monitora in maniera anonima il traffico e il comportamento degli utenti in ottica di miglioramento delle funzionalità. Consulta le nostre policy cliccando sui link presenti nel footer.",
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
    ],
}

# DJANGO-TAILWIND-CLI
TAILWIND_CLI_SRC_CSS = "src/source.css"
TAILWIND_CLI_USE_DAISY_UI = True

# DJANGO-PWA
PWA_APP_NAME = "Menu Scolastico"
PWA_APP_DESCRIPTION = "Cosa mangia mio figlio oggi?"
PWA_APP_THEME_COLOR = "#FFFFFF"
PWA_APP_BACKGROUND_COLOR = "#FFFFFF"
PWA_APP_DISPLAY = "standalone"
PWA_APP_SCOPE = "/"
PWA_APP_ORIENTATION = "natural"
PWA_APP_START_URL = "/"
PWA_APP_STATUS_BAR_COLOR = "default"
PWA_APP_DIR = "ltr"
PWA_APP_LANG = "it-IT"
PWA_APP_ICONS = [
    {"src": "/static/img/android-chrome-192x192.png", "sizes": "192x192"},
    {"src": "/static/img/android-chrome-512x512.png", "sizes": "512x512"},
]
PWA_APP_ICONS_APPLE = [{"src": "/static/img/apple-touch-icon.png", "sizes": "180x180"}]
PWA_APP_SPLASH_SCREEN = [
    {
        "src": "/static/img/splash-640x1136.png",
        "media": "(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)",
    }
]
PWA_APP_OFFLINE_URL = "/offline/"

# WEBPUSH
WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": env("VAPID_PUBLIC_KEY"),
    "VAPID_PRIVATE_KEY": env("VAPID_PRIVATE_KEY"),
    "VAPID_ADMIN_EMAIL": env("ADMIN_EMAIL"),
}
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, "static/js/serviceworker.js")

# SET transitional setting for FORMS_URLFIELD_ASSUME_HTTPS and ignore deprecation warning
filterwarnings(
    "ignore", "The FORMS_URLFIELD_ASSUME_HTTPS transitional setting is deprecated."
)
FORMS_URLFIELD_ASSUME_HTTPS = True

# DJANGO-DEBUG-TOOLBAR
INTERNAL_IPS = [
    "127.0.0.1",
]

# APP-SPECIFIC SETTINGS
ENABLE_SCHOOL_DATE_CHECK = env.bool("ENABLE_SCHOOL_DATE_CHECK", default=True)


# DEVELOPMENT SPECIFIC SETTINGS
if ENVIRONMENT == "dev":
    DEBUG = env("DEBUG", default=True)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

    ALLOWED_HOSTS: list[str] = [
        "localhost",
    ]

    # DJANGO SILK - Performance profiler (dev only)
    INSTALLED_APPS += ["silk"]
    MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]

    # Silk configuration
    SILKY_PYTHON_PROFILER = True
    SILKY_PYTHON_PROFILER_BINARY = True
    SILKY_AUTHENTICATION = True
    SILKY_AUTHORISATION = True
    SILKY_META = True

    # DJANGO-Q
    Q_CLUSTER = {
        "name": "school_menu",
        "workers": 4,
        "timeout": 60,
        "retry": 120,
        "queue_limit": 50,
        "bulk": 10,
        "orm": "default",
        "catch_up": False,
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": "",
        },
    }

    # CACHES - Use database cache in development (no Redis needed)
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache",
            "KEY_PREFIX": "school_menu",
            "TIMEOUT": 300,  # 5 minutes default
        }
    }

    # DJANGO SCHEDULED BACKUPS - Disabled in development
    SCHEDULED_BACKUPS = {
        "ENABLED": False,
    }

# PRODUCTION SPECIFIC SETTINGS
elif ENVIRONMENT == "prod":
    DEBUG = env.bool("DEBUG", default=False)
    ALLOWED_HOSTS: list[str] = env("ALLOWED_HOSTS")
    CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS").split(",")
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
    # DBBACKUP
    DBBACKUP_FILENAME_TEMPLATE = "MenuAppCloud-{datetime}.{extension}"
    # DJANGO-Q
    Q_CLUSTER = {
        "name": "school_menu",
        "workers": 4,
        "timeout": 60,
        "retry": 120,
        "queue_limit": 50,
        "bulk": 10,
        "orm": "default",
        "catch_up": False,
        "redis": {
            "host": "srv-captain--school-menu-redis",
            "port": 6379,
            "db": 0,
            "password": env("REDIS_PASSWORD", default=""),
        },
    }

    # CACHES - Use Redis with database fallback in production
    redis_password = env("REDIS_PASSWORD", default="")
    redis_url = (
        f"redis://:{redis_password}@srv-captain--school-menu-redis:6379/1"
        if redis_password
        else "redis://srv-captain--school-menu-redis:6379/1"
    )
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "KEY_PREFIX": "school_menu",
            "TIMEOUT": 300,  # 5 minutes default
        },
        "db_cache": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache",
            "KEY_PREFIX": "school_menu_db",
        },
    }

    # DJANGO SCHEDULED BACKUPS - Enabled in production only
    SCHEDULED_BACKUPS = {
        # Enable/disable the backup system
        "ENABLED": True,
        # Email addresses to notify (falls back to ADMINS if not set)
        "NOTIFICATION_EMAILS": None,  # Uses ADMINS by default
        # Database backup configuration
        "DATABASE_BACKUP": {
            "enabled": True,
            "schedule": "0 0 * * 0",  # Weekly on Sunday at midnight
        },
        # Media backup configuration (not needed for this project)
        "MEDIA_BACKUP": {
            "enabled": False,
        },
        # How many days to keep backup history records
        "HISTORY_RETENTION_DAYS": 90,
        # Send email on successful backup
        "EMAIL_ON_SUCCESS": True,
        # Send email on failed backup
        "EMAIL_ON_FAILURE": True,
        # Task queue backend: 'django_q' or 'celery'
        "TASK_QUEUE": "django_q",
        # Email subject prefix
        "EMAIL_SUBJECT_PREFIX": "[Menu App Backup]",
    }

# TESTING SPECIFIC SETTINGS
elif ENVIRONMENT == "test":
    import logging

    SECRET_KEY = "my-test-secret-key"  # nosec
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
    PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    Q_CLUSTER = {
        "name": "school_menu",
        "workers": 1,
        "sync": True,
        "timeout": 60,
        "retry": 120,
    }

    # CACHES - Use dummy cache in testing (no actual caching)
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }

    # DJANGO SCHEDULED BACKUPS - Disabled in testing
    SCHEDULED_BACKUPS = {
        "ENABLED": False,
    }

    logging.disable()
