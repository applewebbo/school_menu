from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Meal, School, Settings
from .resources import MealResource

# from .forms import CustomExportForm


@admin.register(Meal)
class MealAdmin(ImportExportModelAdmin):
    resource_classes = [MealResource]
    list_display = ["__str__", "school"]
    list_filter = ["school"]


@admin.register(Settings)
class SettingAdmin(admin.ModelAdmin):
    pass


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    pass
