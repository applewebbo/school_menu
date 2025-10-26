"""Tests for backup tasks with email notifications."""

from unittest.mock import patch

import pytest
from django.core import mail
from django.test import override_settings
from django.utils.timezone import now

from django_scheduled_backups.models import BackupRun
from django_scheduled_backups.tasks import (
    backup,
    scheduled_database_backup,
    scheduled_media_backup,
    send_failure_email,
    send_success_email,
)

pytestmark = pytest.mark.django_db


class TestScheduledDatabaseBackup:
    """Test the scheduled database backup task with email notifications."""

    @override_settings(ADMINS=[("Admin", "admin@example.com")])
    @patch("django_scheduled_backups.tasks.management.call_command")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_backup_success_creates_record_and_sends_email(
        self, mock_get_setting, mock_call_command
    ):
        """Test that successful backup creates record and sends email."""
        # Arrange
        mock_call_command.return_value = None
        mock_get_setting.side_effect = lambda key, default=None: {
            "EMAIL_ON_SUCCESS": True,
            "EMAIL_ON_FAILURE": True,
            "EMAIL_SUBJECT_PREFIX": "[Backup]",
        }.get(key, default)

        # Act
        result = scheduled_database_backup()

        # Assert
        mock_call_command.assert_called_once_with("dbbackup", "--clean")
        assert "successful" in result.lower()

        # Check database record
        backup_run = BackupRun.objects.filter(backup_type="database").first()
        assert backup_run is not None
        assert backup_run.status == "success"
        assert backup_run.completed_at is not None
        assert backup_run.duration_seconds is not None
        assert backup_run.error_message == ""

        # Check email sent
        assert len(mail.outbox) == 1
        assert "[Backup] Database Backup Successful" in mail.outbox[0].subject
        assert "completed successfully" in mail.outbox[0].body

    @override_settings(ADMINS=[("Admin", "admin@example.com")])
    @patch("django_scheduled_backups.tasks.management.call_command")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_backup_failure_creates_record_and_sends_email_and_raises(
        self, mock_get_setting, mock_call_command
    ):
        """Test that failed backup creates record, sends email, and re-raises exception."""
        # Arrange
        mock_call_command.side_effect = Exception("Database connection failed")
        mock_get_setting.side_effect = lambda key, default=None: {
            "EMAIL_ON_SUCCESS": True,
            "EMAIL_ON_FAILURE": True,
            "EMAIL_SUBJECT_PREFIX": "[Backup]",
        }.get(key, default)

        # Act & Assert
        with pytest.raises(Exception, match="Database connection failed"):
            scheduled_database_backup()

        mock_call_command.assert_called_once_with("dbbackup", "--clean")

        # Check database record
        backup_run = BackupRun.objects.filter(backup_type="database").first()
        assert backup_run is not None
        assert backup_run.status == "failed"
        assert backup_run.completed_at is not None
        assert "Database connection failed" in backup_run.error_message

        # Check email sent
        assert len(mail.outbox) == 1
        assert "[Backup] Database Backup FAILED" in mail.outbox[0].subject
        assert "Database connection failed" in mail.outbox[0].body
        assert "⚠️" in mail.outbox[0].body

    @patch("django_scheduled_backups.tasks.management.call_command")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_backup_success_without_email(self, mock_get_setting, mock_call_command):
        """Test that backup works when email notifications are disabled."""
        # Arrange
        mock_call_command.return_value = None
        mock_get_setting.side_effect = lambda key, default=None: {
            "EMAIL_ON_SUCCESS": False,
            "EMAIL_ON_FAILURE": True,
        }.get(key, default)

        # Act
        result = scheduled_database_backup()

        # Assert
        assert "successful" in result.lower()
        backup_run = BackupRun.objects.filter(backup_type="database").first()
        assert backup_run.status == "success"

        # No email should be sent
        assert len(mail.outbox) == 0

    @patch("django_scheduled_backups.tasks.management.call_command")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_backup_failure_without_email(self, mock_get_setting, mock_call_command):
        """Test that backup works when failure email notifications are disabled."""
        # Arrange
        mock_call_command.side_effect = Exception("Backup failed")
        mock_get_setting.side_effect = lambda key, default=None: {
            "EMAIL_ON_SUCCESS": True,
            "EMAIL_ON_FAILURE": False,
        }.get(key, default)

        # Act & Assert
        with pytest.raises(Exception, match="Backup failed"):
            scheduled_database_backup()

        # Check backup run created
        backup_run = BackupRun.objects.filter(backup_type="database").first()
        assert backup_run.status == "failed"

        # No email should be sent
        assert len(mail.outbox) == 0

    @patch("django_scheduled_backups.tasks.management.call_command")
    @patch("django_scheduled_backups.tasks.mail_admins")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_backup_failure_with_email_error_still_raises_backup_error(
        self, mock_get_setting, mock_mail_admins, mock_call_command
    ):
        """Test that if email fails, the original backup error is still raised."""
        # Arrange
        mock_call_command.side_effect = Exception("Backup failed")
        mock_mail_admins.side_effect = Exception("Email send failed")
        mock_get_setting.side_effect = lambda key, default=None: {
            "EMAIL_ON_SUCCESS": True,
            "EMAIL_ON_FAILURE": True,
        }.get(key, default)

        # Act & Assert - should raise the backup error, not email error
        with pytest.raises(Exception, match="Backup failed"):
            scheduled_database_backup()

        # Check that backup run was created with failure status
        backup_run = BackupRun.objects.filter(backup_type="database").first()
        assert backup_run.status == "failed"


