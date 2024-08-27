import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import HttpResponse, TemplateResponse
from django.urls import reverse

from school_menu.forms import (
    DetailedMealForm,
    SchoolForm,
    SimpleMealForm,
    UploadMenuForm,
)
from school_menu.models import DetailedMeal, School, SimpleMeal
from school_menu.resources import DetailedMealResource, SimpleMealResource
from school_menu.utils import (
    calculate_week,
    get_current_date,
    get_season,
    get_user,
    import_menu,
)


def index(request):
    context = {}
    if request.user.is_authenticated:
        school = School.objects.filter(user=request.user).first()
        if not school:
            return redirect(reverse("school_menu:settings", args=[request.user.pk]))
        current_week, adjusted_day = get_current_date()
        bias = school.week_bias
        adjusted_week = calculate_week(current_week, bias)
        season = get_season(school)
        if school.menu_type == School.Types.SIMPLE:
            weekly_meals = SimpleMeal.objects.filter(
                school=school, week=adjusted_week, season=season
            ).order_by("day")
            meal_for_today = weekly_meals.filter(day=adjusted_day).first()
        else:
            weekly_meals = DetailedMeal.objects.filter(
                school=school, week=adjusted_week, season=season
            ).order_by("day")
            meal_for_today = weekly_meals.filter(day=adjusted_day).first()
        context = {
            "school": school,
            "meal": meal_for_today,
            "weekly_meals": weekly_meals,
            "week": adjusted_week,
            "day": adjusted_day,
        }
    return render(request, "index.html", context)


def school_menu(request, slug):
    """Return school menu for the given school"""
    school = get_object_or_404(School, slug=slug)
    if not school.is_published:
        return render(request, "school-menu.html", {"not_published": True})
    current_week, adjusted_day = get_current_date()
    bias = school.week_bias
    adjusted_week = calculate_week(current_week, bias)
    season = get_season(school)
    if school.menu_type == School.Types.SIMPLE:
        weekly_meals = SimpleMeal.objects.filter(
            school=school, week=adjusted_week, season=season
        ).order_by("day")
        meal_for_today = weekly_meals.filter(day=adjusted_day).first()
    else:
        weekly_meals = DetailedMeal.objects.filter(
            school=school, week=adjusted_week, season=season
        ).order_by("day")
        meal_for_today = weekly_meals.filter(day=adjusted_day).first()
    context = {
        "school": school,
        "meal": meal_for_today,
        "weekly_meals": weekly_meals,
        "week": adjusted_week,
        "day": adjusted_day,
    }
    return render(request, "school-menu.html", context)


def get_menu(request, week, day, type, school_id):
    """get menu for the given school, day, week and type"""
    school = School.objects.get(pk=school_id)
    season = school.season_choice
    if school.menu_type == School.Types.SIMPLE:
        weekly_meals = SimpleMeal.objects.filter(
            week=week, type=type, season=season, school=school
        ).order_by("day")
    else:
        weekly_meals = DetailedMeal.objects.filter(
            week=week, type=type, season=season, school=school
        ).order_by("day")
    meal_of_the_day = weekly_meals.get(day=day)
    context = {
        "school": school,
        "meal": meal_of_the_day,
        "weekly_meals": weekly_meals,
        "week": week,
        "day": day,
        "type": type,
    }
    return render(request, "partials/_menu.html", context)


# TODO: get this view working as requested in ISSUE #34
# @require_http_methods(["GET"])
# def json_menu(request):
#     current_week, adjusted_day = get_current_date()
#     adjusted_week = calculate_week(current_week, 0)
#     season = School.objects.first().season_choice
#     meal_for_today = DetailedMeal.objects.filter(
#         week=adjusted_week, type=1, season=season
#     )
#     serializer = MealSerializer(meal_for_today, many=True)
#     meals = list(serializer.data)
#     data = {"current_day": adjusted_day, "meals": meals}
#     return JsonResponse(data, safe=False)


@login_required
def settings_view(request, pk):
    """Get the settings page"""
    user = get_user(pk)
    context = {"user": user}
    return render(request, "settings.html", context)


@login_required
def menu_settings_partial(request, pk):
    """ " Get the menu partial of the settings page when reloaded after a change via htmx"""
    user = get_user(pk)
    context = {"user": user}
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
    school = get_object_or_404(School, user=request.user)
    form = SchoolForm(request.POST or None, instance=school)
    if form.is_valid():
        school = form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            f"<strong>{school.name}</strong> aggiornata con successo",
        )
        return render(request, "settings.html#school", {"school": school})

    context = {"form": form}
    return render(request, "partials/school.html", context)


def school_list(request):
    schools = School.objects.all().exclude(is_published=False)
    context = {"schools": schools}
    return TemplateResponse(request, "school-list.html", context)


@login_required
def upload_menu(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    menu_type = school.menu_type
    if request.method == "POST":
        form = UploadMenuForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            season = form.cleaned_data["season"]
            name, type = os.path.splitext(request.FILES["file"].name)
            import_menu(request, file, type, menu_type, school, season)
            return HttpResponse(status=204, headers={"HX-Trigger": "menuModified"})
        context = {"form": form, "school": school}
        return TemplateResponse(request, "upload-menu.html", context)
    else:
        form = UploadMenuForm()
    context = {"form": form, "school": school}
    return TemplateResponse(request, "upload-menu.html", context)


@login_required
def create_weekly_menu(request, school_id, week, season):
    qs = School.objects.all().select_related("user")
    school = get_object_or_404(qs, pk=school_id)
    menu_type = school.menu_type
    # check if the meal for the given week and season already exists
    if menu_type == School.Types.SIMPLE:
        weekly_meals = SimpleMeal.objects.filter(
            week=week, season=season, school=school
        )
    else:
        weekly_meals = DetailedMeal.objects.filter(
            week=week, season=season, school=school
        )
    # if the meals don't exist, create them with blank values
    if not weekly_meals.exists():
        if menu_type == School.Types.SIMPLE:
            for day in range(1, 6):
                SimpleMeal.objects.create(
                    week=week, day=day, season=season, school=school
                )
        else:
            for day in range(1, 6):
                DetailedMeal.objects.create(
                    week=week, day=day, season=season, school=school
                )
    # create a formset for editing the meals for the week
    if menu_type == School.Types.SIMPLE:
        MealFormSet = modelformset_factory(
            SimpleMeal,
            form=SimpleMealForm,
            extra=0,
            fields=("menu", "snack"),
        )
        meals = SimpleMeal.objects.filter(week=week, season=season, school=school)
    else:
        MealFormSet = modelformset_factory(
            DetailedMeal,
            form=DetailedMealForm,
            extra=0,
            fields=("first_course", "second_course", "side_dish", "fruit", "snack"),
        )
        meals = DetailedMeal.objects.filter(week=week, season=season, school=school)
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


@login_required
def export_menu(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    menu_type = school.menu_type
    if menu_type == School.Types.SIMPLE:
        meals = SimpleMeal.objects.filter(school=school)
        data = SimpleMealResource().export(meals)
    else:
        meals = DetailedMeal.objects.filter(school=school)
        data = DetailedMealResource().export(meals)

    response = HttpResponse(data.csv)
    response["Content-Disposition"] = 'attachment; filename="menu.csv"'
    return response
