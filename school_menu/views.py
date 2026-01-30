import logging
from datetime import date, datetime
from typing import Any, cast

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.files.uploadedfile import UploadedFile
from django.db import connection
from django.db.models import Q
from django.forms import modelformset_factory
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from tablib import Dataset
from tablib.exceptions import InvalidDimensions

from contacts.models import MenuReport
from notifications.tasks import _is_school_in_session
from school_menu.cache import (
    get_cached_or_query,
    invalidate_meal_cache,
    invalidate_school_cache,
)
from school_menu.forms import (
    DetailedMealForm,
    SchoolForm,
    SimpleMealForm,
    UploadAnnualMenuForm,
    UploadMenuForm,
)
from school_menu.models import AnnualMeal, DetailedMeal, Meal, School, SimpleMeal
from school_menu.resources import (
    AnnualMenuExportResource,
    AnnualMenuResource,
    DetailedMealExportResource,
    DetailedMealResource,
    SimpleMealExportResource,
    SimpleMealResource,
)
from school_menu.serializers import (
    AnnualMealSerializer,
    DetailedMealSerializer,
    SchoolSerializer,
    SimpleMealSerializer,
)
from school_menu.utils import (
    build_types_menu,
    calculate_week,
    detect_csv_format,
    fill_missing_dates,
    get_adjusted_year,
    get_alt_menu,
    get_current_date,
    get_meals,
    get_meals_for_annual_menu,
    get_notifications_status,
    get_season,
    get_user,
    validate_annual_dataset,
    validate_dataset,
)

logger = logging.getLogger(__name__)


def load_csv_dataset(
    file: UploadedFile, request: HttpRequest
) -> tuple[Dataset | None, HttpResponse | None]:
    """
    Load and parse CSV file with error handling.

    Args:
        file: Uploaded file object
        request: Django request object (for adding error messages)

    Returns:
        tuple: (dataset, error_response) where:
            - dataset is the loaded Dataset object (or None if error)
            - error_response is HttpResponse with error (or None if success)
    """
    dataset = Dataset()
    try:
        # Read and detect CSV format (supports both comma and semicolon delimiters)
        # This allows importing CSVs exported from Numbers, Excel, and other tools
        content = file.read().decode("utf-8")
        delimiter, quotechar = detect_csv_format(content)
        # Load with detected delimiter and quote character
        dataset.load(content, format="csv", delimiter=delimiter, quotechar=quotechar)
        return dataset, None
    except InvalidDimensions as e:
        messages.add_message(
            request,
            messages.ERROR,
            f"Il file CSV non è valido. Impossibile riconoscere il formato (virgola o punto e virgola). Errore: {str(e)}",
        )
        return None, HttpResponse(status=204, headers={"HX-Trigger": "menuUploadError"})
    except ValueError as e:
        # ValueError often indicates quote-related parsing errors
        error_str = str(e).lower()
        if "quote" in error_str or "delimiter" in error_str:
            messages.add_message(
                request,
                messages.ERROR,
                f"Il file CSV contiene virgolette o delimitatori non validi. Verifica che tutte le virgolette siano chiuse correttamente. Errore: {str(e)}",
            )
        else:
            messages.add_message(
                request,
                messages.ERROR,
                f"Il file CSV non è valido. Errore: {str(e)}",
            )
        return None, HttpResponse(status=204, headers={"HX-Trigger": "menuUploadError"})
    except Exception as e:
        messages.add_message(
            request,
            messages.ERROR,
            f"Errore durante la lettura del file CSV. Verifica il formato del file. Errore: {str(e)}",
        )
        return None, HttpResponse(status=204, headers={"HX-Trigger": "menuUploadError"})


