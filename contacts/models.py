from django.conf import settings
from django.db import models


class MenuReport(models.Model):
    name = models.CharField(max_length=100)
    message = models.TextField(max_length=1000)
    get_notified = models.BooleanField(default=False)
    email = models.EmailField(null=True, blank=True)
    receiver = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "segnalazione"
        verbose_name_plural = "segnalazioni"

    def __str__(self):
        return f"Segnalazione da {self.name}"
