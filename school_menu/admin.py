from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from import_export.admin import ImportExportModelAdmin
from tablib import Dataset

from .models import (
    AnnualMeal,
    AuditLog,
    DetailedMeal,
    MenuImportDraft,
    MenuImportQuota,
    School,
    SimpleMeal,
)
from .resources import DetailedMealResource, SimpleMealResource
from .utils import validate_dataset


class CsvImportForm(forms.Form):
    season = forms.ChoiceField(
        choices=[
            (SimpleMeal.Seasons.ESTIVO, "Estivo"),
            (SimpleMeal.Seasons.INVERNALE, "Invernale"),
        ],
        label="Stagione",
    )
    meal_type = forms.ChoiceField(choices=[], label="Tipo menu")
    csv_file = forms.FileField(label="File CSV")
    overwrite = forms.BooleanField(required=False, label="Sovrascrivi dati esistenti")

    def __init__(self, *args, school, **kwargs):
        super().__init__(*args, **kwargs)
        type_choices = [("S", "Standard")]
        if school.no_gluten:
            type_choices.append((DetailedMeal.Types.GLUTEN_FREE, "Senza glutine"))
        if school.no_lactose:
            type_choices.append((DetailedMeal.Types.LACTOSE_FREE, "Senza lattosio"))
        if school.vegetarian:
            type_choices.append((DetailedMeal.Types.VEGETARIAN, "Vegetariano"))
        if school.special:
            type_choices.append((DetailedMeal.Types.SPECIAL, "Speciale"))
        self.fields["meal_type"].choices = type_choices


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
    actions = ["import_csv_menu"]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:school_id>/import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="school_menu_school_import_csv",
            ),
        ]
        return custom + urls

    @admin.action(description="Importa CSV menu")
    def import_csv_menu(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request, "Seleziona esattamente una scuola.", level=messages.WARNING
            )
            return
        school = queryset.first()
        return redirect(f"{school.pk}/import-csv/")

    def import_csv_view(self, request, school_id):
        school = get_object_or_404(School, pk=school_id)
        errors = []

        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES, school=school)
            if form.is_valid():
                season = int(form.cleaned_data["season"])
                meal_type = form.cleaned_data["meal_type"]
                overwrite = form.cleaned_data["overwrite"]
                csv_file = request.FILES["csv_file"]

                content = csv_file.read().decode("utf-8")
                dataset = Dataset()
                dataset.load(content, format="csv")

                validates, message, filtered_dataset = validate_dataset(
                    dataset, school.menu_type
                )
                if not validates:
                    errors.append(message)
                else:
                    if school.menu_type == School.Types.SIMPLE:
                        ModelClass = SimpleMeal
                        resource = SimpleMealResource()
                    else:
                        ModelClass = DetailedMeal
                        resource = DetailedMealResource()

                    result = resource.import_data(
                        filtered_dataset,
                        dry_run=True,
                        school=school,
                        season=season,
                        type=meal_type,
                    )
                    if result.has_errors():
                        errors.append("Errori nel file CSV. Importazione annullata.")
                    else:
                        if overwrite:
                            ModelClass.objects.filter(
                                school=school, season=season, type=meal_type
                            ).delete()
                        resource.import_data(
                            filtered_dataset,
                            dry_run=False,
                            school=school,
                            season=season,
                            type=meal_type,
                        )
                        self.message_user(
                            request,
                            f"Importati {len(filtered_dataset)} record per {school.name}.",
                            level=messages.SUCCESS,
                        )
                        return redirect("..")
        else:
            form = CsvImportForm(school=school)

        context = {
            **self.admin_site.each_context(request),
            "school": school,
            "form": form,
            "errors": errors,
            "opts": self.model._meta,
            "title": f"Importa CSV — {school.name}",
        }
        return render(request, "admin/school_menu/import_csv_action.html", context)


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


@admin.register(MenuImportDraft)
class MenuImportDraftAdmin(admin.ModelAdmin):
    list_display = ["__str__", "user", "kind", "status", "created_at"]
    list_filter = ["status", "kind", "created_at"]
    search_fields = ["school__name", "user__email", "source_filename"]
    readonly_fields = ["created_at", "updated_at", "completed_at", "task_id", "usage"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        """Drafts are only ever created by the import flow."""
        return False


@admin.register(MenuImportQuota)
class MenuImportQuotaAdmin(admin.ModelAdmin):
    list_display = ["__str__", "user", "date", "count"]
    list_filter = ["date"]
    search_fields = ["user__email"]
