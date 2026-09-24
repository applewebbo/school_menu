import hashlib

from django.conf import settings
from django.db import models

from school_menu.models import Meal, School


class AnonymousMenuNotification(models.Model):
    PREVIOUS_DAY_6PM = "previous_day_6pm"
    SAME_DAY_9AM = "same_day_9am"
    SAME_DAY_12PM = "same_day_12pm"
    SAME_DAY_6PM = "same_day_6pm"

    NOTIFICATION_TIME_CHOICES = [
        (PREVIOUS_DAY_6PM, "alle 18:00 del giorno prima"),
        (SAME_DAY_9AM, "alle 9:00"),
        (SAME_DAY_12PM, "alle 12:00"),
        (SAME_DAY_6PM, "alle 18:00"),
    ]

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="anonymous_notifications"
    )
    subscription_info = models.JSONField()
    subscription_endpoint = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="SHA256 hash of the push subscription endpoint for uniqueness",
    )
    daily_notification = models.BooleanField(default=True)
    notification_time = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TIME_CHOICES,
        default=SAME_DAY_12PM,
        verbose_name="Orario di notifica",
    )
    meal_type = models.CharField(
        max_length=1,
        choices=Meal.Types.choices,
        default=Meal.Types.STANDARD,
        verbose_name="Tipo di menu",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Anonymous Menu Notification"
        verbose_name_plural = "Anonymous Menu Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Anonymous subscription for {self.school} at {self.created_at}"

    @staticmethod
    def hash_endpoint(endpoint):
        """
        Generate a SHA256 hash of the subscription endpoint for uniqueness constraint
        """
        return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()

    @classmethod
    def extract_endpoint(cls, subscription_info):
        """
        Extract the endpoint from subscription_info JSON
        """
        if isinstance(subscription_info, dict):
            return subscription_info.get("endpoint", "")
        return ""

    def save(self, *args, **kwargs):
        """
        Override save to automatically set subscription_endpoint from subscription_info
        """
        if not self.subscription_endpoint:
            endpoint = self.extract_endpoint(self.subscription_info)
            if endpoint:
                self.subscription_endpoint = self.hash_endpoint(endpoint)
        super().save(*args, **kwargs)


class DailyNotification(models.Model):
    """
    One row per menu-notification run: an audit trail that a given time slot actually
    fired on a given day, and with what outcome (#268). With Q_CLUSTER catch_up off, a
    worker/redis outage over a slot leaves no other trace.
    """

    notification_time = models.CharField(
        max_length=20,
        choices=AnonymousMenuNotification.NOTIFICATION_TIME_CHOICES,
        default=AnonymousMenuNotification.SAME_DAY_12PM,
        verbose_name="Orario di notifica",
    )
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    pruned_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Daily Notification"
        verbose_name_plural = "Daily Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_notification_time_display()} run at {self.created_at}: "
            f"{self.sent_count} sent, {self.failed_count} failed, "
            f"{self.pruned_count} pruned"
        )


class MonthlyDigest(models.Model):
    """
    One row per monthly admin digest run: an audit trail that the digest for a given
    period was actually built and sent, and with what counts (#280). Mirrors
    ``DailyNotification``'s role for the daily push slots.
    """

    period_start = models.DateField()
    period_end = models.DateField()
    new_schools = models.PositiveIntegerField(default=0)
    menu_reports = models.PositiveIntegerField(default=0)
    report_errors = models.PositiveIntegerField(default=0)
    feedback_sent = models.PositiveIntegerField(default=0)
    new_subscriptions = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Monthly Digest"
        verbose_name_plural = "Monthly Digests"
        ordering = ["-period_start"]

    def __str__(self):
        return (
            f"Digest {self.period_start} - {self.period_end}: "
            f"{self.new_schools} scuole, {self.menu_reports} segnalazioni, "
            f"{self.new_subscriptions} iscrizioni"
        )


class NotificationDeliveryMarker(models.Model):
    """
    Proof that a subscriber already got a given slot on a given date (#270).

    ``_send_menu_notifications`` checks this table (cache-first) before delivering, so
    a task redelivered by the broker after a timeout resumes instead of reprocessing
    subscribers already pushed in the first pass. Kept as a durable table, not just a
    cache entry, so a cache eviction can't reopen the double-send window.
    """

    subscription_endpoint = models.CharField(max_length=64)
    target_date = models.DateField()
    notification_time = models.CharField(
        max_length=20,
        choices=AnonymousMenuNotification.NOTIFICATION_TIME_CHOICES,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification Delivery Marker"
        verbose_name_plural = "Notification Delivery Markers"
        constraints = [
            models.UniqueConstraint(
                fields=["subscription_endpoint", "target_date", "notification_time"],
                name="unique_notification_delivery_marker",
            )
        ]

    def __str__(self):
        return (
            f"{self.subscription_endpoint} delivered {self.notification_time} "
            f"on {self.target_date}"
        )


# Starting content for a new Newsletter's body_html (#289): inline-styled so it
# stays mail-safe even if the admin sends it as-is, and shaped as the two
# paragraphs + feature list the mail template is designed around.
NEWSLETTER_BODY_PLACEHOLDER = """\
<p style="margin:0 0 16px; font-size:15px; line-height:1.6; color:#1f2937;">
  Primo paragrafo: scrivi qui l'introduzione della newsletter.
</p>
<p style="margin:0 0 16px; font-size:15px; line-height:1.6; color:#1f2937;">
  Secondo paragrafo: scrivi qui ulteriori dettagli o contesto.
</p>
<p style="margin:0 0 8px; font-size:15px; line-height:1.6; color:#1f2937; font-weight:600;">
  Novità di questo aggiornamento:
</p>
<ul style="margin:0 0 16px; padding-left:20px; font-size:15px; line-height:1.6; color:#1f2937;">
  <li style="margin-bottom:6px;">Prima nuova funzionalità</li>
  <li style="margin-bottom:6px;">Seconda nuova funzionalità</li>
  <li style="margin-bottom:6px;">Terza nuova funzionalità</li>
</ul>\
"""


class Newsletter(models.Model):
    """
    Admin-authored one-off email announcement, saved as a draft and sent later (#289).
    Mirrors BroadcastNotification's draft/send lifecycle, but for email instead of push.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    subject = models.CharField(max_length=200)
    body_html = models.TextField(
        default=NEWSLETTER_BODY_PLACEHOLDER,
        help_text=(
            "Raw HTML for the content area only: the header bar and the "
            "unsubscribe link are added automatically by the mail template."
        ),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    recipients_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    failure_count = models.IntegerField(default=0)

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Newsletter"
        verbose_name_plural = "Newsletters"

    def __str__(self):
        return self.subject


class BroadcastNotification(models.Model):
    """
    Admin-created broadcast notifications sent to multiple users
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    title = models.CharField(max_length=100, help_text="Notification title")
    message = models.TextField(help_text="Notification body text")
    url = models.URLField(
        blank=True, help_text="Optional URL when notification is clicked"
    )

    target_schools = models.ManyToManyField(
        School, blank=True, help_text="Leave empty to send to all schools"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    recipients_count = models.IntegerField(
        default=0, help_text="Number of notifications sent"
    )
    success_count = models.IntegerField(default=0)
    failure_count = models.IntegerField(default=0)

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Broadcast Notification"
        verbose_name_plural = "Broadcast Notifications"

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
