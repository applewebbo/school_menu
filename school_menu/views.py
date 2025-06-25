from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import modelformset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import HttpResponse, TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from tablib import Dataset

from contacts.models import MenuReport
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
    fill_missing_dates,
    get_adjusted_year,
    get_alt_menu,
    get_current_date,
    get_meals,
    get_meals_for_annual_menu,
    get_season,
    get_user,
    validate_annual_dataset,
    validate_dataset,
)


def index(request):
    context = {}
    if request.user.is_authenticated:
        try:
            school = School.objects.get(user=request.user)
        except School.DoesNotExist:
            school = None
            return redirect(reverse("school_menu:settings", args=[request.user.pk]))
        current_week, adjusted_day = get_current_date()
        bias = school.week_bias
        adjusted_week = calculate_week(current_week, bias)
        season = get_season(school)
        alt_menu = get_alt_menu(school.user)
        meal_type = "S"
        if school.annual_menu:
            weekly_meals, meals_for_today = get_meals_for_annual_menu(school)
        else:
            weekly_meals, meals_for_today = get_meals(
                school, season, adjusted_week, adjusted_day
            )
        types_menu = build_types_menu(weekly_meals, school)
        weekly_meals = weekly_meals.filter(type=meal_type)
        try:
            meal_for_today = meals_for_today.get(type=meal_type)
        except (
            SimpleMeal.DoesNotExist,
            DetailedMeal.DoesNotExist,
            AnnualMeal.DoesNotExist,
        ):
            meal_for_today = None

        context = {
            "school": school,
            "meal": meal_for_today,
            "weekly_meals": weekly_meals,
            "week": adjusted_week,
            "day": adjusted_day,
            "year": datetime.now().year,
            "alt_menu": alt_menu,
            "types_menu": types_menu,
        }
    return render(request, "index.html", context)


def school_menu(request, slug, meal_type="S"):
    """Return school menu for the given school"""
    school = get_object_or_404(School, slug=slug)
    if not school.is_published:
        return render(request, "school-menu.html", {"not_published": True})
    current_week, adjusted_day = get_current_date()
    bias = school.week_bias
    adjusted_week = calculate_week(current_week, bias)
    season = get_season(school)
    alt_menu = get_alt_menu(school.user)
    if school.annual_menu:
        weekly_meals, meals_for_today = get_meals_for_annual_menu(school)
    else:
        weekly_meals, meals_for_today = get_meals(
            school, season, adjusted_week, adjusted_day
        )
    year = get_adjusted_year()
    types_menu = build_types_menu(weekly_meals, school)
    weekly_meals = weekly_meals.filter(type=meal_type)
    try:
        meal_for_today = meals_for_today.get(type=meal_type)
    except (
        SimpleMeal.DoesNotExist,
        DetailedMeal.DoesNotExist,
        AnnualMeal.DoesNotExist,
    ):
        meal_for_today = None

    context = {
        "school": school,
        "meal": meal_for_today,
        "weekly_meals": weekly_meals,
        "week": adjusted_week,
        "day": adjusted_day,
        "year": year,
        "alt_menu": alt_menu,
        "types_menu": types_menu,
    }
    return render(request, "school-menu.html", context)


def get_menu(request, school_id, week, day, meal_type):
    """get menu for the given school, day, week and type"""
    school = get_object_or_404(School, pk=school_id)
    season = get_season(school)
    year = get_adjusted_year()
    alt_menu = get_alt_menu(school.user)
    if school.annual_menu:
        weekly_meals, meal_for_today = get_meals_for_annual_menu(school)
    else:
        weekly_meals, meal_for_today = get_meals(school, season, week, day)
    types_menu = build_types_menu(weekly_meals, school)
    weekly_meals = weekly_meals.filter(type=meal_type)
    try:
        meal_for_today = weekly_meals.get(day=day)
    except (
        SimpleMeal.DoesNotExist,
        DetailedMeal.DoesNotExist,
        AnnualMeal.DoesNotExist,
    ):
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
    }
    return render(request, "partials/_menu.html", context)


@require_http_methods(["GET"])
def get_schools_json_list(request):
    schools = School.objects.filter(is_published=True)
    serializer = SchoolSerializer(schools, many=True)
    return JsonResponse(serializer.data, safe=False)


@require_http_methods(["GET"])
def get_school_json_menu(request, slug):
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
            weekly_meals = SimpleMeal.objects.filter(
                school=school, week=adjusted_week, season=season
            ).order_by("day")
            serializer = SimpleMealSerializer(weekly_meals, many=True)
        else:
            weekly_meals = DetailedMeal.objects.filter(
                school=school, week=adjusted_week, season=season
            ).order_by("day")
            serializer = DetailedMealSerializer(weekly_meals, many=True)
    meals = list(serializer.data)
    data = {"current_day": adjusted_day, "meals": meals}
    return JsonResponse(data, safe=False)


@login_required
def settings_view(request, pk):
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
def menu_report_count(request):
    user = request.user
    report_count = MenuReport.objects.filter(receiver=user).count()
    return render(
        request,
        "partials/_settings_account.html#menu_report",
        {"report_count": report_count},
    )