def get_school_menu_context(school: School, meal_type: str = "S") -> dict[str, Any]:
    """
    Build common context for school menu display.

    Args:
        school: School object
        meal_type: Meal type code (default "S" for Standard)

    Returns:
        dict: Context dictionary with school menu data
    """
    current_week, adjusted_day = get_current_date()
    bias = school.week_bias
    adjusted_week = calculate_week(current_week, bias)
    season = get_season(school)
    alt_menu = get_alt_menu(school.user)

    if school.annual_menu:
        weekly_meals, meals_for_today = get_meals_for_annual_menu(school)
        types_menu = build_types_menu(weekly_meals, school)
    else:
        weekly_meals, meals_for_today = get_meals(
            school, season, adjusted_week, adjusted_day
        )
        types_menu = build_types_menu(weekly_meals, school, adjusted_week, season)

    # Filter meals by type using list comprehension (weekly_meals is a list, not QuerySet)
    weekly_meals = [m for m in weekly_meals if m.type == meal_type]

    # Get today's meal for the selected type
    try:
        meal_for_today = next(m for m in meals_for_today if m.type == meal_type)
    except StopIteration:
        meal_for_today = None

    year = get_adjusted_year()

    return {
        "school": school,
        "meal": meal_for_today,
        "weekly_meals": weekly_meals,
        "week": adjusted_week,
        "day": adjusted_day,
        "year": year,
        "alt_menu": alt_menu,
        "types_menu": types_menu,
    }


def index(request: HttpRequest) -> HttpResponse:
    """
    Display homepage with authenticated user's school menu.

    Redirects to settings if no school is configured.
    Shows current day menu with weekly overview.
    """
    context = {}
    if request.user.is_authenticated:
        try:
            school = School.objects.get(user=request.user)
        except School.DoesNotExist:
            return redirect(reverse("school_menu:settings", args=[request.user.pk]))
        if not _is_school_in_session(school, datetime.now()):
            context = {
                "not_in_session": True,
                "start_day": school.start_day,
                "start_month": school.start_month,
                "school": school,
            }
            return render(request, "index.html", context)

        context = get_school_menu_context(school, meal_type="S")
    return render(request, "index.html", context)


def school_menu(request: HttpRequest, slug: str, meal_type: str = "S") -> HttpResponse:
    """Return school menu for the given school"""
    school = get_object_or_404(School.objects.select_related("user"), slug=slug)
    pk = request.session.get("anon_notification_pk")
    notifications_status = get_notifications_status(pk, school)
    if not school.is_published:
        return render(request, "school-menu.html", {"not_published": True})
    if not _is_school_in_session(school, datetime.now()):
        context = {
            "not_in_session": True,
            "start_day": school.start_day,
            "start_month": school.start_month,
            "school": school,
        }
        return render(request, "school-menu.html", context)
    context = get_school_menu_context(school, meal_type)
    context["notifications_status"] = notifications_status
    return render(request, "school-menu.html", context)


def get_menu(
    request: HttpRequest, school_id: int, week: int, day: int, meal_type: str
) -> HttpResponse:
    """get menu for the given school, day, week and type"""
    school = get_object_or_404(School.objects.select_related("user"), pk=school_id)
    pk = request.session.get("anon_notification_pk")
    notifications_status = get_notifications_status(pk, school)
    season = get_season(school)
    year = get_adjusted_year()
    alt_menu = get_alt_menu(school.user)
    if school.annual_menu:
        weekly_meals, meals_for_today = get_meals_for_annual_menu(school)
        types_menu = build_types_menu(weekly_meals, school)
    else:
        weekly_meals, meals_for_today = get_meals(school, season, week, day)
        types_menu = build_types_menu(weekly_meals, school, week, season)

    # Filter meals by type using list comprehension (weekly_meals is a list, not QuerySet)
    weekly_meals = [m for m in weekly_meals if m.type == meal_type]

    # Get meal for the specified day and type
    try:
        meal_for_today = next(m for m in weekly_meals if m.day == day)
    except StopIteration:
        meal_for_today = None

    context = {
        "school": school,
        "meal": meal_for_today,
        "weekly_meals": weekly_meals,
        "week": week,
        "day": day,
        "type": meal_type,
        "year": year,
        "alt_menu": alt_menu,
        "types_menu": types_menu,
        "notifications_status": notifications_status,
    }
    return render(request, "partials/_menu.html", context)


