from django.contrib import admin
from unfold.admin import ModelAdmin

from contacts.models import MenuReport


@admin.register(MenuReport)
class MenuReportAdmin(ModelAdmin):
    list_display = ["name", "receiver", "created_at"]
    list_filter = ["receiver", "created_at"]
