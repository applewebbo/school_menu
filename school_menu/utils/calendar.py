"""Calendar and date calculation utilities for school menu management."""

from datetime import date, timedelta

from django.utils import timezone

from school_menu.constants import (
    ACADEMIC_YEAR_START_MONTH,
    AUTUMN_EQUINOX_DAY,
    AUTUMN_EQUINOX_MONTH,
    FIRST_WEEKEND_DAY,
    SPRING_EQUINOX_DAY,
    SPRING_EQUINOX_MONTH,
    WINTER_MONTHS,
)
from school_menu.models import School


def calculate_week(week: int, bias: int) -> int:
    """
    Calculate week number (1-4) from ISO week number with bias adjustment.

    Translates ISO week numbers to menu week numbers (1-4) with an optional bias.
    The bias allows schools to shift their menu rotation cycle.

    Args:
        week: ISO week number (1-53)
        bias: Number of weeks to shift the rotation (can be negative)

    Returns:
        Week number between 1 and 4

    Example:
        >>> calculate_week(1, 0)  # First week of year, no bias
        1
        >>> calculate_week(5, 0)  # Fifth week wraps to week 1
        1
        >>> calculate_week(1, 3)  # First week with +3 bias shifts to week 4
        4
    """
    week_number = (week + bias) / 4
    floor_week_number = (week + bias) // 4
    if week_number == floor_week_number:
        return 4
    return int((week_number - floor_week_number) * 4)


def get_target_date(next_day: bool = False) -> date:
    """
    Get the real calendar date of "today" (or "tomorrow"), skipping weekends
    to the next Monday.

    Shared by get_current_date, get_meals_for_annual_menu and
    get_special_meal.

    Args:
        next_day: If True, returns the date for the next day instead of today

    Returns:
        The target date, moved to next Monday if it would otherwise fall on
        a Saturday or Sunday.
    """
    target_date = timezone.now().date()
    if next_day:
        target_date += timedelta(days=1)

    # If it's weekend, get next Monday
    if target_date.weekday() >= FIRST_WEEKEND_DAY:  # Saturday or Sunday
        target_date += timedelta(days=(7 - target_date.weekday()))

    return target_date


def get_current_date(next_day: bool = False) -> tuple[int, int]:
    """
    Get current week and day numbers, optionally for the next day.

    If the current day is weekend (Saturday/Sunday), returns next Monday's date.

    Args:
        next_day: If True, returns data for the next day instead of today

    Returns:
        Tuple of (week_number, day_number) where:
        - week_number: ISO week number (1-53)
        - day_number: ISO weekday number (1=Monday, 7=Sunday)

    Example:
        >>> get_current_date()  # On a Monday
        (14, 1)
        >>> get_current_date(next_day=True)  # Returns Tuesday
        (14, 2)
    """
    target_date = get_target_date(next_day)
    current_week, day = target_date.isocalendar()[1], target_date.isocalendar()[2]

    return current_week, day


def get_season(school: School) -> int:
    """
    Get the current season for a school based on its settings.

    Returns either the school's configured season or auto-determines it
    based on equinox dates if set to automatic.

    Args:
        school: School instance

    Returns:
        Season code: School.Seasons.INVERNALE or School.Seasons.PRIMAVERILE

    Note:
        Winter season is defined as:
        - December, January, February (full months)
        - March before spring equinox (~March 20)
        - September after autumn equinox (~September 23)
    """
    season = school.season_choice
    if season == School.Seasons.AUTOMATICA:
        today = timezone.now()
        day, month = today.day, today.month
        if (
            month in WINTER_MONTHS
            or (month == SPRING_EQUINOX_MONTH and day < SPRING_EQUINOX_DAY)
            or (month == AUTUMN_EQUINOX_MONTH and day > AUTUMN_EQUINOX_DAY)
        ):
            season = School.Seasons.INVERNALE
        else:
            season = School.Seasons.PRIMAVERILE
    return season


def is_school_in_session(school: School, target_date) -> bool:
    """
    Check if the school is in session on a given date.

    Uses the school's start_month/start_day and end_month/end_day to determine
    if the target date falls within the academic year.

    Args:
        school: School instance with session date configuration
        target_date: Date to check

    Returns:
        True if school is in session on target date, False otherwise

    Note:
        Handles academic years that span calendar years (e.g., Sept to June)
    """
    start_month = school.start_month
    start_day = school.start_day
    end_month = school.end_month
    end_day = school.end_day

    # Create comparable tuples for dates (month, day)
    today_tuple = (target_date.month, target_date.day)
    start_tuple = (start_month, start_day)
    end_tuple = (end_month, end_day)

    # Case 1: School year is within the same calendar year (e.g., Feb to June)
    if start_tuple <= end_tuple:
        return start_tuple <= today_tuple <= end_tuple
    # Case 2: School year spans across calendar years (e.g., Sept to June)
    else:
        return today_tuple >= start_tuple or today_tuple <= end_tuple


def get_adjusted_year() -> int:
    """
    Get the current academic year.

    Returns the current year if we're past September 1st, otherwise returns
    the previous year. This aligns with academic years that start in September.

    Returns:
        Academic year as integer (e.g., 2024 for academic year 2024-2025)

    Example:
        >>> # If today is October 15, 2024
        >>> get_adjusted_year()
        2024
        >>> # If today is June 20, 2024
        >>> get_adjusted_year()
        2023
    """
    today = timezone.now()
    adjusted_year = (
        today.year if today.month >= ACADEMIC_YEAR_START_MONTH else today.year - 1
    )

    return adjusted_year
