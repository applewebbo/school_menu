from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from pywebpush import WebPushException

from notifications.models import AnonymousMenuNotification
from notifications.tasks import (
    _has_menu_for_date,
    _is_school_in_session,
    _send_menu_notifications,
    send_previous_day_6pm_menu_notification,
    send_same_day_6pm_menu_notification,
    send_same_day_9am_menu_notification,
    send_same_day_12pm_menu_notification,
    send_test_notification,
)
from tests.notifications.factories import AnonymousMenuNotificationFactory
from tests.school_menu.factories import (
    AnnualMealFactory,
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def school():
    return SchoolFactory()


@pytest.fixture
def subscription_previous_day(school):
    return AnonymousMenuNotificationFactory(
        school=school,
        daily_notification=True,
        notification_time=AnonymousMenuNotification.PREVIOUS_DAY_6PM,
    )


@pytest.fixture
def subscription_same_day_9am(school):
    return AnonymousMenuNotificationFactory(
        school=school,
        daily_notification=True,
        notification_time=AnonymousMenuNotification.SAME_DAY_9AM,
    )


@patch("notifications.tasks._is_school_in_session")
@patch("notifications.tasks._has_menu_for_date")
@patch("notifications.tasks.build_menu_notification_payload")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_sends_to_correct_time(
    mock_send_test_notification,
    mock_build_payload,
    mock_has_menu,
    mock_is_school_in_session,
    school,
    subscription_same_day_9am,
):
    """Test that notifications are sent only to users subscribed to a specific time."""
    # Create another subscription for a different time that should not be called
    AnonymousMenuNotificationFactory(
        school=school,
        daily_notification=True,
        notification_time=AnonymousMenuNotification.SAME_DAY_12PM,
    )
    mock_build_payload.return_value = {"head": "Test", "body": "Test body"}
    mock_has_menu.return_value = True
    mock_is_school_in_session.return_value = True

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_test_notification.assert_called_once()
    args, _ = mock_send_test_notification.call_args
    assert args[0] == subscription_same_day_9am.subscription_info


@patch("notifications.tasks.logger")
@patch("notifications.tasks._is_school_in_session")
@patch("notifications.tasks._has_menu_for_date")
@patch("notifications.tasks.build_menu_notification_payload")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_no_payload(
    mock_send_test_notification,
    mock_build_payload,
    mock_has_menu,
    mock_is_school_in_session,
    mock_logger,
    subscription_same_day_9am,
):
    """Test that no notification is sent if payload is None."""
    mock_has_menu.return_value = True  # Ensure we pass the date check
    mock_is_school_in_session.return_value = True
    mock_build_payload.return_value = None
    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)
    mock_send_test_notification.assert_not_called()
    mock_logger.info.assert_any_call(
        f"Nessun menu trovato per la scuola {subscription_same_day_9am.school.name}, notifiche non inviate."
    )


@patch("notifications.tasks._send_menu_notifications")
def test_specific_time_tasks_call_helper(mock_send_menu_notifications):
    """Test that specific time tasks call the main helper function."""
    send_previous_day_6pm_menu_notification()
    mock_send_menu_notifications.assert_called_with(
        AnonymousMenuNotification.PREVIOUS_DAY_6PM
    )

    send_same_day_9am_menu_notification()
    mock_send_menu_notifications.assert_called_with(
        AnonymousMenuNotification.SAME_DAY_9AM
    )

    send_same_day_12pm_menu_notification()
    mock_send_menu_notifications.assert_called_with(
        AnonymousMenuNotification.SAME_DAY_12PM
    )

    send_same_day_6pm_menu_notification()
    mock_send_menu_notifications.assert_called_with(
        AnonymousMenuNotification.SAME_DAY_6PM
    )


@patch("notifications.tasks._is_school_in_session")
@patch("notifications.tasks._has_menu_for_date")
@patch("notifications.tasks.webpush")
@patch("notifications.tasks.build_menu_notification_payload")
def test_expired_subscription_is_deleted(
    mock_build_payload,
    mock_webpush,
    mock_has_menu,
    mock_is_school_in_session,
    subscription_same_day_9am,
):
    """Test that an expired subscription is deleted after a WebPushException."""
    mock_build_payload.return_value = {"head": "Test", "body": "Test body"}
    mock_has_menu.return_value = True
    mock_is_school_in_session.return_value = True
    mock_response = MagicMock()
    mock_response.status_code = 410  # Gone
    mock_webpush.side_effect = WebPushException(
        "Subscription expired", response=mock_response
    )

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    assert not AnonymousMenuNotification.objects.filter(
        id=subscription_same_day_9am.id
    ).exists()


