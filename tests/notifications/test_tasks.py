from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django_q.models import Schedule
from pywebpush import WebPushException

from notifications.models import AnonymousMenuNotification
from notifications.tasks import (
    schedule_daily_menu_notification,
    send_daily_menu_notification,
    send_test_notification,
)
from school_menu.models import DetailedMeal, School, SimpleMeal

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        "test@test.com", "test", first_name="test", last_name="test"
    )


@pytest.fixture
def user2(db):
    return User.objects.create_user(
        "test2@test.com", "test", first_name="test", last_name="test"
    )


@pytest.fixture
def user3(db):
    return User.objects.create_user(
        "test3@test.com", "test", first_name="test", last_name="test"
    )


@pytest.fixture
def school(db, user):
    return School.objects.create(
        name="test school", city="test city", user=user, menu_type=School.Types.SIMPLE
    )


@pytest.fixture
def detailed_school(db, user2):
    return School.objects.create(
        name="test detailed school",
        city="test city",
        user=user2,
        menu_type=School.Types.DETAILED,
    )


@pytest.fixture
def annual_school(db, user3):
    return School.objects.create(
        name="test annual school",
        city="test city",
        user=user3,
        annual_menu=True,
    )


@pytest.fixture
def subscription(db, school):
    return AnonymousMenuNotification.objects.create(
        school=school,
        daily_notification=True,
        subscription_info={
            "endpoint": "test",
            "keys": {"p256dh": "test", "auth": "test"},
        },
    )


@pytest.fixture
def detailed_subscription(db, detailed_school):
    return AnonymousMenuNotification.objects.create(
        school=detailed_school,
        daily_notification=True,
        subscription_info={
            "endpoint": "test",
            "keys": {"p256dh": "test", "auth": "test"},
        },
    )


@pytest.fixture
def annual_subscription(db, annual_school):
    return AnonymousMenuNotification.objects.create(
        school=annual_school,
        daily_notification=True,
        subscription_info={
            "endpoint": "test",
            "keys": {"p256dh": "test", "auth": "test"},
        },
    )


@patch("notifications.tasks.send_test_notification")
def test_send_daily_menu_notification_simple_menu(
    mock_send_test_notification, db, monkeypatch, school, subscription
):
    """Test invio notifica giornaliera con menu semplice."""
    SimpleMeal.objects.create(
        school=school,
        day=1,
        week=1,
        season=1,
        menu="test menu",
        morning_snack="test morning snack",
        afternoon_snack="test afternoon snack",
    )

    def fake_get_current_date():
        return 1, 1

    monkeypatch.setattr("notifications.utils.get_current_date", fake_get_current_date)

    def fake_get_season(school):
        return 1

    monkeypatch.setattr("notifications.utils.get_season", fake_get_season)

    def fake_calculate_week(week, bias):
        return 1

    monkeypatch.setattr("notifications.utils.calculate_week", fake_calculate_week)

    send_daily_menu_notification()
    expected_body = "test morning snack\ntest menu\ntest afternoon snack"
    expected_payload = {
        "head": f"Menu {school.name}",
        "body": expected_body,
        "icon": "/static/img/notification-bell.png",
        "url": school.get_absolute_url(),
    }
    mock_send_test_notification.assert_called_once_with(
        subscription.subscription_info, expected_payload
    )


