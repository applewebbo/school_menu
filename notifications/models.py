from django.db import models

from school_menu.models import School


class AnonymousMenuNotification(models.Model):
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="anonymous_notifications"
    )
    subscription_info = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Anonymous Menu Notification"
        verbose_name_plural = "Anonymous Menu Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Anonymous subscription for {self.school} at {self.created_at}"
