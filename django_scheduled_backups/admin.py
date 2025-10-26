"""Admin interface for backup history."""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import BackupRun
from .tasks import scheduled_database_backup, scheduled_media_backup


@admin.register(BackupRun)
class BackupRunAdmin(admin.ModelAdmin):
    """Admin interface for BackupRun model with filters and actions."""

    list_display = [
        "id",
        "backup_type",
        "status_badge",
        "started_at",
        "completed_at",
        "duration_display",
    ]
    list_filter = [
        "status",
        "backup_type",
        "started_at",
    ]
    search_fields = [
        "error_message",
    ]
    readonly_fields = [
        "backup_type",
        "status",
        "started_at",
        "completed_at",
        "duration_seconds",
        "error_message",
    ]
    date_hierarchy = "started_at"
    ordering = ["-started_at"]

    # Disable add and change permissions
    def has_add_permission(self, request):
        """Disable manual creation of backup runs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing of backup runs."""
        return False

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            "running": "orange",
            "success": "green",
            "failed": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description=_("Duration"))
    def duration_display(self, obj):
        """Display duration in human-readable format."""
        if obj.duration_seconds is None:
            return "-"
        minutes, seconds = divmod(obj.duration_seconds, 60)
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    actions = ["trigger_database_backup", "trigger_media_backup", "cleanup_old_records"]

    @admin.action(description=_("Trigger database backup now"))
    def trigger_database_backup(self, request, queryset):
        """Manually trigger a database backup."""
        try:
            result = scheduled_database_backup()
            self.message_user(
                request, f"Database backup triggered successfully: {result}"
            )
        except Exception as e:
            self.message_user(
                request, f"Database backup failed: {str(e)}", level="error"
            )

    @admin.action(description=_("Trigger media backup now"))
    def trigger_media_backup(self, request, queryset):
        """Manually trigger a media backup."""
        try:
            result = scheduled_media_backup()
            self.message_user(request, f"Media backup triggered successfully: {result}")
        except Exception as e:
            self.message_user(request, f"Media backup failed: {str(e)}", level="error")

    @admin.action(description=_("Cleanup old backup records"))
    def cleanup_old_records(self, request, queryset):
        """Delete old backup records based on retention policy."""
        from datetime import timedelta

        from django.utils.timezone import now

        from .conf import get_setting

        retention_days = get_setting("HISTORY_RETENTION_DAYS", 90)
        cutoff_date = now() - timedelta(days=retention_days)

        deleted_count = BackupRun.objects.filter(started_at__lt=cutoff_date).delete()[0]

        self.message_user(
            request,
            f"Deleted {deleted_count} backup records older than {retention_days} days",
        )
