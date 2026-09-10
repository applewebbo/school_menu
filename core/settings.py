# import os
import os
from pathlib import Path
from typing import Any
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
REDIRECT_WWW = env("REDIRECT_WWW", default=True)

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
    "django_browser_reload",
    "django_htmx",
    "django_q",
    "django_social_share",
    "django_tailwind_cli",
    "heroicons",
    "import_export",
    "neapolitan",
    "pwa",
    "rest_framework",
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
    "csp.middleware.CSPMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.AuditLogMiddleware",
    "allauth.account.middleware.AccountMiddleware",
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
                "core.context_processors.app_version",
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
MAILERS = {
    "default": {
        "BACKEND": "anymail.backends.mailgun.EmailBackend",
    },
}
DEFAULT_FROM_EMAIL = "info@mg.webbografico.com"
ADMIN_EMAIL = env("ADMIN_EMAIL")

ANYMAIL = {
    "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),
    "MAILGUN_API_URL": env("MAILGUN_API_URL"),
    "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN"),
}

# DBBACKUP - django-dbbackup 5.0 uses STORAGES dictionary
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "dbbackup": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": env("OVH_S3_ACCESS_KEY", default=""),
            "secret_key": env("OVH_S3_SECRET_KEY", default=""),
            "bucket_name": env("OVH_S3_BUCKET_NAME", default=""),
            "endpoint_url": env("OVH_S3_ENDPOINT_URL", default=""),
            "region_name": env("OVH_S3_REGION", default="eu-south-mil"),
            "default_acl": "private",
        },
    },
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
# The image sets this to the CLI version it baked in, so the runtime looks for that exact
# file instead of asking GitHub for `latest` and downloading ~120MB at start (#248).
# Unset in development, where following the latest release is what we want.
TAILWIND_CLI_VERSION = env("TAILWIND_CLI_VERSION", default="latest")

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

# pywebpush defaults to ttl=0, which lets the push service (FCM for Android) drop the
# message the instant the device is in Doze / offline instead of holding it — the main
# reason Android subscribers get the daily menu push only intermittently (#265). Give the
# message a lifetime that spans the useful window of a "today's / tomorrow's menu" send.
WEBPUSH_TTL_SECONDS = env.int("WEBPUSH_TTL_SECONDS", default=12 * 60 * 60)
# (connect, read) timeout for the push POST. Without it a single slow FCM endpoint blocks
# the whole batch task until Q_CLUSTER["timeout"] kills and redelivers it, which then
# double-sends to everyone already notified in that run (#265).
WEBPUSH_REQUEST_TIMEOUT = (5, 10)

# SET transitional setting for FORMS_URLFIELD_ASSUME_HTTPS and ignore deprecation warning
filterwarnings(
    "ignore", "The FORMS_URLFIELD_ASSUME_HTTPS transitional setting is deprecated."
)

# The menu import review page posts every staged row as form fields (7 per row for an
# annual menu, plus the formset management fields). A real annual menu is a whole school
# year, so the POST easily clears Django's default 1000-field cap and every confirm 400s
# with TooManyFieldsSent (#259). Raised, not removed: still a DoS guard, just one sized
# for the largest form this app legitimately submits.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# APP-SPECIFIC SETTINGS
ENABLE_SCHOOL_DATE_CHECK = env.bool("ENABLE_SCHOOL_DATE_CHECK", default=True)
APP_VERSION = "2026.2.5"

