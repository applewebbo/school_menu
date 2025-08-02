from django.db import models

from school_menu.models import School


class AnonymousMenuNotification(models.Model):
    PREVIOUS_DAY_6PM = "previous_day_6pm"
    SAME_DAY_9AM = "same_day_9am"
    SAME_DAY_12PM = "same_day_12pm"
    SAME_DAY_6PM = "same_day_6pm"

    NOTIFICATION_TIME_CHOICES = [
        (PREVIOUS_DAY_6PM, "Alle 18:00 del giorno prima"),
        (SAME_DAY_9AM, "Alle 9:00"),
        (SAME_DAY_12PM, "Alle 12:00"),
        (SAME_DAY_6PM, "Alle 18:00"),
    ]

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="anonymous_notifications"
    )
    subscription_info = models.JSONField()
    daily_notification = models.BooleanField(default=False)
    notification_time = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TIME_CHOICES,
        default=SAME_DAY_12PM,
        verbose_name="Orario di notifica",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Anonymous Menu Notification"
        verbose_name_plural = "Anonymous Menu Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Anonymous subscription for {self.school} at {self.created_at}"


class DailyNotification(models.Model):
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="daily_notifications"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Daily Notification"
        verbose_name_plural = "Daily Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Daily notification for {self.school} at {self.created_at}"
