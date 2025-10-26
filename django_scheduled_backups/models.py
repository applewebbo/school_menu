"""Models for tracking backup execution history."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class BackupRun(models.Model):
    """Track backup execution history with status and errors."""

    BACKUP_TYPE_CHOICES = [
        ("database", _("Database")),
        ("media", _("Media")),
    ]

    STATUS_CHOICES = [
        ("running", _("Running")),
        ("success", _("Success")),
        ("failed", _("Failed")),
    ]

    backup_type = models.CharField(
        max_length=20,
        choices=BACKUP_TYPE_CHOICES,
        verbose_name=_("Backup Type"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="running",
        verbose_name=_("Status"),
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Started At"),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed At"),
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("Error Message"),
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Duration (seconds)"),
    )

    class Meta:
        verbose_name = _("Backup Run")
        verbose_name_plural = _("Backup Runs")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["-started_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["backup_type"]),
        ]

    def __str__(self):
        return f"{self.get_backup_type_display()} - {self.get_status_display()} - {self.started_at}"

    def calculate_duration(self):
        """Calculate duration in seconds if backup is completed."""
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
            return self.duration_seconds
        return None
