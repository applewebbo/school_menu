from school_menu.models import School
from school_menu.utils import (
    calculate_week,
    get_current_date,
    get_meals,
    get_meals_for_annual_menu,
    get_season,
)


def build_menu_notification_payload(school, is_previous_day=False):
    """
    Builds the payload (head and body) for the daily menu notification for a given school.

    Note: meals_for_today is a list (not QuerySet) after caching implementation.
    """
    if school.annual_menu:
        _, meals_for_today = get_meals_for_annual_menu(school, next_day=is_previous_day)
    else:
        current_week, day = get_current_date(next_day=is_previous_day)
        season = get_season(school)
        week = calculate_week(current_week, school.week_bias)
        _, meals_for_today = get_meals(school, season, week, day)

    # meals_for_today is a list, check if it's not empty
    if not meals_for_today:
        return None

    body = "Nessun menu previsto."
    head = f"Menu {school.name}"
    if is_previous_day:
        head = f"Menu di domani {school.name}"

    # Get first meal from the list
    meal = meals_for_today[0]
    body_parts = []
    if school.annual_menu:
        if meal.menu:
            body_parts.append(meal.menu)
        if meal.snack:
            body_parts.append(meal.snack)
    elif school.menu_type == School.Types.SIMPLE:
        if meal.morning_snack:
            body_parts.append(meal.morning_snack)
        if meal.menu:
            body_parts.append(meal.menu)
        if meal.afternoon_snack:
            body_parts.append(meal.afternoon_snack)
    else:  # DetailedMeal
        body_parts.append(meal.first_course)
        body_parts.append(meal.second_course)
        body_parts.append(meal.side_dish)

    if body_parts:
        body = "\n".join(filter(None, body_parts))
        if not any(body_parts):
            body = "Nessun menu previsto."

    return {"head": head, "body": body}
