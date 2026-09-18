from django.contrib import admin
from django_q.tasks import async_task

from notifications.models import BroadcastNotification, DailyNotification, MonthlyDigest


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
