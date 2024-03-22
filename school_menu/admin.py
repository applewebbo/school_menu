from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Meal, Settings
from .resources import MealResource

# from .forms import CustomExportForm


@admin.register(Meal)
class MealAdmin(ImportExportModelAdmin):
    resource_classes = [MealResource]


@admin.register(Settings)
class SettingAdmin(admin.ModelAdmin):
    pass
