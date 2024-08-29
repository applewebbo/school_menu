from datetime import datetime

import pandas as pd
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from import_export.widgets import Widget

from school_menu.models import DetailedMeal, School, SimpleMeal


# TODO: need to refactor this function when number of weeks is different than 4 in settings
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
    today = datetime.now()
    current_year, current_week, current_day = today.isocalendar()
    # get next week monday's menu on weekends
    if current_day > 5:
        current_week = current_week + 1
        adjusted_day = 1
    else:
        adjusted_day = current_day
    return current_week, adjusted_day


def get_season(school):
    """
    Get season based on school's settings
    """
    season = school.season_choice
    if season == School.Seasons.AUTOMATICA:
        today = datetime.now()
        day, month = today.day, today.month
        if (
            month in [10, 11, 12, 1, 2]
            or (month == 3 and day < 21)
            or (month == 9 and day > 22)
        ):
            season = School.Seasons.INVERNALE
        else:
            season = School.Seasons.PRIMAVERILE
    return season


def get_user(pk):
    User = get_user_model()
    queryset = User.objects.select_related("school")
    user = get_object_or_404(queryset, pk=pk)
    return user


def import_menu(request, file, type, menu_type, school, season):
    """take a file and import the menu into the database dealing with validation errors and relative messages"""
    if type == ".csv":
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, engine="openpyxl")
    # Check if 'day' rows contain only the day names
    day_mapping = {
        "Lunedì": 1,
        "Martedì": 2,
        "Mercoledì": 3,
        "Giovedì": 4,
        "Venerdì": 5,
    }
    df["giorno"] = df["giorno"].map(day_mapping)
    if not df["giorno"].isin(day_mapping.values()).all():
        messages.error(
            request,
            'Formato non valido. La colonna "giorno" contiene valori diversi dai giorni della settimana.',
        )
        return
    if menu_type == School.Types.DETAILED:
        # check if the file contains all the required columns
        required_columns = [
            "giorno",
            "settimana",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
        ]
        if not all(column in df.columns for column in required_columns):
            messages.add_message(
                request,
                messages.ERROR,
                "Formato non valido. Il file non contiene tutte le colonne richieste.",
            )
            return

        for index, row in df.iterrows():
            DetailedMeal.objects.update_or_create(
                week=row["settimana"],
                day=row["giorno"],
                season=season,
                first_course=row["primo"],
                second_course=row["secondo"],
                side_dish=row["contorno"],
                fruit=row["frutta"],
                snack=row["spuntino"],
                school=school,
            )
        messages.add_message(
            request,
            messages.SUCCESS,
            "<strong>Menu</strong> salvato correttamente",
        )
        return
    else:
        # check if the file contains all the required columns
        required_columns = [
            "giorno",
            "settimana",
            "pranzo",
            "spuntino",
        ]
        if not all(column in df.columns for column in required_columns):
            messages.add_message(
                request,
                messages.ERROR,
                "Formato non valido. Il file non contiene tutte le colonne richieste.",
            )
            return
        for index, row in df.iterrows():
            SimpleMeal.objects.update_or_create(
                week=row["settimana"],
                day=row["giorno"],
                season=season,
                menu=row["pranzo"],
                snack=row["spuntino"],
                school=school,
            )
        messages.add_message(
            request,
            messages.SUCCESS,
            "<strong>Menu</strong> salvato correttamente",
        )
        return


class ChoicesWidget(Widget):
    """
    Widget that uses choice display values in place of database values
    """

    def __init__(self, choices, *args, **kwargs):
        """
        Creates a self.choices dict with a key, display value, and value,
        db value, e.g. {'Chocolate': 'CHOC'}
        """
        self.choices = dict(choices)
        self.revert_choices = {v: k for k, v in self.choices.items()}

    def clean(self, value, row=None, *args, **kwargs):
        """Returns the db value given the display value"""
        return self.revert_choices.get(value, value) if value else None

    def render(self, value, obj=None):
        """Returns the display value given the db value"""
        return self.choices.get(value, "")