@require_http_methods(["GET"])
@cache_page(86400, key_prefix="schools_json")
def get_schools_json_list(request: HttpRequest) -> JsonResponse:
    """Return JSON list of all published schools."""
    schools = School.objects.filter(is_published=True)
    serializer = SchoolSerializer(schools, many=True)
    response = JsonResponse(serializer.data, safe=False)

    # Deprecation headers
    response["X-API-Deprecated"] = "true"
    response["Deprecation"] = 'version="v1"'
    response["Warning"] = '299 - "Endpoint deprecato. Usare /api/v1/schools/"'

    return response


@require_http_methods(["GET"])
@cache_page(86400, key_prefix="json_api")
def get_school_json_menu(request: HttpRequest, slug: str) -> JsonResponse:
    """Return JSON menu data for a specific school."""
    school = get_object_or_404(School, slug=slug)
    current_week, adjusted_day = get_current_date()
    bias = school.week_bias
    adjusted_week = calculate_week(current_week, bias)
    season = get_season(school)
    if school.annual_menu:
        weekly_meals, meals_for_today = get_meals_for_annual_menu(school)
        serializer = AnnualMealSerializer(weekly_meals, many=True)
    else:
        if school.menu_type == School.Types.SIMPLE:
            weekly_meals = list(
                SimpleMeal.objects.filter(
                    school=school, week=adjusted_week, season=season
                ).order_by("day")
            )
            serializer = SimpleMealSerializer(weekly_meals, many=True)
        else:
            weekly_meals = list(
                DetailedMeal.objects.filter(
                    school=school, week=adjusted_week, season=season
                ).order_by("day")
            )
            serializer = DetailedMealSerializer(weekly_meals, many=True)
    meals = list(serializer.data)
    data = {"current_day": adjusted_day, "meals": meals}
    response = JsonResponse(data, safe=False)

    # Deprecation headers
    response["X-API-Deprecated"] = "true"
    response["Deprecation"] = 'version="v1"'
    response["Warning"] = f'299 - "Endpoint deprecato. Usare /api/v1/menu/{slug}/"'

    return response


@login_required
def settings_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Get the settings page"""
    user, alt_menu = get_user(pk)
    active_menu = request.session.get("active_menu", "S")
    menu_label_dict = dict(Meal.Types.choices)
    menu_label = menu_label_dict.get(active_menu)
    report_count = MenuReport.objects.filter(receiver=user).count()
    context = {
        "user": user,
        "alt_menu": alt_menu,
        "menu_label": menu_label,
        "active_menu": active_menu,
        "report_count": report_count,
    }
    return render(request, "settings.html", context)


@login_required
def menu_report_count(request: HttpRequest) -> HttpResponse:
    """Return partial with menu report count for authenticated user."""
    User = get_user_model()
    user = request.user
    assert isinstance(user, User)  # login_required guarantees this
    report_count = MenuReport.objects.filter(receiver=user).count()
    return render(
        request,
        "partials/_settings_account.html#menu_report",
        {"report_count": report_count},
    )


@login_required
def menu_settings_partial(request: HttpRequest, pk: int) -> HttpResponse:
    """ " Get the menu partial of the settings page when reloaded after a change via htmx"""
    user, alt_menu = get_user(pk)
    active_menu = request.GET.get("active_menu", "S")
    request.session["active_menu"] = active_menu
    menu_label_dict = dict(Meal.Types.choices)
    menu_label = menu_label_dict.get(active_menu)
    context = {
        "user": user,
        "alt_menu": alt_menu,
        "menu_label": menu_label,
        "active_menu": active_menu,
    }
    return render(request, "settings.html#menu", context)


@login_required
def school_settings_partial(request: HttpRequest) -> HttpResponse:
    """Return school settings partial for htmx reload."""
    user = request.user
    return render(request, "settings.html#school", {"user": user})


@login_required
def school_view(request: HttpRequest) -> HttpResponse:
    """Display school detail view for authenticated user's school."""
    user = request.user
    school = get_object_or_404(School, user=user)
    context = {"school": school}
    return render(request, "settings.html#school", context)


