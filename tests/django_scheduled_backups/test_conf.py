"""Tests for configuration settings."""

from django.test import override_settings

from django_scheduled_backups.conf import (
    DEFAULT_SETTINGS,
    get_database_backup_config,
    get_media_backup_config,
    get_notification_emails,
    get_setting,
    is_enabled,
)


class TestConfigurationSettings:
    """Test configuration helper functions."""

    @override_settings(SCHEDULED_BACKUPS={"ENABLED": True})
    def test_get_setting_returns_configured_value(self):
        """Test that get_setting returns configured value."""
        assert get_setting("ENABLED") is True

    def test_get_setting_returns_default_when_not_configured(self):
        """Test that get_setting returns default when key not found."""
        assert get_setting("NON_EXISTENT_KEY", "default_value") == "default_value"

    @override_settings(SCHEDULED_BACKUPS={})
    def test_get_setting_returns_none_when_no_default(self):
        """Test that get_setting returns None when no default provided."""
        assert get_setting("NON_EXISTENT_KEY") is None

    @override_settings(SCHEDULED_BACKUPS={"NOTIFICATION_EMAILS": ["test@example.com"]})
    def test_get_notification_emails_from_setting(self):
        """Test getting notification emails from settings."""
        emails = get_notification_emails()
        assert emails == ["test@example.com"]

    @override_settings(SCHEDULED_BACKUPS={"NOTIFICATION_EMAILS": "single@example.com"})
    def test_get_notification_emails_converts_string_to_list(self):
        """Test that single email string is converted to list."""
        emails = get_notification_emails()
        assert emails == ["single@example.com"]

    @override_settings(
        SCHEDULED_BACKUPS={},
        ADMINS=[("Admin", "admin@example.com"), ("Manager", "manager@example.com")],
    )
    def test_get_notification_emails_falls_back_to_admins(self):
        """Test that notification emails fall back to ADMINS."""
        emails = get_notification_emails()
        assert "admin@example.com" in emails
        assert "manager@example.com" in emails

    @override_settings(SCHEDULED_BACKUPS={"ENABLED": True})
    def test_is_enabled_returns_true(self):
        """Test is_enabled returns True when enabled."""
        assert is_enabled() is True

    @override_settings(SCHEDULED_BACKUPS={"ENABLED": False})
    def test_is_enabled_returns_false(self):
        """Test is_enabled returns False when disabled."""
        assert is_enabled() is False

    @override_settings(SCHEDULED_BACKUPS={})
    def test_is_enabled_returns_default(self):
        """Test is_enabled returns default when not configured."""
        assert is_enabled() == DEFAULT_SETTINGS["ENABLED"]

    @override_settings(
        SCHEDULED_BACKUPS={
            "DATABASE_BACKUP": {"enabled": True, "schedule": "0 3 * * *"}
        }
    )
    def test_get_database_backup_config(self):
        """Test getting database backup configuration."""
        config = get_database_backup_config()
        assert config["enabled"] is True
        assert config["schedule"] == "0 3 * * *"

    @override_settings(
        SCHEDULED_BACKUPS={"MEDIA_BACKUP": {"enabled": True, "schedule": "0 4 * * 0"}}
    )
    def test_get_media_backup_config(self):
        """Test getting media backup configuration."""
        config = get_media_backup_config()
        assert config["enabled"] is True
        assert config["schedule"] == "0 4 * * 0"

    @override_settings(SCHEDULED_BACKUPS={})
    def test_get_backup_configs_return_defaults(self):
        """Test that backup configs return defaults when not configured."""
        db_config = get_database_backup_config()
        media_config = get_media_backup_config()

        assert db_config == DEFAULT_SETTINGS["DATABASE_BACKUP"]
        assert media_config == DEFAULT_SETTINGS["MEDIA_BACKUP"]
