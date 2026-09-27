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
        ("running", _("In corso")),
        ("success", _("Completato")),
        ("failed", _("Fallito")),
    ]

    backup_type = models.CharField(
        max_length=20,
        choices=BACKUP_TYPE_CHOICES,
        verbose_name=_("Tipo di backup"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="running",
        verbose_name=_("Stato"),
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Avviato il"),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completato il"),
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("Messaggio di errore"),
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Durata (secondi)"),
    )

    class Meta:
        verbose_name = _("Esecuzione backup")
        verbose_name_plural = _("Esecuzioni backup")
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
