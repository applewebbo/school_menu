"""Meal retrieval and menu building utilities for school menu management."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone

from school_menu.cache import get_cached_or_query
from school_menu.constants import (
    CACHE_TTL_7_DAYS,
    CACHE_TTL_24_HOURS,
    FIRST_WEEKEND_DAY,
    LAST_WORKING_DAY,
)
from school_menu.models import AnnualMeal, DetailedMeal, Meal, School, SimpleMeal


def get_user(pk: int) -> tuple:
    """
    Get user with related school and menu reports, checking for alternative menus.

    Prefetches related data to avoid N+1 queries.

    Args:
        pk: User primary key

    Returns:
        Tuple of (user, alt_menu):
        - user: User instance with prefetched school and menu reports
        - alt_menu: True if school has any alternative menu options enabled

    Raises:
        Http404: If user not found
    """
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


def get_alt_menu(user) -> bool:
    """
    Check if a user's school has alternative menu options enabled.

    Args:
        user: User instance with school attribute

    Returns:
        True if school has any alternative menu (gluten-free, lactose-free,
        vegetarian, or special), False otherwise
    """
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


def build_types_menu(
    weekly_meals: list,
    school: School,
    week: int | None = None,
    season: int | None = None,
) -> dict[str, str]:
    """
    Build the alternate meal menu for the given school, caching for 24 hours.

    Creates a dictionary of available meal types based on school settings
    and actual meals available in the dataset.

    Args:
        weekly_meals: List of meal objects (not QuerySet) for the week
        school: School object
        week: Week number (optional, for cache key specificity)
        season: Season code (optional, for cache key specificity)

    Returns:
        Dictionary of available meal types: {label: type_code}
        e.g., {'Standard': 'S', 'Senza Glutine': 'G'}

    Cache:
        - Key: types_menu:{school_id}:w{week}:s{season} (if week/season provided)
              or types_menu:{school_id} (otherwise)
        - TTL: 24 hours (86400 seconds)
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
                meals[str(Meal.Types(menu_type).label)] = menu_type

        return meals

    # Get cached or query types menu
    return get_cached_or_query(cache_key, query_types, timeout=CACHE_TTL_24_HOURS)


def get_meals(school: School, season: int, week: int, day: int) -> tuple[list, list]:
    """
    Get meals for a school, caching weekly meals for 24 hours.

    Args:
        school: School instance
        season: Season code (School.Seasons.INVERNALE or PRIMAVERILE)
        week: Week number (1-4)
        day: Day number (1=Monday, 7=Sunday)

    Returns:
        Tuple of (weekly_meals, meals_for_today):
        - weekly_meals: List of all meals for the week
        - meals_for_today: List of meals for the specified day

        Both are lists (not QuerySets). Use list comprehensions for filtering:
        [m for m in meals if condition]

    Cache:
        - Key: meals:{school_id}:w{week}:s{season}
        - TTL: 24 hours (86400 seconds)
    """
    meal: type[SimpleMeal] | type[DetailedMeal]
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
    weekly_meals = get_cached_or_query(
        cache_key, query_weekly_meals, timeout=CACHE_TTL_24_HOURS
    )

    # Filter for today's meals from the cached list
    meals_for_today = [m for m in weekly_meals if m.day == day]

    return weekly_meals, meals_for_today


def get_meals_for_annual_menu(
    school: School, next_day: bool = False
) -> tuple[list, list]:
    """
    Get current week's meals and today's meal for annual menu, caching for 7 days.

    For annual menus that use specific dates instead of week rotations.

    Args:
        school: School instance
        next_day: If True, returns meals for the next day instead of today

    Returns:
        Tuple of (weekly_meals, meals_for_today):
        - weekly_meals: List of all meals for the current week
        - meals_for_today: List of active meals for the target date

        Both are lists (not QuerySets). Use list comprehensions for filtering:
        [m for m in meals if condition]

    Cache:
        - Key: annual_meals:{school_id}:{year}:w{week}
        - TTL: 7 days (604800 seconds)

    Note:
        Automatically skips to next Monday if target date falls on weekend.
    """
    target_date = timezone.now().date()
    if next_day:
        target_date += timedelta(days=1)

    # If weekend, get next Monday's date
    if target_date.weekday() >= FIRST_WEEKEND_DAY:  # Saturday (5) or Sunday (6)
        target_date += timedelta(days=(7 - target_date.weekday()))

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
    weekly_meals = get_cached_or_query(
        cache_key, query_weekly_meals, timeout=CACHE_TTL_7_DAYS
    )

    # Filter for today's meals from the cached list
    meals_for_today = [m for m in weekly_meals if m.date == target_date and m.is_active]

    return weekly_meals, meals_for_today


def fill_missing_dates(school: School, meal_type: str) -> None:
    """
    Fill missing weekday dates with inactive annual meals.

    Optimized to use bulk_create for massive performance improvement
    (N queries → 1 query).

    Creates inactive meal entries for all weekdays between the earliest
    and latest existing meal dates that don't already have meals.

    Args:
        school: School instance
        meal_type: Meal type code (e.g., 'S' for standard)

    Note:
        Only creates meals for weekdays (Monday-Friday).
        All created meals are marked as inactive.
    """
    existing_dates = set(
        AnnualMeal.objects.filter(school=school, type=meal_type).values_list(
            "date", flat=True
        )
    )
    start_date = min(existing_dates)
    end_date = max(existing_dates)
    current_date = start_date

    # Collect all missing dates in a list
    meals_to_create = []
    while current_date <= end_date:
        if current_date.weekday() <= LAST_WORKING_DAY:  # Monday to Friday
            if current_date not in existing_dates:
                meals_to_create.append(
                    AnnualMeal(
                        school=school,
                        type=meal_type,
                        date=current_date,
                        day=current_date.weekday() + 1,
                        is_active=False,
                    )
                )
        current_date += timedelta(days=1)

    # Bulk create all missing meals in a single query (N→1 query optimization)
    if meals_to_create:
        AnnualMeal.objects.bulk_create(meals_to_create)
