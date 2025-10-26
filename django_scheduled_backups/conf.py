"""Configuration settings for django_scheduled_backups."""

from django.conf import settings


def get_setting(key, default=None):
    """
    Get a setting from SCHEDULED_BACKUPS dict in Django settings.

    Args:
        key: Setting key to retrieve
        default: Default value if key not found

    Returns:
        Setting value or default
    """
    backup_settings = getattr(settings, "SCHEDULED_BACKUPS", {})
    return backup_settings.get(key, default)


# Default configuration
DEFAULT_SETTINGS = {
    # Enable/disable the backup system
    "ENABLED": True,
    # Email addresses to notify (falls back to ADMINS if not set)
    "NOTIFICATION_EMAILS": None,
    # Database backup configuration
    "DATABASE_BACKUP": {
        "enabled": True,
        "schedule": "0 2 * * *",  # Daily at 2 AM
    },
    # Media backup configuration
    "MEDIA_BACKUP": {
        "enabled": False,
        "schedule": "0 3 * * 0",  # Weekly on Sunday at 3 AM
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
    "EMAIL_SUBJECT_PREFIX": "[Backup]",
}


def get_notification_emails():
    """
    Get list of email addresses for notifications.

    Returns:
        List of email addresses from NOTIFICATION_EMAILS setting,
        or falls back to ADMINS if not configured.
    """
    emails = get_setting("NOTIFICATION_EMAILS")
    if emails:
        return emails if isinstance(emails, list) else [emails]

    # Fallback to ADMINS
    admins = getattr(settings, "ADMINS", [])
    return [email for name, email in admins]


def is_enabled():
    """Check if backup system is enabled."""
    return get_setting("ENABLED", DEFAULT_SETTINGS["ENABLED"])


def get_database_backup_config():
    """Get database backup configuration."""
    return get_setting("DATABASE_BACKUP", DEFAULT_SETTINGS["DATABASE_BACKUP"])


def get_media_backup_config():
    """Get media backup configuration."""
    return get_setting("MEDIA_BACKUP", DEFAULT_SETTINGS["MEDIA_BACKUP"])
