from datetime import datetime

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from import_export.widgets import Widget

from school_menu.models import School


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


def validate_dataset(dataset, menu_type):
    """validates menu import dataset for required columns and values before importing into database and return validates = False and message if not valid"""
    validates = True
    message = None
    # check required headers presence
    columns = dataset.headers
    if menu_type == School.Types.SIMPLE:
        required_columns = ["giorno", "settimana", "pranzo", "spuntino"]
    else:
        required_columns = [
            "giorno",
            "settimana",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
        ]
    if not all(column in columns for column in required_columns):
        validates = False
        message = "Formato non valido. Il file non contiene tutte le colonne richieste."
        return validates, message

    # check if the day column contains only valid day names
    days = {"Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì"}
    day_values = dataset["giorno"]
    if not all(day in days for day in day_values):
        validates = False
        message = 'Formato non valido. La colonna "giorno" contiene valori diversi dai giorni della settimana.'

    # check if week values are 1 to 4
    weeks = dataset["settimana"]
    try:
        weeks = [int(week) for week in weeks]
    except ValueError:
        validates = False
        message = (
            'Formato non valido. La colonna "settimana" contiene valori non numerici.'
        )
        return validates, message
    if not all(0 < week <= 4 for week in weeks):
        validates = False
        message = 'Formato non valido. La colonna "settimana" contiene valori non compresi fra 1 e 4.'

    # if everything ok return validates = True and no message
    return validates, message


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
