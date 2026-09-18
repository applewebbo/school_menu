from django.conf import settings
from django.db import models


class MenuReport(models.Model):
    name = models.CharField(max_length=100)
    message = models.TextField(max_length=1000)
    get_notified = models.BooleanField(default=False)
    email = models.EmailField(null=True, blank=True)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_error = models.TextField(
        blank=True,
        default="",
        help_text="Error message if the report-received email to the receiver failed to send (#280)",
    )
    feedback_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When a feedback reply was successfully sent for this report (#280)",
    )

    class Meta:
        verbose_name = "segnalazione"
        verbose_name_plural = "segnalazioni"

    def __str__(self):
        return f"Segnalazione da {self.name}"
