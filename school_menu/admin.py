from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Meal, Settings
from .resources import MealResource

# from .forms import CustomExportForm


@admin.register(Meal)
class MealAdmin(ImportExportModelAdmin):
    resource_classes = [MealResource]


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
