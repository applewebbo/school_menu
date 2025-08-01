from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from notifications.utils import build_menu_notification_payload
from school_menu.models import AnnualMeal, DetailedMeal, School, SimpleMeal

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user("test@test.com", "test")


@pytest.fixture
def school(db, user):
    return School.objects.create(
        name="Test School", city="Test City", user=user, menu_type=School.Types.SIMPLE
    )


@pytest.fixture
def detailed_school(db, user):
    school = School.objects.create(
        name="Detailed School",
        city="Test City",
        user=User.objects.create_user("test2@test.com", "test"),
        menu_type=School.Types.DETAILED,
    )
    return school


@pytest.fixture
def annual_school(db, user):
    school = School.objects.create(
        name="Annual School",
        city="Test City",
        user=User.objects.create_user("test3@test.com", "test"),
        annual_menu=True,
    )
    return school


def test_build_menu_notification_payload_annual_menu(annual_school):
    AnnualMeal.objects.create(
        school=annual_school,
        date=date.today(),
        menu="Annual Menu",
        snack="Annual Snack",
    )
    payload = build_menu_notification_payload(annual_school)
    assert payload["head"] == f"Menu {annual_school.name}"
    assert "Annual Menu" in payload["body"]
    assert "Annual Snack" in payload["body"]


def test_build_menu_notification_payload_annual_menu_no_meal(annual_school):
    payload = build_menu_notification_payload(annual_school)
    assert payload["head"] == f"Menu {annual_school.name}"
    assert payload["body"] == "Nessun menu previsto per oggi."


def test_build_menu_notification_payload_simple_menu(school):
    with (
        patch("notifications.utils.get_current_date", return_value=(1, 1)),
        patch("notifications.utils.get_season", return_value=1),
        patch("notifications.utils.calculate_week", return_value=1),
    ):
        SimpleMeal.objects.create(
            school=school,
            day=1,
            week=1,
            season=1,
            menu="Simple Menu",
            morning_snack="Morning Snack",
            afternoon_snack="Afternoon Snack",
        )
        payload = build_menu_notification_payload(school)
        assert payload["head"] == f"Menu {school.name}"
        assert "Morning Snack" in payload["body"]
        assert "Simple Menu" in payload["body"]
        assert "Afternoon Snack" in payload["body"]


def test_build_menu_notification_payload_simple_menu_no_meal(school):
    with (
        patch("notifications.utils.get_current_date", return_value=(1, 1)),
        patch("notifications.utils.get_season", return_value=1),
        patch("notifications.utils.calculate_week", return_value=1),
    ):
        payload = build_menu_notification_payload(school)
        assert payload["head"] == f"Menu {school.name}"
        assert payload["body"] == "Nessun menu previsto per oggi."


def test_build_menu_notification_payload_detailed_menu(detailed_school):
    with (
        patch("notifications.utils.get_current_date", return_value=(1, 1)),
        patch("notifications.utils.get_season", return_value=1),
        patch("notifications.utils.calculate_week", return_value=1),
    ):
        DetailedMeal.objects.create(
            school=detailed_school,
            day=1,
            week=1,
            season=1,
            first_course="First Course",
            second_course="Second Course",
            side_dish="Side Dish",
        )
        payload = build_menu_notification_payload(detailed_school)
        assert payload["head"] == f"Menu {detailed_school.name}"
        assert "First Course" in payload["body"]
        assert "Second Course" in payload["body"]
        assert "Side Dish" in payload["body"]


def test_build_menu_notification_payload_annual_menu_empty_fields(annual_school):
    AnnualMeal.objects.create(
        school=annual_school,
        date=date.today(),
        menu="",
        snack="",
    )
    payload = build_menu_notification_payload(annual_school)
    assert payload["head"] == f"Menu {annual_school.name}"
    assert payload["body"] == "Nessun menu previsto per oggi."


def test_build_menu_notification_payload_detailed_menu_no_meal(detailed_school):
    with (
        patch("notifications.utils.get_current_date", return_value=(1, 1)),
        patch("notifications.utils.get_season", return_value=1),
        patch("notifications.utils.calculate_week", return_value=1),
    ):
        payload = build_menu_notification_payload(detailed_school)
        assert payload["head"] == f"Menu {detailed_school.name}"
        assert payload["body"] == "Nessun menu previsto per oggi."


def test_build_menu_notification_payload_empty_fields(school):
    with (
        patch("notifications.utils.get_current_date", return_value=(1, 1)),
        patch("notifications.utils.get_season", return_value=1),
        patch("notifications.utils.calculate_week", return_value=1),
    ):
        SimpleMeal.objects.create(
            school=school,
            day=1,
            week=1,
            season=1,
            menu="",
            morning_snack="",
            afternoon_snack="",
        )
        payload = build_menu_notification_payload(school)
        assert payload["head"] == f"Menu {school.name}"
        assert payload["body"] == "Nessun menu previsto per oggi."
