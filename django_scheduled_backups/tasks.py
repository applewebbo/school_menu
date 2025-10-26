"""Backup tasks with email notifications and history tracking."""

import logging

from django.conf import settings
from django.core import management
from django.core.mail import mail_admins
from django.utils.timezone import now

from .conf import get_notification_emails, get_setting
from .models import BackupRun

logger = logging.getLogger(__name__)


def send_success_email(backup_run):
    """
    Send email notification for successful backup.

    Args:
        backup_run: BackupRun instance
    """
    emails = get_notification_emails()
    if not emails:
        logger.warning("No notification emails configured, skipping success email")
        return

    subject_prefix = get_setting("EMAIL_SUBJECT_PREFIX", "[Backup]")
    timestamp = backup_run.completed_at.strftime("%Y-%m-%d %H:%M:%S")

    subject = f"{subject_prefix} {backup_run.get_backup_type_display()} Backup Successful - {timestamp}"

    duration = backup_run.duration_seconds or 0
    message = f"""
{backup_run.get_backup_type_display()} backup completed successfully.

Timestamp: {timestamp}
Duration: {duration} seconds
Environment: {getattr(settings, "ENVIRONMENT", "unknown")}
Storage Backend: {getattr(settings, "DBBACKUP_STORAGE", "default")}

This is an automated message from the Django Scheduled Backups system.
"""

    try:
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=False,
        )
        logger.info(f"Success email sent for backup run #{backup_run.id}")
    except Exception as e:
        logger.error(f"Failed to send success email: {str(e)}")


def send_failure_email(backup_run):
    """
    Send email notification for failed backup.

    Args:
        backup_run: BackupRun instance with error details
    """
    emails = get_notification_emails()
    if not emails:
        logger.warning("No notification emails configured, skipping failure email")
        return

    subject_prefix = get_setting("EMAIL_SUBJECT_PREFIX", "[Backup]")
    timestamp = backup_run.started_at.strftime("%Y-%m-%d %H:%M:%S")

    subject = f"{subject_prefix} {backup_run.get_backup_type_display()} Backup FAILED - {timestamp}"

    message = f"""
⚠️ {backup_run.get_backup_type_display().upper()} BACKUP FAILED ⚠️

Timestamp: {timestamp}
Environment: {getattr(settings, "ENVIRONMENT", "unknown")}
Error: {backup_run.error_message}

Please investigate this issue immediately.
Check the Django admin for full error details and traceback.

Backup Run ID: {backup_run.id}

This is an automated message from the Django Scheduled Backups system.
"""

    try:
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=False,
        )
        logger.info(f"Failure email sent for backup run #{backup_run.id}")
    except Exception as e:
        logger.error(f"Failed to send failure notification email: {str(e)}")


def scheduled_database_backup():
    """
    Scheduled task to backup database with email notification.

    This function is called by Django-Q2 scheduler or Celery.
    It tracks the backup execution, sends email notifications,
    and logs all events.

    Returns:
        str: Success message for task tracking

    Raises:
        Exception: Re-raises any backup errors after logging
    """
    backup_run = BackupRun.objects.create(
        backup_type="database",
        status="running",
    )

    logger.info(f"Starting database backup (run #{backup_run.id})")

    try:
        # Perform the backup using django-dbbackup
        management.call_command("dbbackup", "--clean")

        # Mark as successful
        backup_run.status = "success"
        backup_run.completed_at = now()
        backup_run.calculate_duration()
        backup_run.save()

        logger.info(
            f"Database backup completed successfully (run #{backup_run.id}, "
            f"duration: {backup_run.duration_seconds}s)"
        )

        # Send success email if enabled
        if get_setting("EMAIL_ON_SUCCESS", True):
            send_success_email(backup_run)

        return f"Database backup successful (run #{backup_run.id})"

    except Exception as e:
        # Mark as failed
        backup_run.status = "failed"
        backup_run.completed_at = now()
        backup_run.error_message = str(e)
        backup_run.calculate_duration()
        backup_run.save()

        logger.error(
            f"Database backup failed (run #{backup_run.id}): {str(e)}",
            exc_info=True,
        )

        # Send failure email if enabled
        if get_setting("EMAIL_ON_FAILURE", True):
            send_failure_email(backup_run)

        # Re-raise to mark task as failed in Django-Q/Celery
        raise


def scheduled_media_backup():
    """
    Scheduled task to backup media files with email notification.

    This function is called by Django-Q2 scheduler or Celery.
    It tracks the backup execution, sends email notifications,
    and logs all events.

    Returns:
        str: Success message for task tracking

    Raises:
        Exception: Re-raises any backup errors after logging
    """
    backup_run = BackupRun.objects.create(
        backup_type="media",
        status="running",
    )

    logger.info(f"Starting media backup (run #{backup_run.id})")

    try:
        # Perform the backup using django-dbbackup's mediabackup command
        management.call_command("mediabackup", "--clean")

        # Mark as successful
        backup_run.status = "success"
        backup_run.completed_at = now()
        backup_run.calculate_duration()
        backup_run.save()

        logger.info(
            f"Media backup completed successfully (run #{backup_run.id}, "
            f"duration: {backup_run.duration_seconds}s)"
        )

        # Send success email if enabled
        if get_setting("EMAIL_ON_SUCCESS", True):
            send_success_email(backup_run)

        return f"Media backup successful (run #{backup_run.id})"

    except Exception as e:
        # Mark as failed
        backup_run.status = "failed"
        backup_run.completed_at = now()
        backup_run.error_message = str(e)
        backup_run.calculate_duration()
        backup_run.save()

        logger.error(
            f"Media backup failed (run #{backup_run.id}): {str(e)}",
            exc_info=True,
        )

        # Send failure email if enabled
        if get_setting("EMAIL_ON_FAILURE", True):
            send_failure_email(backup_run)

        # Re-raise to mark task as failed in Django-Q/Celery
        raise


# Maintain backward compatibility with existing core.tasks.backup function
def backup():
    """
    Legacy backup function for backward compatibility.

    Simply calls django-dbbackup command.
    For scheduled backups with notifications, use scheduled_database_backup() instead.
    """
    return management.call_command("dbbackup")
