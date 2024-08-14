from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin

from .models import DetailedMeal, School, SimpleMeal
from .resources import DetailedMealResource, SimpleMealResource

# from .forms import CustomExportForm


@admin.register(DetailedMeal)
class DetailedMealAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_classes = [DetailedMealResource]
    list_display = ["__str__", "school"]
    list_filter = ["school"]


@admin.register(SimpleMeal)
class SimpleMealAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_classes = [SimpleMealResource]
    list_display = ["__str__", "school"]
    list_filter = ["school"]


@admin.register(School)
class SchoolAdmin(ModelAdmin):
    pass
