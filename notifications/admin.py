from django import forms
from django.conf import settings
from django.contrib import admin
from django.urls import reverse
from django_q.tasks import async_task

from notifications.models import (
    BroadcastNotification,
    DailyNotification,
    MonthlyDigest,
    Newsletter,
)
from notifications.tasks import _build_newsletter_email


@admin.register(DailyNotification)
class DailyNotificationAdmin(admin.ModelAdmin):
    """Read-only audit log of notification runs (#268)."""

    list_display = [
        "notification_time",
        "created_at",
        "sent_count",
        "failed_count",
        "pruned_count",
    ]
    list_filter = ["notification_time", "created_at"]
    readonly_fields = [field.name for field in DailyNotification._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MonthlyDigest)
class MonthlyDigestAdmin(admin.ModelAdmin):
    """Read-only audit log of monthly admin digest runs (#280)."""

    list_display = [
        "period_start",
        "period_end",
        "new_schools",
        "menu_reports",
        "report_errors",
        "feedback_sent",
        "new_subscriptions",
        "created_at",
    ]
    list_filter = ["period_start"]
    readonly_fields = [field.name for field in MonthlyDigest._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class NewsletterAdminForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = "__all__"
        widgets = {
            # A plain textarea for raw HTML (#289): no WYSIWYG dependency, matching
            # the project's minimalism convention since only the site owner uses this.
            "body_html": forms.Textarea(attrs={"rows": 20, "cols": 100}),
        }


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    form = NewsletterAdminForm
    list_display = [
        "subject",
        "created_at",
        "sent_at",
        "status",
        "recipients_count",
        "success_count",
        "failure_count",
    ]
    list_filter = ["status", "created_at", "sent_at"]
    readonly_fields = [
        "created_by",
        "created_at",
        "sent_at",
        "recipients_count",
        "success_count",
        "failure_count",
        "status",
    ]

    fieldsets = (
        ("Newsletter Content", {"fields": ("subject", "body_html")}),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "created_by",
                    "created_at",
                    "sent_at",
                    "recipients_count",
                    "success_count",
                    "failure_count",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.status = Newsletter.Status.DRAFT
        super().save_model(request, obj, form, change)

    actions = ["send_newsletter", "send_test_to_self"]

    @admin.action(description="Send test to my email")
    def send_test_to_self(self, request, queryset):
        """
        Preview to the logged-in admin's own address (#289): same placeholder
        unsubscribe link as the --test CLI flag, and it never touches the
        newsletter's status or counts, so it can be re-run freely while drafting.
        """
        unsubscribe_url = (
            f"{settings.SITE_URL}"
            f"{reverse('users:newsletter_unsubscribe', args=['anteprima'])}"
        )
        for newsletter in queryset:
            email = _build_newsletter_email(
                newsletter.subject,
                newsletter.body_html,
                request.user.email,
                unsubscribe_url,
            )
            email.send()

        self.message_user(request, f"Test email sent to {request.user.email}")

    @admin.action(description="Send selected newsletters")
    def send_newsletter(self, request, queryset):
        sent_count = 0
        for newsletter in queryset:
            if newsletter.status in [Newsletter.Status.SENT, Newsletter.Status.SENDING]:
                self.message_user(
                    request,
                    f"'{newsletter.subject}' already sent or currently sending",
                    level="warning",
                )
                continue

            async_task("notifications.tasks.send_newsletter", newsletter.pk)

            newsletter.status = Newsletter.Status.SENDING
            newsletter.save()
            sent_count += 1

        if sent_count > 0:
            self.message_user(request, f"Sending {sent_count} newsletter(s)...")


@admin.register(BroadcastNotification)
class BroadcastNotificationAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "created_at",
        "sent_at",
        "status",
        "recipients_count",
        "success_count",
        "failure_count",
    ]
    list_filter = ["status", "created_at", "sent_at"]
    filter_horizontal = ["target_schools"]
    readonly_fields = [
        "created_by",
        "created_at",
        "sent_at",
        "recipients_count",
        "success_count",
        "failure_count",
        "status",
    ]

    fieldsets = (
        ("Notification Content", {"fields": ("title", "message", "url")}),
        (
            "Recipients",
            {
                "fields": ("target_schools",),
                "description": "Leave empty to send to all subscribed users",
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "created_by",
                    "created_at",
                    "sent_at",
                    "recipients_count",
                    "success_count",
                    "failure_count",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """
        Override save to set created_by
        """
        if not change:
            obj.created_by = request.user
            obj.status = BroadcastNotification.Status.DRAFT
        super().save_model(request, obj, form, change)

    actions = ["send_broadcast"]

    @admin.action(description="Send selected broadcasts")
    def send_broadcast(self, request, queryset):
        """
        Admin action to send broadcast notifications
        """
        sent_count = 0
        for broadcast in queryset:
            if broadcast.status in [
                BroadcastNotification.Status.SENT,
                BroadcastNotification.Status.SENDING,
            ]:
                self.message_user(
                    request,
                    f"'{broadcast.title}' already sent or currently sending",
                    level="warning",
                )
                continue

            # Trigger async task to send
            async_task("notifications.tasks.send_broadcast_notification", broadcast.pk)

            broadcast.status = BroadcastNotification.Status.SENDING
            broadcast.save()
            sent_count += 1

        if sent_count > 0:
            self.message_user(
                request, f"Sending {sent_count} broadcast(s) to subscribed users..."
            )
