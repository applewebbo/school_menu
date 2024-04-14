import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from school_menu.forms import SchoolForm, SettingsForm
from school_menu.models import Meal, School, Settings
from school_menu.serializers import MealSerializer


def calculate_week(week, bias):
    """
    Getting week number from today's date translated to week number available in Meal model (1,2,3,4) shifted by bias
    """
    week_number = (week + bias) / 4
    floor_week_number = (week + bias) // 4
    if week_number == floor_week_number:
        return 4
    else:
        return int((week_number - floor_week_number) * 4)


def get_current_date():
    """
    Get current week and day
    """
    today = datetime.datetime.now()
    current_year, current_week, current_day = today.isocalendar()
    # get next week monday's menu on weekends
    if current_day > 5:
        current_week = current_week + 1
        adjusted_day = 1
    else:
        adjusted_day = current_day
    return current_week, adjusted_day


def index(request):
    current_week, adjusted_day = get_current_date()
    bias = Settings.objects.first().week_bias
    adjusted_week = calculate_week(current_week, bias)
    season = Settings.objects.first().season_choice
    meal_for_today = Meal.objects.filter(
        week=adjusted_week, day=adjusted_day, season=season
    ).first()
    context = {"meal": meal_for_today, "week": adjusted_week, "day": adjusted_day}
    return render(request, "index.html", context)


def school_menu(request, slug):
    """Return school menu for the given school"""
    school = get_object_or_404(School, slug=slug)
    current_week, adjusted_day = get_current_date()
    bias = Settings.objects.get(school=school).week_bias
    adjusted_week = calculate_week(current_week, bias)
    season = Settings.objects.get(school=school).season_choice
    meal_for_today = Meal.objects.filter(
        week=adjusted_week, day=adjusted_day, season=season
    ).first()
    context = {"meal": meal_for_today, "week": adjusted_week, "day": adjusted_day}
    return render(request, "school-menu.html", context)


def get_menu(request, week, day, type):
    season = Settings.objects.first().season_choice
    meal = Meal.objects.filter(week=week, day=day, type=type, season=season).first()
    context = {"meal": meal, "week": week, "day": day}
    return render(request, "partials/_menu.html", context)


@require_http_methods(["GET"])
def json_menu(request):
    current_week, adjusted_day = get_current_date()
    adjusted_week = calculate_week(current_week, 0)
    season = Settings.objects.first().season_choice
    meal_for_today = Meal.objects.filter(week=adjusted_week, type=1, season=season)
    serializer = MealSerializer(meal_for_today, many=True)
    meals = list(serializer.data)
    data = {"current_day": adjusted_day, "meals": meals}
    return JsonResponse(data, safe=False)


@login_required
def settings_view(request, pk):
    User = get_user_model()
    queryset = User.objects.select_related("school", "settings")
    user = get_object_or_404(queryset, pk=pk)
    context = {"user": user}
    return render(request, "settings.html", context)


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
            f"<strong>{school.name}</strong> created successfully",
        )
        return render(request, "settings.html#school", {"school": school})

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
            f"<strong>{school.name}</strong> updated successfully",
        )
        return render(request, "settings.html#school", {"school": school})

    context = {"form": form}
    return render(request, "partials/school.html", context)


@login_required
def settings_create(request):
    user = request.user
    form = SettingsForm(request.POST or None)
    if form.is_valid():
        settings = form.save(commit=False)
        settings.user = user
        settings.save()
        return render(request, "settings.html#settings", {"user": user})

    context = {"form": form, "create": True}
    return render(request, "partials/settings.html", context)


@login_required
def settings_update(request):
    user = request.user
    settings = get_object_or_404(Settings, user=user)
    form = SettingsForm(request.POST or None, instance=settings)
    if form.is_valid():
        settings = form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Settings updated successfully",
        )
        return render(request, "settings.html#settings", {"user": user})

    context = {"form": form}
    return render(request, "partials/settings.html", context)
