from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from import_export.widgets import Widget

from school_menu.models import AnnualMeal, DetailedMeal, Meal, School, SimpleMeal


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


def get_adjusted_year():
    """Get current year if date is after September 1st, otherwise previous year"""
    today = datetime.now()
    adjusted_year = today.year if today.month >= 9 else today.year - 1

    return adjusted_year


def get_user(pk):
    User = get_user_model()
    alt_menu = False
    queryset = User.objects.select_related("school").prefetch_related("menureport_set")
    user = get_object_or_404(queryset, pk=pk)
    if hasattr(user, "school"):
        if any(
            [
                user.school.no_gluten,
                user.school.no_lactose,
                user.school.vegetarian,
                user.school.special,
            ]
        ):
            alt_menu = True
    return user, alt_menu


def get_alt_menu(user):
    alt_menu = False
    if any(
        [
            user.school.no_gluten,
            user.school.no_lactose,
            user.school.vegetarian,
            user.school.special,
        ]
    ):
        alt_menu = True
    return alt_menu


def build_types_menu(weekly_meals, school):
    """Build the alternate meal menu for the given school based on presence of meal for the given day"""
    active_menu = [
        "S",  # Standard menu is always included
        "G" if school.no_gluten else None,
        "L" if school.no_lactose else None,
        "V" if school.vegetarian else None,
        "P" if school.special else None,
    ]
    active_menu = [menu for menu in active_menu if menu is not None]
    available_types = weekly_meals.values_list("type", flat=True).distinct()

    meals = {}
    for menu_type in active_menu:
        if menu_type in available_types:
            meals[Meal.Types(menu_type).label] = menu_type

    return meals


def validate_dataset(dataset, menu_type):
    """validates menu import dataset for required columns and values before importing into database and return validates = False and message if not valid"""
    validates = True
    message = None
    # check required headers presence
    columns = dataset.headers
    if menu_type == School.Types.SIMPLE:
        required_columns = [
            "giorno",
            "settimana",
            "pranzo",
            "spuntino",
            "merenda",
        ]
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


def validate_annual_dataset(dataset):
    """validates menu import dataset for required columns and values before importing into database and return validates = False and message if not valid"""
    validates = True
    message = None

    # check required headers presence
    columns = dataset.headers
    required_columns = ["data", "primo", "secondo", "contorno", "frutta", "altro"]
    if not all(column in columns for column in required_columns):
        validates = False
        message = "Formato non valido. Il file non contiene tutte le colonne richieste."
        return validates, message

    # check if data column contain valid data values
    dates = dataset["data"]
    for date_str in dates:
        try:
            datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            validates = False
            message = 'Formato non valido. La colonna "data" contiene date in formato non valido. Usa il formato GG/MM/AAAA'
            return validates, message

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


def get_meals(school, season, week, day):
    if school.menu_type == School.Types.SIMPLE:
        meal = SimpleMeal
    else:
        meal = DetailedMeal
    weekly_meals = meal.objects.filter(
        school=school, week=week, season=season
    ).order_by("day")
    meals_for_today = weekly_meals.filter(day=day)

    return weekly_meals, meals_for_today


def get_meals_for_annual_menu(school):
    """Get current week's meals and today's meal for annual menu"""
    date = datetime.now().date()

    # Get the current week and year
    year, current_week, _ = date.isocalendar()

    # If weekend, get next week and next Monday's date
    if date.weekday() >= 5:  # Saturday (5) or Sunday (6)
        target_date = date + timedelta(days=(7 - date.weekday()))
        year, current_week, _ = target_date.isocalendar()
        date = target_date

    # Get meals for the current/next week (Monday to Friday)
    weekly_meals = AnnualMeal.objects.filter(
        school=school, date__week=current_week
    ).order_by("date")

    # Get target date meal (current date or next Monday if weekend)
    meals_for_today = AnnualMeal.objects.filter(school=school, date=date)

    return weekly_meals, meals_for_today


def fill_missing_dates(school, meal_type):
    existing_dates = set(
        AnnualMeal.objects.filter(school=school, type=meal_type).values_list(
            "date", flat=True
        )
    )
    start_date = min(existing_dates)
    end_date = max(existing_dates)
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday to Friday
            if current_date not in existing_dates:
                AnnualMeal.objects.create(
                    school=school,
                    type=meal_type,
                    date=current_date,
                    day=current_date.weekday() + 1,
                    is_active=False,
                )
        current_date += timedelta(days=1)
