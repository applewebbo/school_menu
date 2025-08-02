from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from notifications.utils import build_menu_notification_payload
from school_menu.models import AnnualMeal, DetailedMeal, School, SimpleMeal

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user("test@test.com", "test")


@pytest.fixture
def school(user):
    return School.objects.create(
        name="Test School", city="Test City", user=user, menu_type=School.Types.SIMPLE
    )


@pytest.fixture
def detailed_school(user):
    return School.objects.create(
        name="Detailed School",
        city="Test City",
        user=User.objects.create_user("test2@test.com", "test"),
        menu_type=School.Types.DETAILED,
    )


@pytest.fixture
def annual_school(user):
    return School.objects.create(
        name="Annual School",
        city="Test City",
        user=User.objects.create_user("test3@test.com", "test"),
        annual_menu=True,
    )


@pytest.mark.parametrize(
    "is_previous_day",
    [False, True],
)
def test_build_menu_notification_payload_annual_menu(annual_school, is_previous_day):
    """Test payload building for annual menus for today and tomorrow."""
    meal_date = timezone.now().date()
    if is_previous_day:
        meal_date += timedelta(days=1)

    # If the date is a weekend, move to next Monday to match app logic
    if meal_date.weekday() >= 5:
        meal_date += timedelta(days=(7 - meal_date.weekday()))

    AnnualMeal.objects.create(
        school=annual_school,
        date=meal_date,
        menu="Annual Menu",
        snack="Annual Snack",
        is_active=True,
    )
    payload = build_menu_notification_payload(
        annual_school, is_previous_day=is_previous_day
    )
    expected_head = (
        f"Menu di domani {annual_school.name}"
        if is_previous_day
        else f"Menu {annual_school.name}"
    )
    assert payload is not None
    assert payload["head"] == expected_head
    assert "Annual Menu" in payload["body"]
    assert "Annual Snack" in payload["body"]


@pytest.mark.parametrize(
    "meal_data, expected_body",
    [
        ({"morning_snack": "Snack", "menu": "", "afternoon_snack": ""}, "Snack"),
        ({"morning_snack": "", "menu": "Menu", "afternoon_snack": ""}, "Menu"),
        (
            {"morning_snack": "", "menu": "", "afternoon_snack": "Snack"},
            "Snack",
        ),
        (
            {"morning_snack": "", "menu": "", "afternoon_snack": ""},
            "Nessun menu previsto.",
        ),
    ],
)
def test_build_menu_notification_payload_simple_menu_empty_parts(
    school, meal_data, expected_body
):
    """Test payload building for simple menu with some empty fields."""
    SimpleMeal.objects.create(
        school=school,
        day=1,
        week=1,
        season=School.Seasons.PRIMAVERILE,
        **meal_data,
    )
    with (
        patch("notifications.utils.get_current_date", return_value=(1, 1)),
        patch("notifications.utils.calculate_week", return_value=1),
    ):
        payload = build_menu_notification_payload(school)
        assert payload["body"] == expected_body


@pytest.mark.parametrize(
    "meal_data, expected_body",
    [
        ({"first_course": "Primo", "second_course": "", "side_dish": ""}, "Primo"),
        ({"first_course": "", "second_course": "Secondo", "side_dish": ""}, "Secondo"),
        (
            {"first_course": "", "second_course": "", "side_dish": "Contorno"},
            "Contorno",
        ),
        (
            {"first_course": "", "second_course": "", "side_dish": ""},
            "Nessun menu previsto.",
        ),
    ],
)
def test_build_menu_notification_payload_detailed_menu_empty_parts(
    detailed_school, meal_data, expected_body
):
    """Test payload building for detailed menu with some empty fields."""
    DetailedMeal.objects.create(
        school=detailed_school,
        day=1,
        week=1,
        season=School.Seasons.PRIMAVERILE,
        **meal_data,
    )
    with (
        patch("notifications.utils.get_current_date", return_value=(1, 1)),
        patch("notifications.utils.calculate_week", return_value=1),
    ):
        payload = build_menu_notification_payload(detailed_school)
        assert payload["body"] == expected_body


@pytest.mark.parametrize(
    "school_fixture, meal_model, meal_data",
    [
        (
            "school",
            SimpleMeal,
            {
                "menu": "Simple Menu",
                "morning_snack": "Morning Snack",
                "afternoon_snack": "Afternoon Snack",
            },
        ),
        (
            "detailed_school",
            DetailedMeal,
            {
                "first_course": "First Course",
                "second_course": "Second Course",
                "side_dish": "Side Dish",
            },
        ),
    ],
)
@pytest.mark.parametrize("is_previous_day", [False, True])
def test_build_menu_notification_payload_weekly_menus(
    request,
    school_fixture,
    meal_model,
    meal_data,
    is_previous_day,
    monkeypatch,
):
    """Test payload building for simple and detailed weekly menus."""
    school = request.getfixturevalue(school_fixture)
    target_date = timezone.now()
    if is_previous_day:
        target_date += timedelta(days=1)

    # Ensure we are not on a weekend
    if target_date.weekday() >= 5:
        target_date += timedelta(days=(7 - target_date.weekday()))

    week, day = target_date.isocalendar()[1], target_date.weekday() + 1

    from school_menu.utils import calculate_week

    # ... (omitting unchanged parts of the file for brevity)

    monkeypatch.setattr(
        "school_menu.utils.get_current_date", lambda next_day=False: (week, day)
    )
    monkeypatch.setattr(
        "school_menu.utils.get_season", lambda school: School.Seasons.PRIMAVERILE
    )

    # Use the real calculate_week function to ensure consistency
    calculated_week = calculate_week(week, school.week_bias)

    meal_model.objects.create(
        school=school,
        day=day,
        week=calculated_week,
        season=School.Seasons.PRIMAVERILE,
        **meal_data,
    )

    payload = build_menu_notification_payload(school, is_previous_day=is_previous_day)

    expected_head = (
        f"Menu di domani {school.name}" if is_previous_day else f"Menu {school.name}"
    )
    assert payload is not None, "Payload should not be None"
    assert payload["head"] == expected_head
    for key, value in meal_data.items():
        assert value in payload["body"]


def test_build_menu_notification_payload_no_meal_found(school):
    """Test that payload is None when no meal is found."""
    with (
        patch("notifications.utils.get_current_date", return_value=(1, 1)),
        patch("notifications.utils.calculate_week", return_value=1),
    ):
        payload = build_menu_notification_payload(school)
        assert payload is None


def test_build_menu_notification_payload_annual_menu_empty_parts(annual_school):
    """Test payload for annual menu with empty menu and snack."""
    meal_date = timezone.now().date()
    if meal_date.weekday() >= 5:
        meal_date += timedelta(days=(7 - meal_date.weekday()))

    AnnualMeal.objects.create(
        school=annual_school,
        date=meal_date,
        menu="",
        snack="",
        is_active=True,
    )
    payload = build_menu_notification_payload(annual_school)
    assert payload is not None
    assert payload["body"] == "Nessun menu previsto."
