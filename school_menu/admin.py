from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import DetailedMeal, School
from .resources import DetailedMealResource

# from .forms import CustomExportForm


@admin.register(DetailedMeal)
class MealAdmin(ImportExportModelAdmin):
    resource_classes = [DetailedMealResource]
    list_display = ["__str__", "school"]
    list_filter = ["school"]


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    pass
