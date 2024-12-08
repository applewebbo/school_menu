from django.contrib import admin

from contacts.models import MenuReport


@admin.register(MenuReport)
class MenuReportAdmin(admin.ModelAdmin):
    list_display = ["name", "receiver", "created_at"]
    list_filter = ["receiver", "created_at"]
