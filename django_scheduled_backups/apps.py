"""App configuration for django_scheduled_backups."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DjangoScheduledBackupsConfig(AppConfig):
    """Configuration for the django_scheduled_backups app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_scheduled_backups"
    verbose_name = _("Scheduled Backups")
