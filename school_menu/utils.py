import csv
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from import_export.widgets import Widget

from notifications.models import AnonymousMenuNotification
from school_menu.cache import get_cached_or_query
from school_menu.models import AnnualMeal, DetailedMeal, Meal, School, SimpleMeal


def detect_csv_format(content: str) -> tuple[str, str]:
    """
    Detect CSV delimiter and quote character.
    Returns: (delimiter, quotechar)
    Uses csv.Sniffer for detection with fallback to comma then semicolon.
    """
    # Try csv.Sniffer first on a sample of the content
    try:
        sample = content[:1024]  # Use first 1KB for detection
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",;")
        return dialect.delimiter, dialect.quotechar
    except Exception:  # nosec B110
        # Sniffer failed, use fallback manual detection
        pass  # Intentionally fall through to manual detection

    # Fallback: try to detect by counting delimiters in first few lines
    lines = content.split("\n")[:5]  # Check first 5 lines
    comma_count = sum(line.count(",") for line in lines)
    semicolon_count = sum(line.count(";") for line in lines)

    if semicolon_count > comma_count:
        return ";", '"'

    # Default to comma (backward compatibility)
    return ",", '"'


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


def get_current_date(next_day=False):
    """
    Get current week and day.
    If next_day is True, returns the data for the next day.
    """
    target_date = datetime.now()
    if next_day:
        target_date += timedelta(days=1)

    # if it's weekend, get next monday
    if target_date.weekday() >= 5:  # Saturday or Sunday
        target_date += timezone.timedelta(days=(7 - target_date.weekday()))

    current_week = target_date.isocalendar()[1]
    day = target_date.isocalendar()[2]

    return current_week, day


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


def build_types_menu(weekly_meals, school, week=None, season=None):
    """
    Build the alternate meal menu for the given school, caching for 24 hours.

    Args:
        weekly_meals: List of meal objects (not QuerySet)
        school: School object
        week: Week number (optional, for cache key specificity)
        season: Season (optional, for cache key specificity)

    Returns:
        dict: Available meal types {label: type_code}

    Cache key: types_menu:{school_id}:w{week}:s{season} (if week/season provided)
               types_menu:{school_id} (otherwise)
    TTL: 24 hours (86400 seconds)
    """
    # Build cache key
    if week is not None and season is not None:
        cache_key = f"types_menu:{school.id}:w{week}:s{season}"
    else:
        cache_key = f"types_menu:{school.id}"

    # Query function to execute on cache miss
    def query_types():
        active_menu = [
            "S",  # Standard menu is always included
            "G" if school.no_gluten else None,
            "L" if school.no_lactose else None,
            "V" if school.vegetarian else None,
            "P" if school.special else None,
        ]
        active_menu = [menu for menu in active_menu if menu is not None]

        # Extract available types from the list of meals
        available_types = {m.type for m in weekly_meals}

        meals = {}
        for menu_type in active_menu:
            if menu_type in available_types:
                meals[Meal.Types(menu_type).label] = menu_type

        return meals

    # Get cached or query types menu
    return get_cached_or_query(cache_key, query_types, timeout=86400)


def validate_dataset(dataset, menu_type):
    """validates menu import dataset for required columns and values before importing into database and return validates = False and message if not valid"""
    validates = True
    message = None
    columns = dataset.headers

    # check required headers presence
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
    """
    Get meals for a school, caching weekly meals for 24 hours.

    Returns:
        tuple: (weekly_meals, meals_for_today) where both are lists (not QuerySets)
               Use list comprehensions for filtering: [m for m in meals if condition]

    Cache key: meals:{school_id}:w{week}:s{season}
    TTL: 24 hours (86400 seconds)
    """
    if school.menu_type == School.Types.SIMPLE:
        meal = SimpleMeal
    else:
        meal = DetailedMeal

    # Build cache key for weekly meals
    cache_key = f"meals:{school.id}:w{week}:s{season}"

    # Query function to execute on cache miss
    def query_weekly_meals():
        queryset = meal.objects.filter(
            school=school, week=week, season=season
        ).order_by("day")
        # Convert QuerySet to list for cacheability
        return list(queryset)

    # Get cached or query weekly meals
    weekly_meals = get_cached_or_query(cache_key, query_weekly_meals, timeout=86400)

    # Filter for today's meals from the cached list
    meals_for_today = [m for m in weekly_meals if m.day == day]

    return weekly_meals, meals_for_today


def get_meals_for_annual_menu(school, next_day=False):
    """
    Get current week's meals and today's meal for annual menu, caching for 7 days.

    Returns:
        tuple: (weekly_meals, meals_for_today) where both are lists (not QuerySets)
               Use list comprehensions for filtering: [m for m in meals if condition]

    Cache key: annual_meals:{school_id}:{year}:w{week}
    TTL: 7 days (604800 seconds)
    """
    target_date = datetime.now().date()
    if next_day:
        target_date += timedelta(days=1)

    # If weekend, get next Monday's date
    if target_date.weekday() >= 5:  # Saturday (5) or Sunday (6)
        target_date += timezone.timedelta(days=(7 - target_date.weekday()))

    # Get meals for the week of the target date
    year, week, _ = target_date.isocalendar()

    # Build cache key for weekly meals
    cache_key = f"annual_meals:{school.id}:{year}:w{week}"

    # Query function to execute on cache miss
    def query_weekly_meals():
        queryset = AnnualMeal.objects.filter(
            school=school, date__week=week, date__year=year
        ).order_by("date")
        # Convert QuerySet to list for cacheability
        return list(queryset)

    # Get cached or query weekly meals
    weekly_meals = get_cached_or_query(cache_key, query_weekly_meals, timeout=604800)

    # Filter for today's meals from the cached list
    meals_for_today = [m for m in weekly_meals if m.date == target_date and m.is_active]

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


def get_notifications_status(pk, school):
    if pk:
        notification = get_object_or_404(AnonymousMenuNotification, pk=pk)
        if notification.school == school and notification.daily_notification:
            return True
    return False
