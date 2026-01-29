"""Calendar and date calculation utilities for school menu management."""

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
    from datetime import timedelta

    target_date = timezone.now()
    if next_day:
        target_date += timedelta(days=1)

    # If it's weekend, get next Monday
    if target_date.weekday() >= FIRST_WEEKEND_DAY:  # Saturday or Sunday
        target_date += timedelta(days=(7 - target_date.weekday()))

    current_week = target_date.isocalendar()[1]
    day = target_date.isocalendar()[2]

    return current_week, day


def get_season(school: School) -> str:
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