@login_required
def school_create(request: HttpRequest) -> HttpResponse:
    """Create new school for authenticated user via htmx form."""
    if request.method == "POST":
        form = SchoolForm(request.POST)
        if form.is_valid():
            school = form.save(commit=False)
            school.user = request.user
            school.start_day = form.cleaned_data["start_date"].day
            school.start_month = form.cleaned_data["start_date"].month
            school.end_day = form.cleaned_data["end_date"].day
            school.end_month = form.cleaned_data["end_date"].month
            school.save()

            # Audit log school creation  # pragma: no cover
            request.audit_log(
                action="SCHOOL_CREATE",
                model_name="School",
                object_id=school.id,
                object_repr=str(school),
                changes={"created": True},
            )

            messages.add_message(
                request,
                messages.SUCCESS,
                f"<strong>{school.name}</strong> creata con successo",
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    else:
        current_year = date.today().year
        initial_data = {
            "start_date": date(current_year, 9, 10),
            "end_date": date(current_year + 1, 6, 10),
        }
        form = SchoolForm(initial=initial_data)

    context = {"form": form, "create": True}
    return render(request, "partials/school.html", context)


@login_required
def school_update(request: HttpRequest) -> HttpResponse:
    """Update authenticated user's school via htmx form."""
    user = request.user
    school = get_object_or_404(School, user=user)
    if request.method == "POST":
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            # Track changes before saving  # pragma: no cover
            if form.has_changed():  # pragma: no cover
                changes = {
                    field: {
                        "old": str(form.initial.get(field)),
                        "new": str(form.cleaned_data[field]),
                    }
                    for field in form.changed_data
                }
            else:  # pragma: no cover
                changes = None

            school = form.save(commit=False)
            school.start_day = form.cleaned_data["start_date"].day
            school.start_month = form.cleaned_data["start_date"].month
            school.end_day = form.cleaned_data["end_date"].day
            school.end_month = form.cleaned_data["end_date"].month
            school.save()

            # Audit log school update if there were changes  # pragma: no cover
            if changes:  # pragma: no cover
                request.audit_log(
                    action="SCHOOL_UPDATE",
                    model_name="School",
                    object_id=school.id,
                    object_repr=str(school),
                    changes=changes,
                )

            messages.add_message(
                request,
                messages.SUCCESS,
                f"<strong>{school.name}</strong> aggiornata con successo",
            )
            request.session["active_menu"] = "S"
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    else:
        today = date.today()
        if today.month < school.end_month or (
            today.month == school.end_month and today.day <= school.end_day
        ):
            start_year = today.year - 1
            end_year = today.year
        else:
            start_year = today.year
            end_year = today.year + 1

        initial_data = {
            "start_date": date(start_year, school.start_month, school.start_day),
            "end_date": date(end_year, school.end_month, school.end_day),
        }
        form = SchoolForm(instance=school, initial=initial_data)

    context = {"form": form}
    return render(request, "partials/school.html", context)


def school_list(request: HttpRequest) -> HttpResponse:
    """Return list of all published schools with cached queryset."""
    cache_key = "school_list_queryset"

    def get_schools():
        return list(School.objects.exclude(is_published=False))

    schools = get_cached_or_query(cache_key, get_schools, timeout=86400)
    context = {"schools": schools}
    return TemplateResponse(request, "school-list.html", context)


@login_required
def upload_menu(request: HttpRequest, school_id: int, meal_type: str) -> HttpResponse:
    """Upload weekly menu CSV file for school."""
    school = get_object_or_404(School, pk=school_id)
    menu_type = school.menu_type
    active_menu = meal_type
    if request.method == "POST":
        form = UploadMenuForm(request.POST, request.FILES)
        if form.is_valid():
            file = cast(UploadedFile, request.FILES["file"])
            season = form.cleaned_data["season"]
            if menu_type == School.Types.SIMPLE:
                resource = SimpleMealResource()
            else:
                resource = DetailedMealResource()

            # Load CSV dataset with error handling
            dataset, error_response = load_csv_dataset(file, request)
            if error_response:
                return error_response
            # Validate and filter dataset (removes unnamed and extra columns)
            # This allows CSVs with trailing commas or additional columns to work correctly
            validates, message, filtered_dataset = validate_dataset(dataset, menu_type)
            if not validates:
                context = {
                    "form": form,
                    "school": school,
                    "active_menu": active_menu,
                    "error_message": message,
                }
                return TemplateResponse(request, "upload-menu.html", context)
            result = resource.import_data(
                filtered_dataset,
                dry_run=True,
                school=school,
                season=season,
                type=meal_type,
            )
            if not result.has_errors():  # pragma: no cover
                result = resource.import_data(
                    filtered_dataset,
                    dry_run=False,
                    school=school,
                    season=season,
                    type=meal_type,
                )
                # Explicitly invalidate cache after bulk import
                # (django-import-export may use bulk_create which bypasses save())
                invalidate_meal_cache(school.id)

                # Audit log menu upload  # pragma: no cover
                season_name = "Estivo" if season == 1 else "Invernale"
                meal_type_choices = dict(Meal.Types.choices)
                meal_type_name = meal_type_choices.get(meal_type, meal_type)
                model_name = (
                    "SimpleMeal" if menu_type == School.Types.SIMPLE else "DetailedMeal"
                )
                request.audit_log(
                    action="MENU_UPLOAD",
                    model_name=model_name,
                    object_id=school.id,
                    object_repr=f"{school.name} - {season_name} - {meal_type_name}",
                    changes={"rows_imported": result.totals["new"]},
                )

                messages.add_message(
                    request, messages.SUCCESS, "Menu caricato con successo"
                )
            else:  # pragma: no cover
                logger.error(
                    "Menu import failed with row errors: %s", result.row_errors()
                )
                messages.add_message(
                    request,
                    messages.ERROR,
                    "Qualcosa è andato storto..",
                )
            request.session["active_menu"] = active_menu
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        context = {"form": form, "school": school, "active_menu": active_menu}
        return TemplateResponse(request, "upload-menu.html", context)
    else:
        form = UploadMenuForm()
    context = {"form": form, "school": school, "active_menu": active_menu}
    return TemplateResponse(request, "upload-menu.html", context)


@login_required
def upload_annual_menu(
    request: HttpRequest, school_id: int, meal_type: str
) -> HttpResponse:
    """Upload annual menu CSV file for school."""
    school = get_object_or_404(School, pk=school_id)
    active_menu = meal_type
    if request.method == "POST":
        form = UploadAnnualMenuForm(request.POST, request.FILES)
        if form.is_valid():
            file = cast(UploadedFile, request.FILES["file"])
            resource = AnnualMenuResource()

            # Load CSV dataset with error handling
            dataset, error_response = load_csv_dataset(file, request)
            if error_response:
                return error_response
            # Validate and filter dataset (removes unnamed and extra columns)
            # This allows CSVs with trailing commas or additional columns to work correctly
            validates, message, filtered_dataset = validate_annual_dataset(dataset)
            if not validates:
                context = {
                    "form": form,
                    "school": school,
                    "active_menu": active_menu,
                    "error_message": message,
                }
                return TemplateResponse(request, "upload-menu.html", context)
            result = resource.import_data(
                filtered_dataset, dry_run=True, school=school, type=meal_type
            )
            if not result.has_errors():  # pragma: no cover
                result = resource.import_data(
                    filtered_dataset, dry_run=False, school=school, type=meal_type
                )
                fill_missing_dates(school, meal_type)
                # Explicitly invalidate cache after bulk import and fill_missing_dates
                # (django-import-export may use bulk_create which bypasses save())
                invalidate_meal_cache(school.id)
                messages.add_message(
                    request, messages.SUCCESS, "Menu caricato con successo"
                )
            else:  # pragma: no cover
                logger.error(
                    "Menu import failed with row errors: %s", result.row_errors()
                )
                messages.add_message(
                    request,
                    messages.ERROR,
                    "Qualcosa è andato storto..",
                )
            request.session["active_menu"] = active_menu
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        context = {"form": form, "school": school, "active_menu": active_menu}
        return TemplateResponse(request, "upload-menu.html", context)
    else:
        form = UploadAnnualMenuForm()
    context = {"form": form, "school": school, "active_menu": active_menu}
    return TemplateResponse(request, "upload-menu.html", context)


@login_required
def create_weekly_menu(
    request: HttpRequest, school_id: int, week: int, season: str, meal_type: str
) -> HttpResponse:
    """Create or display weekly menu form for specific week and season."""
    qs = School.objects.all().select_related("user")
    school = get_object_or_404(qs, pk=school_id)
    menu_type = school.menu_type
    # check if the meal for the given week and season already exists
    if menu_type == School.Types.SIMPLE:
        weekly_meals = SimpleMeal.objects.filter(
            week=week, season=season, school=school, type=meal_type
        )
    else:
        weekly_meals = DetailedMeal.objects.filter(  # type: ignore[assignment]
            week=week, season=season, school=school, type=meal_type
        )
    # if the meals don't exist, create them with blank values
    if not weekly_meals.exists():
        if menu_type == School.Types.SIMPLE:
            for day in range(1, 6):
                SimpleMeal.objects.create(
                    week=week, day=day, season=season, school=school, type=meal_type
                )
        else:
            for day in range(1, 6):
                DetailedMeal.objects.create(
                    week=week, day=day, season=season, school=school, type=meal_type
                )
    # create a formset for editing the meals for the week
    if menu_type == School.Types.SIMPLE:
        MealFormSet = modelformset_factory(
            SimpleMeal,
            form=SimpleMealForm,
            extra=0,
            fields=("menu", "morning_snack", "afternoon_snack"),
        )
        meals = SimpleMeal.objects.filter(
            week=week, season=season, school=school, type=meal_type
        )
    else:
        MealFormSet = modelformset_factory(
            DetailedMeal,  # type: ignore[arg-type]
            form=DetailedMealForm,  # type: ignore[arg-type]
            extra=0,
            fields=("first_course", "second_course", "side_dish", "fruit", "snack"),
        )
        meals = DetailedMeal.objects.filter(  # type: ignore[assignment]
            week=week, season=season, school=school, type=meal_type
        )
    formset = MealFormSet(request.POST or None, queryset=meals)
    if request.method == "POST":
        if formset.is_valid():
            formset.save()
            messages.add_message(
                request, messages.SUCCESS, "Menu settimanale salvato con successo"
            )
            return redirect("school_menu:settings", pk=school.user.pk)
        context = {"formset": formset, "school": school, "week": week, "season": season}
        return render(request, "create-weekly-menu.html", context)
    else:
        formset = MealFormSet(queryset=meals)
    context = {"formset": formset, "school": school, "week": week, "season": season}
    return render(request, "create-weekly-menu.html", context)


@cache_page(3600, key_prefix="search")
def search_schools(request: HttpRequest) -> HttpResponse:
    """get the schools based on the search input via htmx"""
    context = {}
    query = request.GET.get("q")
    schools = School.objects.exclude(is_published=False).filter(
        Q(name__icontains=query) | Q(city__icontains=query)
    )
    referrer = request.headers.get("referer", None)
    # get a different partial if the search comes from the index page
    if referrer == request.build_absolute_uri(
        reverse("school_menu:index")
    ):  # pragma: no cover
        template = "index.html#search-result"
    else:
        template = "school-list.html#search-result"
    # hidden results if the input is empty in the index page
    if not query:
        context["hidden"] = True
    # get a message if no schools match the search query
    if not schools:
        context["no_schools"] = True
    else:
        context["schools"] = schools  # type: ignore[assignment]
    return TemplateResponse(request, template, context)


def export_modal_view(
    request: HttpRequest, school_id: int, meal_type: str
) -> HttpResponse:
    """Display export modal with available seasons for school menu."""
    school = get_object_or_404(School, pk=school_id)
    if school.annual_menu:
        model = AnnualMeal
        summer_meals = None
        winter_meals = None
        annual_meals = model.objects.filter(school=school, type=meal_type).exists()
    else:
        annual_meals = None
        if school.menu_type == School.Types.SIMPLE:
            model = SimpleMeal  # type: ignore[assignment]
        else:
            model = DetailedMeal  # type: ignore[assignment]
        summer_meals = model.objects.filter(
            school=school, season=School.Seasons.PRIMAVERILE, type=meal_type
        ).exists()
        winter_meals = model.objects.filter(
            school=school, season=School.Seasons.INVERNALE, type=meal_type
        ).exists()
    context = {
        "school": school,
        "summer_meals": summer_meals,
        "winter_meals": winter_meals,
        "annual_meals": annual_meals,
        "active_menu": meal_type,
    }
    return render(request, "export-menu.html", context)


@login_required
def export_menu(
    request: HttpRequest, school_id: int, season: str, meal_type: str
) -> HttpResponse:
    """Export school menu as CSV file for specified season and meal type."""
    school = get_object_or_404(School, pk=school_id)
    if school.annual_menu:
        model = AnnualMeal
        resource = AnnualMenuExportResource()
    elif school.menu_type == School.Types.SIMPLE:
        model = SimpleMeal  # type: ignore[assignment]
        resource = SimpleMealExportResource()
    else:
        model = DetailedMeal  # type: ignore[assignment]
        resource = DetailedMealExportResource()

    meals = model.objects.filter(school=school, season=season, type=meal_type)
    data = resource.export(meals)

    response = HttpResponse(data.csv, content_type="text/csv")
    return response


@require_http_methods(["GET"])
def health_check(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint for monitoring service status.

    Tests connectivity to:
    - Redis cache backend
    - PostgreSQL/SQLite database

    Returns:
        JSON response with service status and details

    Example responses:
        Healthy: {"status": "healthy", "services": {"cache": "ok", "database": "ok"}}
        Degraded: {"status": "degraded", "services": {"cache": "error", "database": "ok"}}
        Unhealthy: {"status": "unhealthy", "services": {"cache": "error", "database": "error"}}
    """
    services = {}
    overall_status = "healthy"

    # Test Redis cache connectivity
    try:
        test_key = "_health_check_test"
        test_value = "ok"
        cache.set(test_key, test_value, timeout=10)
        cached_value = cache.get(test_key)

        if cached_value == test_value:
            services["cache"] = "ok"
            cache.delete(test_key)
        else:
            services["cache"] = "error"
            overall_status = "degraded"
    except Exception as e:
        services["cache"] = f"error: {str(e)}"
        overall_status = "degraded"

    # Test database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        services["database"] = "ok"
    except Exception as e:
        services["database"] = f"error: {str(e)}"
        overall_status = "unhealthy"

    # Overall status logic:
    # - healthy: all services ok
    # - degraded: cache down but database ok
    # - unhealthy: database down (critical)
    response_data = {
        "status": overall_status,
        "services": services,
    }

    # Return 200 for healthy/degraded, 503 for unhealthy
    status_code = 200 if overall_status != "unhealthy" else 503

    return JsonResponse(response_data, status=status_code)


@login_required
def school_delete(request: HttpRequest) -> HttpResponse:
    """Delete the school associated with the current user"""
    user = request.user
    school = get_object_or_404(School, user=user)
    if request.method == "POST":
        school_id = school.id
        school_slug = school.slug
        school_name = school.name

        # Audit log school deletion before delete  # pragma: no cover
        request.audit_log(
            action="SCHOOL_DELETE",
            model_name="School",
            object_id=school_id,
            object_repr=str(school),
            changes={"deleted": True},
        )

        school.delete()
        # Invalidate all school-related caches
        invalidate_school_cache(school_id, school_slug)
        messages.add_message(
            request,
            messages.SUCCESS,
            f"<strong>{school_name}</strong> eliminata con successo",
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    return render(request, "school_menu/school_delete.html", context={"school": school})