# ... (omitting unchanged parts of the file for brevity)


@patch("notifications.tasks.logger")
@patch("notifications.tasks.webpush")
def test_send_test_notification_webpush_exception_logs_error(mock_webpush, mock_logger):
    """Test that WebPushException with other status codes logs an error."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_webpush.side_effect = WebPushException("Test error", response=mock_response)

    with pytest.raises(WebPushException):
        send_test_notification({}, {})

    mock_logger.error.assert_called_once()


@patch("notifications.tasks.logger")
@patch("notifications.tasks.webpush")
def test_send_test_notification_generic_exception_logs_error_and_raises(
    mock_webpush, mock_logger
):
    """Test that a generic Exception logs an error and is re-raised."""
    error_message = "Generic test error"
    mock_webpush.side_effect = Exception(error_message)

    try:
        send_test_notification({}, {})
    except Exception as e:
        assert str(e) == error_message

    mock_logger.error.assert_called_once_with(
        f"Errore inatteso durante l'invio della notifica: {error_message}"
    )


@patch("notifications.tasks.logger")
@patch("notifications.tasks.webpush")
def test_send_test_notification_success(mock_webpush, mock_logger):
    """Test that a successful notification logs info messages."""
    send_test_notification({}, {})
    mock_webpush.assert_called_once()
    assert mock_logger.info.call_count == 2


class TestHasMenuForDate:
    def test_with_annual_meal(self, school):
        """Test that it returns True if an AnnualMeal exists."""
        target_date = date(2025, 8, 2)  # A Saturday
        AnnualMealFactory(school=school, date=target_date, is_active=True)
        assert _has_menu_for_date(school, target_date) is True

    def test_weekend_without_annual_meal(self, school):
        """Test that it returns False on a weekend if no AnnualMeal exists."""
        target_date = date(2025, 8, 3)  # A Sunday
        assert _has_menu_for_date(school, target_date) is False

    def test_weekday_with_simple_meal(self, school):
        """Test that it returns True on a weekday with a SimpleMeal."""
        school.menu_type = "S"
        school.save()
        target_date = date(2025, 8, 4)  # A Monday
        SimpleMealFactory(school=school, day=1)  # Monday
        assert _has_menu_for_date(school, target_date) is True

    def test_weekday_with_detailed_meal(self, school):
        """Test that it returns True on a weekday with a DetailedMeal."""
        school.menu_type = "D"
        school.save()
        target_date = date(2025, 8, 5)  # A Tuesday
        DetailedMealFactory(school=school, day=2)  # Tuesday
        assert _has_menu_for_date(school, target_date) is True

    def test_weekday_without_meal(self, school):
        """Test that it returns False on a weekday if no meal exists."""
        target_date = date(2025, 8, 6)  # A Wednesday
        assert _has_menu_for_date(school, target_date) is False


@patch("notifications.tasks.send_test_notification")
@patch("notifications.tasks.date")
def test_send_menu_notifications_skipped_on_weekend_without_menu(
    mock_date, mock_send_test_notification, subscription_same_day_9am
):
    """Test that notifications are skipped on a weekend if no menu exists."""
    # Set the current date to a Saturday
    mock_date.today.return_value = date(2025, 8, 2)

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_test_notification.assert_not_called()


@patch("notifications.tasks.logger")
@patch("notifications.tasks._is_school_in_session")
@patch("notifications.tasks.send_test_notification")
@patch("notifications.tasks.date")
def test_send_menu_notifications_logs_skip_on_weekend_without_menu(
    mock_date,
    mock_send_test_notification,
    mock_is_school_in_session,
    mock_logger,
    subscription_same_day_9am,
):
    """Test that a log message is created when skipping a weekend notification."""
    # Set the current date to a Saturday
    saturday = date(2025, 8, 2)
    mock_date.today.return_value = saturday
    mock_is_school_in_session.return_value = True  # Mock school in session
    school = subscription_same_day_9am.school

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_test_notification.assert_not_called()
    mock_logger.info.assert_any_call(
        f"Skipping notification for {school.name} on {saturday.strftime('%A')} "
        "as there is no menu."
    )


@patch("notifications.tasks._is_school_in_session")
@patch("notifications.tasks.build_menu_notification_payload")
@patch("notifications.tasks.send_test_notification")
@patch("notifications.tasks.date")
def test_send_menu_notifications_sent_on_weekend_with_menu(
    mock_date,
    mock_send_test_notification,
    mock_build_payload,
    mock_is_school_in_session,
    school,
    subscription_previous_day,
):
    """Test that notifications are sent on a weekend if a menu exists."""
    # Set the current date to a Friday, so the target is Saturday
    saturday = date(2025, 8, 2)
    mock_date.today.return_value = saturday - timedelta(days=1)
    mock_is_school_in_session.return_value = True
    AnnualMealFactory(school=school, date=saturday, is_active=True)
    mock_build_payload.return_value = {"head": "Test", "body": "Test body"}

    _send_menu_notifications(AnonymousMenuNotification.PREVIOUS_DAY_6PM)

    mock_send_test_notification.assert_called_once()


@patch("notifications.tasks.settings")
@patch("notifications.tasks._is_school_in_session")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_school_not_in_session(
    mock_send_notification, mock_is_in_session, mock_settings, subscription_same_day_9am
):
    """Test that notifications are not sent if the school is not in session."""
    mock_settings.ENABLE_SCHOOL_DATE_CHECK = True
    mock_is_in_session.return_value = False

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_notification.assert_not_called()


@patch("notifications.tasks.settings")
@patch("notifications.tasks._is_school_in_session")
@patch("notifications.tasks._has_menu_for_date")
@patch("notifications.tasks.build_menu_notification_payload")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_school_in_session(
    mock_send_notification,
    mock_build_payload,
    mock_has_menu,
    mock_is_in_session,
    mock_settings,
    subscription_same_day_9am,
):
    """Test that notifications are sent if the school is in session."""
    mock_settings.ENABLE_SCHOOL_DATE_CHECK = True
    mock_is_in_session.return_value = True
    mock_has_menu.return_value = True
    mock_build_payload.return_value = {"head": "Test", "body": "Test body"}

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_notification.assert_called_once()


class TestIsSchoolInSession:
    def test_school_year_within_same_calendar_year(self):
        """
        Test _is_school_in_session for a school year within the same calendar year.
        (e.g., February to June)
        """
        school = SchoolFactory(start_month=2, start_day=1, end_month=6, end_day=30)

        # Date before school starts
        assert _is_school_in_session(school, date(2025, 1, 15)) is False

        # Date within school session
        assert _is_school_in_session(school, date(2025, 4, 15)) is True

        # Date after school ends
        assert _is_school_in_session(school, date(2025, 7, 15)) is False

    def test_school_year_spanning_calendar_years(self):
        """
        Test _is_school_in_session for a school year spanning calendar years.
        (e.g., September to June)
        """
        school = SchoolFactory(start_month=9, start_day=1, end_month=6, end_day=30)

        # Date within school session (first part of the year, e.g., October)
        assert _is_school_in_session(school, date(2025, 10, 15)) is True

        # Date within school session (second part of the year, e.g., March)
        assert _is_school_in_session(school, date(2026, 3, 15)) is True

        # Date outside school session (e.g., August)
        assert _is_school_in_session(school, date(2025, 8, 15)) is False


@patch("notifications.tasks.settings")
@patch("notifications.tasks._is_school_in_session")
@patch("notifications.tasks._has_menu_for_date")
@patch("notifications.tasks.build_menu_notification_payload")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_check_disabled(
    mock_send_notification,
    mock_build_payload,
    mock_has_menu,
    mock_is_in_session,
    mock_settings,
    subscription_same_day_9am,
):
    """Test that the school session check is skipped if disabled."""
    mock_settings.ENABLE_SCHOOL_DATE_CHECK = False
    mock_build_payload.return_value = {"head": "Test", "body": "Test body"}
    mock_has_menu.return_value = True

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    # The check should not be performed
    mock_is_in_session.assert_not_called()

    # Notification should be sent because the check is disabled
    mock_send_notification.assert_called_once()
