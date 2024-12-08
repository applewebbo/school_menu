from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import DetailedMeal, School, SimpleMeal
from .resources import DetailedMealResource, SimpleMealResource

# from .forms import CustomExportForm


@admin.register(DetailedMeal)
class DetailedMealAdmin(ImportExportModelAdmin):
    resource_classes = [DetailedMealResource]
    list_display = ["__str__", "school"]
    list_filter = ["school"]


@admin.register(SimpleMeal)
class SimpleMealAdmin(ImportExportModelAdmin):
    resource_classes = [SimpleMealResource]
    list_display = ["__str__", "school"]
    list_filter = ["school"]


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    pass