class TestScheduledMediaBackup:
    """Test the scheduled media backup task with email notifications."""

    @override_settings(ADMINS=[("Admin", "admin@example.com")])
    @patch("django_scheduled_backups.tasks.management.call_command")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_media_backup_success(self, mock_get_setting, mock_call_command):
        """Test that successful media backup works correctly."""
        # Arrange
        mock_call_command.return_value = None
        mock_get_setting.side_effect = lambda key, default=None: {
            "EMAIL_ON_SUCCESS": True,
            "EMAIL_SUBJECT_PREFIX": "[Backup]",
        }.get(key, default)

        # Act
        result = scheduled_media_backup()

        # Assert
        mock_call_command.assert_called_once_with("mediabackup", "--clean")
        assert "successful" in result.lower()

        # Check database record
        backup_run = BackupRun.objects.filter(backup_type="media").first()
        assert backup_run is not None
        assert backup_run.status == "success"

        # Check email sent
        assert len(mail.outbox) == 1
        assert "[Backup] Media Backup Successful" in mail.outbox[0].subject

    @patch("django_scheduled_backups.tasks.management.call_command")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_media_backup_failure(self, mock_get_setting, mock_call_command):
        """Test that failed media backup handles errors correctly."""
        # Arrange
        mock_call_command.side_effect = Exception("Media backup failed")
        mock_get_setting.side_effect = lambda key, default=None: {
            "EMAIL_ON_FAILURE": True,
            "EMAIL_SUBJECT_PREFIX": "[Backup]",
        }.get(key, default)

        # Act & Assert
        with pytest.raises(Exception, match="Media backup failed"):
            scheduled_media_backup()

        # Check database record
        backup_run = BackupRun.objects.filter(backup_type="media").first()
        assert backup_run is not None
        assert backup_run.status == "failed"
        assert "Media backup failed" in backup_run.error_message

    @patch("django_scheduled_backups.tasks.management.call_command")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_media_backup_success_without_email(
        self, mock_get_setting, mock_call_command
    ):
        """Test that media backup works when success email is disabled."""
        # Arrange
        mock_call_command.return_value = None
        mock_get_setting.side_effect = lambda key, default=None: {
            "EMAIL_ON_SUCCESS": False,
        }.get(key, default)

        # Act
        result = scheduled_media_backup()

        # Assert
        assert "successful" in result.lower()
        backup_run = BackupRun.objects.filter(backup_type="media").first()
        assert backup_run.status == "success"

        # No email should be sent
        assert len(mail.outbox) == 0

    @patch("django_scheduled_backups.tasks.management.call_command")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_media_backup_failure_without_email(
        self, mock_get_setting, mock_call_command
    ):
        """Test that media backup works when failure email is disabled."""
        # Arrange
        mock_call_command.side_effect = Exception("Media backup failed")
        mock_get_setting.side_effect = lambda key, default=None: {
            "EMAIL_ON_FAILURE": False,
        }.get(key, default)

        # Act & Assert
        with pytest.raises(Exception, match="Media backup failed"):
            scheduled_media_backup()

        # Check database record
        backup_run = BackupRun.objects.filter(backup_type="media").first()
        assert backup_run.status == "failed"

        # No email should be sent
        assert len(mail.outbox) == 0


