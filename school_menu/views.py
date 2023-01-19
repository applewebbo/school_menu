import datetime

from django.core.serializers import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from school_menu.models import Meal
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
    adjusted_week = calculate_week(current_week, 0)
    meal_for_today = Meal.objects.filter(week=adjusted_week, day=adjusted_day).first()
    context = {"meal": meal_for_today, "week": adjusted_week, "day": adjusted_day}
    return render(request, "index.html", context)


def get_menu(request, week, day, type):
    meal = Meal.objects.filter(week=week, day=day, type=type).first()
    context = {"meal": meal, "week": week, "day": day}
    return render(request, "partials/_menu.html", context)


@require_http_methods(["GET"])
def json_menu(request):
    current_week, adjusted_day = get_current_date()
    adjusted_week = calculate_week(current_week, 0)
    meal_for_today = Meal.objects.filter(week=adjusted_week, type=1)
    serializer = MealSerializer(meal_for_today, many=True)
    meals = list(serializer.data)
    data = {"current_day": adjusted_day, "meals": meals}
    return JsonResponse(data, safe=False)
