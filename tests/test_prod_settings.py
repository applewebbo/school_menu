"""The production settings block never runs under the test environment, so a broken
LOGGING dict would surface for the first time when the container boots (#258).

These tests import ``core.settings`` in a subprocess with ``ENVIRONMENT=prod`` and a
throwaway env, then feed the resulting ``LOGGING`` through ``logging.config.dictConfig``
exactly as Django does at startup.
"""

import json
import subprocess  # nosec B404
import sys

from django.conf import settings

# Every env var the base and prod blocks read without a default. Values are throwaway:
# the test only builds settings, it never connects to anything.
PROD_ENV = {
    "ENVIRONMENT": "prod",
    "DJANGO_SETTINGS_MODULE": "core.settings",
    "SECRET_KEY": "test-only-secret",  # nosec B105
    "ADMIN_EMAIL": "admin@example.com",
    "MAILGUN_API_KEY": "key-test",
    "MAILGUN_API_URL": "https://api.eu.mailgun.net/v3",
    "MAILGUN_SENDER_DOMAIN": "mg.example.com",
    "VAPID_PUBLIC_KEY": "test-public",
    "VAPID_PRIVATE_KEY": "test-private",
    "ALLOWED_HOSTS": "example.com",
    "CSRF_TRUSTED_ORIGINS": "https://example.com",
    "DB_NAME": "x",
    "DB_USER": "x",
    "DB_PASSWORD": "x",  # nosec B105
    "DB_HOST": "x",
    "REDIS_HOST": "localhost",
}

SCRIPT = """
import json
import logging.config

import django

django.setup()
from django.conf import settings

from django_scheduled_backups.conf import get_notification_emails

logging.config.dictConfig(settings.LOGGING)
print(json.dumps({
    "loggers": sorted(settings.LOGGING["loggers"]),
    "request_handlers": settings.LOGGING["loggers"]["django.request"]["handlers"],
    "admins": settings.ADMINS,
    "server_email": settings.SERVER_EMAIL,
    "scheduled_backups": settings.SCHEDULED_BACKUPS,
    "backup_notification_emails": get_notification_emails(),
}))
"""


def _load_prod_settings(extra_env=None):
    env = {**PROD_ENV, **(extra_env or {})}
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SCRIPT],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_prod_logging_is_a_valid_dictconfig():
    """dictConfig raises on a malformed handler, filter or formatter reference."""
    data = _load_prod_settings()

    assert {
        "anymail",
        "django",
        "django.request",
        "django.security.DisallowedHost",
        "django_q",
        "notifications",
        "school_menu",
    } <= set(data["loggers"])
    assert data["admins"] == [["Admin", "admin@example.com"]]
    assert data["server_email"] == settings.DEFAULT_FROM_EMAIL


def test_backup_notifications_have_a_deliverable_recipient():
    """NOTIFICATION_EMAILS is an explicit list of address strings, so a failed backup
    actually sends mail — the ADMINS fallback yields (name, address) tuples that
    send_mail cannot use (#256)."""
    data = _load_prod_settings()
    backups = data["scheduled_backups"]

    assert backups["NOTIFICATION_EMAILS"] == ["admin@example.com"]
    assert data["backup_notification_emails"] == ["admin@example.com"]
    assert all(isinstance(addr, str) for addr in data["backup_notification_emails"])


def test_backup_email_is_failure_only():
    """A weekly 'all good' mail trains the reader to ignore backup mail; the admin
    history is the positive check instead (#256)."""
    backups = _load_prod_settings()["scheduled_backups"]

    assert backups["EMAIL_ON_SUCCESS"] is False
    assert backups["EMAIL_ON_FAILURE"] is True


def test_mail_admins_on_error_is_opt_in():
    """django.request logs only to the console until MAIL_ADMINS_ON_ERROR is set."""
    assert _load_prod_settings()["request_handlers"] == ["console"]

    with_mail = _load_prod_settings({"MAIL_ADMINS_ON_ERROR": "True"})
    assert with_mail["request_handlers"] == ["console", "mail_admins"]