class TestEmailNotifications:
    """Test email notification functions."""

    @patch("django_scheduled_backups.tasks.get_notification_emails")
    def test_send_success_email_with_no_recipients(self, mock_get_emails):
        """Test that success email is skipped when no recipients configured."""
        # Arrange
        mock_get_emails.return_value = []
        backup_run = BackupRun.objects.create(
            backup_type="database",
            status="success",
            completed_at=now(),
        )
        backup_run.calculate_duration()
        backup_run.save()

        # Act
        send_success_email(backup_run)

        # Assert - no email should be sent
        assert len(mail.outbox) == 0

    @patch("django_scheduled_backups.tasks.get_notification_emails")
    def test_send_failure_email_with_no_recipients(self, mock_get_emails):
        """Test that failure email is skipped when no recipients configured."""
        # Arrange
        mock_get_emails.return_value = []
        backup_run = BackupRun.objects.create(
            backup_type="database",
            status="failed",
            error_message="Test error",
            completed_at=now(),
        )

        # Act
        send_failure_email(backup_run)

        # Assert - no email should be sent
        assert len(mail.outbox) == 0

    @override_settings(ADMINS=[("Admin", "admin@example.com")])
    @patch("django_scheduled_backups.tasks.mail_admins")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_send_success_email_exception_is_logged(
        self, mock_get_setting, mock_mail_admins
    ):
        """Test that exceptions in send_success_email are logged but not raised."""
        # Arrange
        mock_mail_admins.side_effect = Exception("Email server error")
        mock_get_setting.return_value = "[Test]"
        backup_run = BackupRun.objects.create(
            backup_type="database",
            status="success",
            completed_at=now(),
        )
        backup_run.calculate_duration()
        backup_run.save()

        # Act - should not raise exception
        send_success_email(backup_run)

        # Assert - mail_admins was called
        assert mock_mail_admins.called

    @override_settings(ADMINS=[("Admin", "admin@example.com")])
    @patch("django_scheduled_backups.tasks.mail_admins")
    @patch("django_scheduled_backups.tasks.get_setting")
    def test_send_failure_email_exception_is_logged(
        self, mock_get_setting, mock_mail_admins
    ):
        """Test that exceptions in send_failure_email are logged but not raised."""
        # Arrange
        mock_mail_admins.side_effect = Exception("Email server error")
        mock_get_setting.return_value = "[Test]"
        backup_run = BackupRun.objects.create(
            backup_type="database",
            status="failed",
            error_message="Backup error",
            completed_at=now(),
        )

        # Act - should not raise exception
        send_failure_email(backup_run)

        # Assert - mail_admins was called
        assert mock_mail_admins.called


class TestBackupRunModel:
    """Test BackupRun model methods."""

    def test_calculate_duration(self):
        """Test duration calculation."""
        # Arrange
        backup_run = BackupRun.objects.create(
            backup_type="database",
            status="running",
        )

        # Duration should be None before completion
        assert backup_run.calculate_duration() is None

        # Complete the backup
        backup_run.completed_at = now()
        backup_run.save()

        # Duration should be calculated
        duration = backup_run.calculate_duration()
        assert duration is not None
        assert duration >= 0
        assert backup_run.duration_seconds == duration

    def test_str_representation(self):
        """Test string representation of BackupRun."""
        backup_run = BackupRun.objects.create(
            backup_type="database",
            status="success",
        )

        str_repr = str(backup_run)
        assert "Database" in str_repr
        assert "Success" in str_repr


class TestLegacyBackupFunction:
    """Test the legacy backup() function for backward compatibility."""

    @patch("django_scheduled_backups.tasks.management.call_command")
    def test_backup_calls_dbbackup_command(self, mock_call_command):
        """Test that backup() calls dbbackup command without tracking."""
        # Arrange
        mock_call_command.return_value = None

        # Act
        result = backup()

        # Assert
        mock_call_command.assert_called_once_with("dbbackup")
        assert result is None