@login_required
def menu_settings_partial(request, pk):
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
def school_view(request):
    user = request.user
    school = get_object_or_404(School, user=user)
    context = {"school": school}
    return render(request, "settings.html#school", context)


@login_required
def school_create(request):
    form = SchoolForm(request.POST or None)
    if form.is_valid():
        school = form.save(commit=False)
        school.user = request.user
        school.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            f"<strong>{school.name}</strong> creata con successo",
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    context = {"form": form, "create": True}
    return render(request, "partials/school.html", context)


@login_required
def school_update(request):
    user = request.user
    school = get_object_or_404(School, user=user)
    form = SchoolForm(request.POST or None, instance=school)
    get_alt_menu(user)
    if form.is_valid():
        school = form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            f"<strong>{school.name}</strong> aggiornata con successo",
        )
        request.session["active_menu"] = "S"
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    context = {"form": form}
    return render(request, "partials/school.html", context)


def school_list(request):
    schools = School.objects.exclude(is_published=False)
    context = {"schools": schools}
    return TemplateResponse(request, "school-list.html", context)


@login_required
def upload_menu(request, school_id, meal_type):
    school = get_object_or_404(School, pk=school_id)
    menu_type = school.menu_type
    active_menu = meal_type
    if request.method == "POST":
        form = UploadMenuForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            season = form.cleaned_data["season"]
            if menu_type == School.Types.SIMPLE:
                resource = SimpleMealResource()
            else:
                resource = DetailedMealResource()
            dataset = Dataset()
            dataset.load(file.read().decode(), format="csv")
            validates, message = validate_dataset(dataset, menu_type)
            result = resource.import_data(
                dataset, dry_run=True, school=school, season=season, type=meal_type
            )
            if not validates:
                messages.add_message(request, messages.ERROR, message)
                return HttpResponse(status=204, headers={"HX-Trigger": "menuModified"})
            if not result.has_errors():  # pragma: no cover
                result = resource.import_data(
                    dataset, dry_run=False, school=school, season=season, type=meal_type
                )
                messages.add_message(
                    request, messages.SUCCESS, "Menu caricato con successo"
                )
            else:  # pragma: no cover
                print(result.row_errors())
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
def upload_annual_menu(request, school_id, meal_type):
    school = get_object_or_404(School, pk=school_id)
    active_menu = meal_type
    if request.method == "POST":
        form = UploadAnnualMenuForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            resource = AnnualMenuResource()
            dataset = Dataset()
            dataset.load(file.read().decode(), format="csv")
            validates, message = validate_annual_dataset(dataset)
            result = resource.import_data(
                dataset, dry_run=True, school=school, type=meal_type
            )
            if not validates:
                messages.add_message(request, messages.ERROR, message)
                return HttpResponse(status=204, headers={"HX-Trigger": "menuModified"})
            if not result.has_errors():  # pragma: no cover
                result = resource.import_data(
                    dataset, dry_run=False, school=school, type=meal_type
                )
                fill_missing_dates(school, meal_type)
                messages.add_message(
                    request, messages.SUCCESS, "Menu caricato con successo"
                )
            else:  # pragma: no cover
                print(result.row_errors())
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
def create_weekly_menu(request, school_id, week, season, meal_type):
    qs = School.objects.all().select_related("user")
    school = get_object_or_404(qs, pk=school_id)
    menu_type = school.menu_type
    # check if the meal for the given week and season already exists
    if menu_type == School.Types.SIMPLE:
        weekly_meals = SimpleMeal.objects.filter(
            week=week, season=season, school=school, type=meal_type
        )
    else:
        weekly_meals = DetailedMeal.objects.filter(
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
            DetailedMeal,
            form=DetailedMealForm,
            extra=0,
            fields=("first_course", "second_course", "side_dish", "fruit", "snack"),
        )
        meals = DetailedMeal.objects.filter(
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


def search_schools(request):
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
        context["schools"] = schools
    return TemplateResponse(request, template, context)


def export_modal_view(request, school_id, meal_type):
    school = get_object_or_404(School, pk=school_id)
    if school.annual_menu:
        model = AnnualMeal
        summer_meals = None
        winter_meals = None
        annual_meals = model.objects.filter(school=school, type=meal_type).exists()
    else:
        annual_meals = None
        if school.menu_type == School.Types.SIMPLE:
            model = SimpleMeal
        else:
            model = DetailedMeal
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
def export_menu(request, school_id, season, meal_type):
    school = get_object_or_404(School, pk=school_id)
    if school.annual_menu:
        model = AnnualMeal
        resource = AnnualMenuExportResource()
    elif school.menu_type == School.Types.SIMPLE:
        model = SimpleMeal
        resource = SimpleMealExportResource()
    else:
        model = DetailedMeal
        resource = DetailedMealExportResource()

    meals = model.objects.filter(school=school, season=season, type=meal_type)
    data = resource.export(meals)

    response = HttpResponse(data.csv, content_type="text/csv")
    return response
