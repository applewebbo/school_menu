"""``ENVIRONMENT=restore`` exists only to exercise ``dbrestore`` against a real
Postgres without any chance of aiming it at production (#256).

The database name and host are hard-coded in the settings block, never read from
``DB_NAME`` / ``DB_HOST``. These tests import ``core.settings`` in a subprocess
with a deliberately hostile environment (prod-looking DB vars) and assert the
restore target stays local.
"""

import json
import subprocess  # nosec B404
import sys

from django.conf import settings

# A hostile environment: every value points at a "production" host. The restore
# block must ignore all of it.
RESTORE_ENV = {
    "ENVIRONMENT": "restore",
    "DJANGO_SETTINGS_MODULE": "core.settings",
    "SECRET_KEY": "test-only-secret",  # nosec B105
    "ADMIN_EMAIL": "admin@example.com",
    "MAILGUN_API_KEY": "key-test",
    "MAILGUN_API_URL": "https://api.eu.mailgun.net/v3",
    "MAILGUN_SENDER_DOMAIN": "mg.example.com",
    "VAPID_PUBLIC_KEY": "test-public",
    "VAPID_PRIVATE_KEY": "test-private",
    "DB_NAME": "school_menu_prod",
    "DB_USER": "prod_user",
    "DB_PASSWORD": "prod_password",  # nosec B105
    "DB_HOST": "db.production.example.com",
    "REDIS_HOST": "redis.production.example.com",
}

SCRIPT = """
import json

import django

django.setup()
from django.conf import settings

from dbbackup.db.base import get_connector

db = settings.DATABASES["default"]
connector = get_connector()
print(json.dumps({
    "engine": db["ENGINE"],
    "name": db["NAME"],
    "host": db["HOST"],
    "backups_enabled": settings.SCHEDULED_BACKUPS["ENABLED"],
    "debug": settings.DEBUG,
    "dbbackup_storage": settings.STORAGES["dbbackup"]["BACKEND"],
    "restore_suffix": connector.restore_suffix,
}))
"""


def _load_restore_settings(extra_env=None):
    env = {**RESTORE_ENV, **(extra_env or {})}
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


def test_restore_target_is_a_fixed_local_database():
    """NAME and HOST are constants, so DB_NAME / DB_HOST cannot redirect a restore
    at production even when they are set to production values."""
    data = _load_restore_settings()

    assert data["engine"].endswith("postgresql")
    assert data["name"] == "menu_restore_test"
    assert data["host"] == "localhost"


def test_restore_env_keeps_scheduled_backups_and_debug_off():
    data = _load_restore_settings()

    assert data["backups_enabled"] is False
    assert data["debug"] is False


def test_restore_env_uses_the_real_dbbackup_storage():
    """The download path must be the real one, so restoring exercises storage too."""
    data = _load_restore_settings()

    assert data["dbbackup_storage"] == "storages.backends.s3boto3.S3Boto3Storage"


def test_restore_skips_ownership_and_privileges():
    """pg_restore must not choke on OWNER TO / GRANT for a prod role the local
    cluster does not have; with --single-transaction one such line would abort the
    whole restore (#256)."""
    data = _load_restore_settings()

    assert "--no-owner" in data["restore_suffix"]
    assert "--no-privileges" in data["restore_suffix"]
