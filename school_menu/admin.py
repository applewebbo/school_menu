from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import AnnualMeal, AuditLog, DetailedMeal, School, SimpleMeal
from .resources import DetailedMealResource, SimpleMealResource

# from .forms import CustomExportForm


@admin.register(DetailedMeal)
class DetailedMealAdmin(ImportExportModelAdmin):
    resource_classes = [DetailedMealResource]
    list_display = ["__str__", "school"]
    list_filter = ["school", "type"]


@admin.register(SimpleMeal)
class SimpleMealAdmin(ImportExportModelAdmin):
    resource_classes = [SimpleMealResource]
    list_display = ["__str__", "school"]
    list_filter = ["school", "type"]


@admin.register(AnnualMeal)
class AnnualMealAdmin(admin.ModelAdmin):
    list_display = ["__str__", "date", "type"]
    list_filter = ["type"]


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "city",
                    "user",
                    "is_published",
                )
            },
        ),
        (
            "Configurazione Menu",
            {
                "fields": (
                    "menu_type",
                    "season_choice",
                    "week_bias",
                    "annual_menu",
                    "no_gluten",
                    "no_lactose",
                    "vegetarian",
                    "special",
                )
            },
        ),
        (
            "Periodo Scolastico (per le notifiche)",
            {
                "fields": (
                    "start_month",
                    "start_day",
                    "end_month",
                    "end_day",
                )
            },
        ),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "timestamp",
        "user",
        "action",
        "model_name",
        "object_repr",
        "ip_address",
    ]
    list_filter = ["action", "model_name", "timestamp"]
    search_fields = ["object_repr", "user__email", "ip_address"]
    readonly_fields = [
        "timestamp",
        "user",
        "action",
        "model_name",
        "object_id",
        "object_repr",
        "changes",
        "ip_address",
        "user_agent",
    ]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