# AI MENU IMPORT (#234)
# The Gemini key belongs to the site, not to the user: quotas below are what keeps a
# single account from burning the shared allowance. Everything is env-driven so moving
# off the free tier, or switching model, needs no code change.
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
# Pinned on purpose: the "-latest" aliases move to a new model without notice, which can
# silently change both output quality and which tier the request falls under.
# Flash Lite over Flash: 500 requests/day instead of 20 on the free tier, at the cost of
# some extraction accuracy on messy PDFs. Volume matters more here because a user who has
# to retry twice must not exhaust the whole site's daily allowance.
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-3.5-flash-lite")
# Without a key nothing can be extracted, so the fallback is never offered: proposing a
# button that always fails is worse than showing only the CSV instructions.
AI_MENU_IMPORT_ENABLED = env.bool(
    "AI_MENU_IMPORT_ENABLED", default=bool(GEMINI_API_KEY)
)
# Swappable client, so tests inject a fake instead of mocking the SDK.
AI_MENU_IMPORT_CLIENT = env(
    "AI_MENU_IMPORT_CLIENT", default="school_menu.ai.client.GeminiClient"
)
# Generous per user: importing a menu is a rare, once-a-season act, and someone fighting
# a badly formatted PDF needs room to retry rather than being locked out for the day.
AI_MENU_IMPORT_USER_DAILY_LIMIT = env.int("AI_MENU_IMPORT_USER_DAILY_LIMIT", default=10)
# Half the model's real allowance, so the user gets our Italian "limit reached" message
# instead of a raw 429 from Google, and a runaway loop cannot drain the day. Checked on
# 2026-08-11 in AI Studio: on the free tier the Flash Lite models allow 500 RPD, the full
# Flash ones only 20. Re-check when changing GEMINI_MODEL — the two only make sense together.
AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT = env.int(
    "AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT", default=250
)
AI_MENU_IMPORT_MAX_FILE_SIZE = env.int(
    "AI_MENU_IMPORT_MAX_FILE_SIZE", default=10 * 1024 * 1024
)
AI_MENU_IMPORT_MAX_TEXT_CHARS = env.int("AI_MENU_IMPORT_MAX_TEXT_CHARS", default=40000)
AI_MENU_IMPORT_HTTP_TIMEOUT = env.int("AI_MENU_IMPORT_HTTP_TIMEOUT", default=60)
# A spend guard against a generation that starts repeating itself, not a size limit:
# a truncated answer is invalid JSON, which fails without a refund. Kept well above what
# a full annual menu needs (a 45-day file measured ~5000 output tokens).
AI_MENU_IMPORT_MAX_OUTPUT_TOKENS = env.int(
    "AI_MENU_IMPORT_MAX_OUTPUT_TOKENS", default=16384
)
AI_MENU_IMPORT_MAX_RETRIES = env.int("AI_MENU_IMPORT_MAX_RETRIES", default=1)
# Must stay below Q_CLUSTER["retry"], otherwise the broker redelivers a task that is
# still running and the same file gets billed to Gemini twice.
AI_MENU_IMPORT_TASK_TIMEOUT = env.int("AI_MENU_IMPORT_TASK_TIMEOUT", default=150)
AI_MENU_IMPORT_DRAFT_RETENTION_DAYS = env.int(
    "AI_MENU_IMPORT_DRAFT_RETENTION_DAYS", default=7
)
# Cron for the retention run, applied by `manage.py setup_ai_import_schedule`. At night,
# when deleting rows and files competes with nothing.
AI_MENU_IMPORT_PURGE_SCHEDULE = env(
    "AI_MENU_IMPORT_PURGE_SCHEDULE", default="30 3 * * *"
)

# The scheduled slot fires a thin wrapper that re-queues the real fan-out as an
# async_task with this timeout, so the per-subscriber loop runs on its own budget
# instead of the cluster's default 60s (#266). Must stay below Q_CLUSTER["retry"]
# (300s) or the broker redelivers a run that is still sending.
NOTIFICATION_TASK_TIMEOUT = env.int("NOTIFICATION_TASK_TIMEOUT", default=240)

# Cron for each daily menu-notification slot, applied by
# `manage.py setup_notification_schedules` (run from entrypoint.sh on every deploy).
# Times are in the server timezone. The slots are self-describing — override only to
# shift the hour (#267).
NOTIFICATION_SCHEDULE_CRONS = {
    "previous_day_6pm": env("NOTIFICATION_CRON_PREVIOUS_DAY_6PM", default="0 18 * * *"),
    "same_day_9am": env("NOTIFICATION_CRON_SAME_DAY_9AM", default="0 9 * * *"),
    "same_day_12pm": env("NOTIFICATION_CRON_SAME_DAY_12PM", default="0 12 * * *"),
    "same_day_6pm": env("NOTIFICATION_CRON_SAME_DAY_6PM", default="0 18 * * *"),
}

# DJANGO REST FRAMEWORK
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
    "DEFAULT_PAGINATION_CLASS": "school_menu.api.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "school_menu.api.exceptions.custom_exception_handler",
}

# CONTENT SECURITY POLICY
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'nonce-{nonce}'",
)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # Tailwind requires unsafe-inline
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "data:")
CSP_CONNECT_SRC = ("'self'",)
# Nothing is framed: the share button is a plain link opened in a new tab, and the
# Facebook SDK that used to need these allowances is gone (#240).
CSP_FRAME_SRC = ("'none'",)

