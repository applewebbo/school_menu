from django.contrib import admin
from django_q.tasks import async_task

from notifications.models import BroadcastNotification


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
            if broadcast.status == BroadcastNotification.Status.SENT:
                self.message_user(
                    request, f"'{broadcast.title}' already sent", level="warning"
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
