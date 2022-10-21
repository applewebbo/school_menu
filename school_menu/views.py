import datetime

from django.shortcuts import render

from school_menu.models import Meal


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


def index(request):
    today = datetime.datetime.now()
    current_year, current_week, current_day = today.isocalendar()
    # get next week monday's menu on weekends
    if current_day > 5:
        current_week = current_week + 1
        adjusted_day = 1
    else:
        adjusted_day = current_day
    adjusted_week = calculate_week(current_week, 1)
    meal_for_today = Meal.objects.filter(week=adjusted_week, day=adjusted_day).first()
    context = {"meal": meal_for_today, "week": adjusted_week, "day": adjusted_day}
    return render(request, "index.html", context)


def get_menu(request, week, day):
    meal = Meal.objects.filter(week=week, day=day).first()
    context = {"meal": meal, "week": week, "day": day}
    return render(request, "partials/_menu.html", context)