# Report-only mode initially to avoid breaking existing functionality
CSP_REPORT_ONLY = True

# Trust the reverse proxy (Coolify) TLS termination so Django recognises
# forwarded requests as HTTPS. Without this the CSRF Origin check compares the
# browser's https Origin against an http scheme and rejects logins (#222).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


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

    # DJANGO CRAWL - Site crawler for broken links / runtime errors (dev only)
    INSTALLED_APPS += ["django_crawl"]

    # DJANGO-DEVBAR - replaces django-debug-toolbar (#243). Wired here rather than in the
    # base config so nothing debugging-related ships in the production image.
    _security_idx = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
    MIDDLEWARE.insert(_security_idx + 1, "django_devbar.DevBarMiddleware")

    # DJANGO SILK - Performance profiler (dev only)
    INSTALLED_APPS += ["silk"]
    MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]

    # Silk configuration
    SILKY_PYTHON_PROFILER = False  # Disable to avoid .prof file issues
    SILKY_PYTHON_PROFILER_BINARY = False
    SILKY_AUTHENTICATION = True
    SILKY_AUTHORISATION = True
    SILKY_META = True
    SILKY_MAX_REQUEST_BODY_SIZE = 1024  # Limit stored request size (KB)
    SILKY_MAX_RESPONSE_BODY_SIZE = 1024  # Limit stored response size (KB)
    SILKY_MAX_RECORDED_REQUESTS = 1000  # Auto-cleanup old requests

    # DJANGO-Q
    Q_CLUSTER = {
        "name": "school_menu",
        "workers": 4,
        "timeout": 60,
        # Must exceed the longest per-task timeout (AI_MENU_IMPORT_TASK_TIMEOUT), or the
        # broker redelivers a task that is still running.
        "retry": 300,
        "queue_limit": 50,
        "bulk": 10,
        "orm": "default",
        "catch_up": False,
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": "",  # nosec B105
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
    SCHEDULED_BACKUPS: dict[str, Any] = {
        "ENABLED": False,
    }

# PRODUCTION SPECIFIC SETTINGS
elif ENVIRONMENT == "prod":
    DEBUG = env.bool("DEBUG", default=False)
    ALLOWED_HOSTS = env("ALLOWED_HOSTS")
    CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS").split(",")
    PREPEND_WWW = REDIRECT_WWW

    # TRANSPORT SECURITY
    # The Coolify proxy already redirects http -> https and terminates TLS
    # (see SECURE_PROXY_SSL_HEADER above); these are defence in depth.
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True

    # STATIC FILES
    # Hashed filenames + manifest, so whitenoise can serve them immutable and a browser can
    # never pair a cached stylesheet with newer HTML after a deploy (#242). Production only:
    # the manifest is written by collectstatic, and dev/test never run it, so requiring it
    # everywhere would break {% static %} outside the container.
    STORAGES["staticfiles"] = {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    }
    # Verified in production with a 1 hour max-age before raising it to a year (#230).
    SECURE_HSTS_SECONDS = 31536000
    # SECURE_HSTS_INCLUDE_SUBDOMAINS stays off on purpose: mail.menuscolastico.it (Aruba
    # webmail) and admin.menuscolastico.it serve HTTP only — no TLS listener on port 443 —
    # so including subdomains would make both unreachable from any browser that has visited
    # the site. Revisit only if those hosts move to HTTPS. SECURE_HSTS_PRELOAD stays off too:
    # removal from the browser preload list takes months.
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
    # UMAMI TRACKING
    UMAMI_SCRIPT_URL = env("UMAMI_SCRIPT_URL", default=None)
    UMAMI_WEBSITE_ID = env("UMAMI_WEBSITE_ID", default=None)
    UMAMI_DOMAINS = env("UMAMI_DOMAINS", default=None)

    # Add Umami to CSP if configured
    if UMAMI_SCRIPT_URL:
        CSP_SCRIPT_SRC += (UMAMI_SCRIPT_URL,)
    # DBBACKUP
    DBBACKUP_FILENAME_TEMPLATE = "MenuAppCloud-{datetime}.{extension}"
    # Retention is NOT enforced by dbbackup: `--clean` filters candidates by a
    # substring match on the DB alias, and this template carries no {databasename},
    # so it never deletes anything. Instead an OVH Object Storage lifecycle rule on
    # the `django-db-backup` bucket expires objects with prefix `MenuAppCloud-`
    # after 84 days (~12 weekly dumps). See django_scheduled_backups/README.md for
    # the rule and how to apply it. Keep any future DBBACKUP_CLEANUP_KEEP well
    # below that window so the two mechanisms do not fight. (#256)
    # DJANGO-Q
    Q_CLUSTER = {
        "name": "school_menu",
        "workers": 4,
        "timeout": 60,
        # Must exceed the longest per-task timeout (AI_MENU_IMPORT_TASK_TIMEOUT), or the
        # broker redelivers a task that is still running.
        "retry": 300,
        "queue_limit": 50,
        "bulk": 10,
        "orm": "default",
        "catch_up": False,
        "redis": {
            "host": env("REDIS_HOST"),
            "port": 6379,
            "db": 0,
            "password": env("REDIS_PASSWORD", default=""),
        },
    }

    # CACHES - Use Redis with database fallback in production
    redis_password = env("REDIS_PASSWORD", default="")
    redis_host = env("REDIS_HOST")
    redis_url = (
        f"redis://:{redis_password}@{redis_host}:6379/1"
        if redis_password
        else f"redis://{redis_host}:6379/1"
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

    # CACHE TIMEOUTS - TTL values for different data types
    CACHE_TIMEOUTS = {
        "MEAL": 86400,  # 24 hours - meal data changes infrequently
        "ANNUAL_MEAL": 604800,  # 7 days - annual menus are more stable
        "TYPES_MENU": 86400,  # 24 hours - alternative menu availability
        "JSON_API": 86400,  # 24 hours - public JSON API responses
        "SCHOOL_PAGE": 86400,  # 24 hours - public school menu pages
    }

    # DJANGO SCHEDULED BACKUPS - Enabled in production only
    SCHEDULED_BACKUPS = {
        # Enable/disable the backup system
        "ENABLED": True,
        # Who gets backup mail. Set explicitly rather than falling back to ADMINS:
        # the fallback yields (name, address) tuples that send_mail cannot deliver,
        # so a failed backup would notify nobody (#256).
        "NOTIFICATION_EMAILS": [ADMIN_EMAIL],
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
        # Failure-only: a weekly "all good" mail trains the reader to ignore backup
        # mail. The admin history / `listbackups` is the positive check (#256).
        "EMAIL_ON_SUCCESS": False,
        # Send email on failed backup
        "EMAIL_ON_FAILURE": True,
        # Task queue backend: 'django_q' or 'celery'
        "TASK_QUEUE": "django_q",
        # Email subject prefix
        "EMAIL_SUBJECT_PREFIX": "[Menu App Backup]",
    }

    # LOGGING
    # The container captures stdout/stderr, so every handler is the console. Without this
    # block a 500 is swallowed: Django's default config sends django.request only to
    # mail_admins, and ADMINS was never set, so the traceback went nowhere (#258).
    # ADMINS also feeds SCHEDULED_BACKUPS' failure email and the mail_admins handler below.
    ADMINS = [("Admin", ADMIN_EMAIL)]
    SERVER_EMAIL = DEFAULT_FROM_EMAIL

    # An email per 500 helps until a crash loop floods the inbox: AdminEmailHandler has no
    # rate limiting, so it stays opt-in behind MAIL_ADMINS_ON_ERROR.
    _request_handlers = ["console"]
    if env.bool("MAIL_ADMINS_ON_ERROR", default=False):
        _request_handlers.append("mail_admins")

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        },
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {name} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "mail_admins": {
                "class": "django.utils.log.AdminEmailHandler",
                "level": "ERROR",
                "filters": ["require_debug_false"],
            },
        },
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "django.request": {
                "handlers": _request_handlers,
                "level": "ERROR",
                "propagate": False,
            },
            # Bots hitting the bare IP or a wrong Host produce a steady trickle of these:
            # log them, but never email.
            "django.security.DisallowedHost": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False,
            },
            "school_menu": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "notifications": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "anymail": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "django_q": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
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
    # Off unless a test opts in, otherwise the suite would behave differently depending
    # on whether the developer running it happens to have a Gemini key in their .env.
    AI_MENU_IMPORT_ENABLED = False
    GEMINI_API_KEY = ""
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        },
    }
    Q_CLUSTER = {
        "name": "school_menu",
        "workers": 1,
        "sync": True,
        "timeout": 60,
        # Must exceed the longest per-task timeout (AI_MENU_IMPORT_TASK_TIMEOUT), or the
        # broker redelivers a task that is still running.
        "retry": 300,
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