@patch("notifications.tasks.send_test_notification")
def test_send_daily_menu_notification_detailed_menu(
    mock_send_test_notification, db, monkeypatch, detailed_school, detailed_subscription
):
    """Test invio notifica giornaliera con menu dettagliato."""
    DetailedMeal.objects.create(
        school=detailed_school,
        day=1,
        week=1,
        season=1,
        first_course="test first",
        second_course="test second",
        side_dish="test side",
        fruit="test fruit",
        snack="test snack",
    )

    def fake_get_current_date():
        return 1, 1

    monkeypatch.setattr("notifications.utils.get_current_date", fake_get_current_date)

    def fake_get_season(school):
        return 1

    monkeypatch.setattr("notifications.utils.get_season", fake_get_season)

    def fake_calculate_week(week, bias):
        return 1

    monkeypatch.setattr("notifications.utils.calculate_week", fake_calculate_week)

    send_daily_menu_notification()
    expected_body = "test first\ntest second\ntest side"
    expected_payload = {
        "head": f"Menu {detailed_school.name}",
        "body": expected_body,
        "icon": "/static/img/notification-bell.png",
        "url": detailed_school.get_absolute_url(),
    }
    mock_send_test_notification.assert_called_once_with(
        detailed_subscription.subscription_info, expected_payload
    )


@patch("notifications.tasks.send_test_notification")
def test_send_daily_menu_notification_annual_menu(
    mock_send_test_notification, db, monkeypatch, annual_school, annual_subscription
):
    """Test invio notifica giornaliera con menu annuale."""
    from datetime import date

    from school_menu.models import AnnualMeal

    AnnualMeal.objects.create(
        school=annual_school,
        date=date.today(),
        menu="test menu",
        snack="test snack",
    )

    send_daily_menu_notification()
    expected_body = "test menu\ntest snack"
    expected_payload = {
        "head": f"Menu {annual_school.name}",
        "body": expected_body,
        "icon": "/static/img/notification-bell.png",
        "url": annual_school.get_absolute_url(),
    }
    mock_send_test_notification.assert_called_once_with(
        annual_subscription.subscription_info, expected_payload
    )


def test_send_daily_menu_notification_no_meal(db, monkeypatch, school, subscription):
    """Test invio notifica giornaliera senza menu."""

    def fake_webpush(*args, **kwargs):
        return None

    monkeypatch.setattr("notifications.tasks.webpush", fake_webpush)

    def fake_get_current_date():
        return 1, 1

    monkeypatch.setattr("notifications.utils.get_current_date", fake_get_current_date)

    def fake_get_season(school):
        return 1

    monkeypatch.setattr("notifications.utils.get_season", fake_get_season)

    def fake_calculate_week(week, bias):
        return 1

    monkeypatch.setattr("notifications.utils.calculate_week", fake_calculate_week)

    send_daily_menu_notification()


def test_schedule_daily_menu_notification(monkeypatch):
    """Test schedulazione notifiche giornaliere."""

    def fake_update_or_create(*args, **kwargs):
        return None

    monkeypatch.setattr(Schedule.objects, "update_or_create", fake_update_or_create)
    schedule_daily_menu_notification()


pytestmark = pytest.mark.django_db


def test_send_test_notification_success_with_string_args(monkeypatch):
    """Test invio notifica di prova con successo."""

    def fake_webpush(*args, **kwargs):
        return None

    monkeypatch.setattr("notifications.tasks.webpush", fake_webpush)
    send_test_notification('{"test": "test"}', '{"test": "test"}')


def test_send_test_notification_success(monkeypatch):
    """Test invio notifica di prova con successo."""

    def fake_webpush(*args, **kwargs):
        return None

    monkeypatch.setattr("notifications.tasks.webpush", fake_webpush)
    send_test_notification({}, {})


def test_send_test_notification_webpush_exception(monkeypatch):
    """Test invio notifica di prova con WebPushException."""

    def fake_webpush(*args, **kwargs):
        raise WebPushException("test")

    monkeypatch.setattr("notifications.tasks.webpush", fake_webpush)
    with pytest.raises(WebPushException):
        send_test_notification({}, {})


def test_send_test_notification_generic_exception(monkeypatch):
    """Test invio notifica di prova con eccezione generica."""

    def fake_webpush(*args, **kwargs):
        raise ValueError("test")

    monkeypatch.setattr("notifications.tasks.webpush", fake_webpush)
    with pytest.raises(ValueError):
        send_test_notification({}, {})
