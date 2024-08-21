from django.contrib import admin

# from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(ModelAdmin):
    list_display = ["name", "email", "created_at"]
    list_filter = ["email"]
