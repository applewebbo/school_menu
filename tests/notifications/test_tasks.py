from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import time_machine
from django.contrib.auth import get_user_model
from pywebpush import WebPushException

from notifications.models import AnonymousMenuNotification, BroadcastNotification
from notifications.tasks import (
    _has_menu_for_date,
    _is_school_in_session,
    _send_menu_notifications,
    send_broadcast_notification,
    send_previous_day_6pm_menu_notification,
    send_same_day_6pm_menu_notification,
    send_same_day_9am_menu_notification,
    send_same_day_12pm_menu_notification,
    send_test_notification,
)
from school_menu.models import School
from tests.notifications.factories import (
    AnonymousMenuNotificationFactory,
    BroadcastNotificationFactory,
)
from tests.school_menu.factories import (
    AnnualMealFactory,
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def school_in_session():
    """
    Creates a school that is currently in session with a simple menu type.
    """
    today = date(2025, 8, 18)  # A Monday
    start_month = (today.month - 1) if today.month > 1 else 12
    end_month = (today.month + 1) if today.month < 12 else 1
    school = SchoolFactory(
        start_month=start_month, end_month=end_month, menu_type=School.Types.SIMPLE
    )
    return school


@pytest.fixture
def school_not_in_session():
    """
    Creates a school that is currently not in session with a simple menu type.
    """
    today = date(2025, 8, 18)  # A Monday
    start_month = (today.month + 1) if today.month < 12 else 1
    end_month = (today.month + 2) if today.month < 11 else 1
    school = SchoolFactory(
        start_month=start_month, end_month=end_month, menu_type=School.Types.SIMPLE
    )
    return school


def create_simple_meals_for_all_seasons_and_weeks(school, day):
    """Helper function to create SimpleMeal for all seasons and weeks."""
    for season in School.Seasons.values:
        for week in range(1, 5):  # Weeks 1 to 4
            SimpleMealFactory(school=school, day=day, season=season, week=week)


@time_machine.travel("2025-08-18")  # A Monday
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_sends_to_correct_time(
    mock_send_test_notification, school_in_session
):
    """
    Test that notifications are sent only to users subscribed to a specific time.
    """
    subscription_9am = AnonymousMenuNotificationFactory(
        school=school_in_session,
        daily_notification=True,
        notification_time=AnonymousMenuNotification.SAME_DAY_9AM,
    )
    AnonymousMenuNotificationFactory(
        school=school_in_session,
        daily_notification=True,
        notification_time=AnonymousMenuNotification.SAME_DAY_12PM,
    )
    create_simple_meals_for_all_seasons_and_weeks(
        school_in_session, date.today().weekday() + 1
    )

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_test_notification.assert_called_once()
    args, _ = mock_send_test_notification.call_args
    assert args[0] == subscription_9am.subscription_info


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


@time_machine.travel("2025-08-18")  # A Monday
@patch("notifications.tasks.webpush")
def test_expired_subscription_is_deleted(mock_webpush, school_in_session):
    """Test that an expired subscription is deleted after a WebPushException."""
    subscription = AnonymousMenuNotificationFactory(
        school=school_in_session,
        daily_notification=True,
        notification_time=AnonymousMenuNotification.SAME_DAY_9AM,
    )
    create_simple_meals_for_all_seasons_and_weeks(
        school_in_session, date.today().weekday() + 1
    )

    mock_response = MagicMock()
    mock_response.status_code = 410
    mock_webpush.side_effect = WebPushException(
        "Subscription expired", response=mock_response
    )

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    assert not AnonymousMenuNotification.objects.filter(id=subscription.id).exists()


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

    with pytest.raises(Exception, match=error_message):
        send_test_notification({}, {})

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
    def test_with_annual_meal(self, school_in_session):
        """Test that it returns True if an AnnualMeal exists."""
        target_date = date(2025, 8, 2)
        AnnualMealFactory(school=school_in_session, date=target_date, is_active=True)
        assert _has_menu_for_date(school_in_session, target_date) is True

    def test_weekend_without_annual_meal(self, school_in_session):
        """Test that it returns False on a weekend if no AnnualMeal exists."""
        target_date = date(2025, 8, 3)
        assert _has_menu_for_date(school_in_session, target_date) is False

    def test_weekday_with_simple_meal(self, school_in_session):
        """Test that it returns True on a weekday with a SimpleMeal."""
        target_date = date(2025, 8, 4)
        SimpleMealFactory(school=school_in_session, day=1)
        assert _has_menu_for_date(school_in_session, target_date) is True

    def test_weekday_with_detailed_meal(self, school_in_session):
        """Test that it returns True on a weekday with a DetailedMeal."""
        school_in_session.menu_type = "D"
        school_in_session.save()
        target_date = date(2025, 8, 5)
        DetailedMealFactory(school=school_in_session, day=2)
        assert _has_menu_for_date(school_in_session, target_date) is True

    def test_weekday_without_meal(self, school_in_session):
        """Test that it returns False on a weekday if no meal exists."""
        target_date = date(2025, 8, 6)
        assert _has_menu_for_date(school_in_session, target_date) is False


@time_machine.travel("2025-08-18")  # A Monday
@patch("notifications.tasks.settings")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_school_not_in_session(
    mock_send_notification, mock_settings, school_not_in_session
):
    """Test that notifications are not sent if the school is not in session."""
    mock_settings.ENABLE_SCHOOL_DATE_CHECK = True
    AnonymousMenuNotificationFactory(
        school=school_not_in_session,
        notification_time=AnonymousMenuNotification.SAME_DAY_9AM,
    )

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_notification.assert_not_called()


@time_machine.travel("2025-08-18")  # A Monday
@patch("notifications.tasks.settings")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_school_in_session(
    mock_send_notification, mock_settings, school_in_session
):
    """Test that notifications are sent if the school is in session."""
    mock_settings.ENABLE_SCHOOL_DATE_CHECK = True
    AnonymousMenuNotificationFactory(
        school=school_in_session,
        notification_time=AnonymousMenuNotification.SAME_DAY_9AM,
    )
    create_simple_meals_for_all_seasons_and_weeks(
        school_in_session, date.today().weekday() + 1
    )

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_notification.assert_called_once()


class TestIsSchoolInSession:
    def test_school_year_within_same_calendar_year(self):
        """
        Test _is_school_in_session for a school year within the same calendar year.
        """
        school = SchoolFactory(start_month=2, start_day=1, end_month=6, end_day=30)
        assert not _is_school_in_session(school, date(2025, 1, 15))
        assert _is_school_in_session(school, date(2025, 4, 15))
        assert not _is_school_in_session(school, date(2025, 7, 15))

    def test_school_year_spanning_calendar_years(self):
        """
        Test _is_school_in_session for a school year spanning calendar years.
        """
        school = SchoolFactory(start_month=9, start_day=1, end_month=6, end_day=30)
        assert _is_school_in_session(school, date(2025, 10, 15))
        assert _is_school_in_session(school, date(2026, 3, 15))
        assert not _is_school_in_session(school, date(2025, 8, 15))


@time_machine.travel("2025-08-18")  # A Monday
@patch("notifications.tasks.settings")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_check_disabled(
    mock_send_notification, mock_settings, school_not_in_session
):
    """Test that the school session check is skipped if disabled."""
    mock_settings.ENABLE_SCHOOL_DATE_CHECK = False
    AnonymousMenuNotificationFactory(
        school=school_not_in_session,
        notification_time=AnonymousMenuNotification.SAME_DAY_9AM,
    )
    create_simple_meals_for_all_seasons_and_weeks(
        school_not_in_session, date.today().weekday() + 1
    )

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_notification.assert_called_once()


class TestSendBroadcastNotification:
    @patch("notifications.tasks.send_test_notification")
    def test_send_to_all_subscriptions(self, mock_send_test):
        """Test broadcast sends to all subscriptions with daily_notification=True."""
        school1 = SchoolFactory()
        school2 = SchoolFactory()
        AnonymousMenuNotificationFactory(school=school1, daily_notification=True)
        AnonymousMenuNotificationFactory(school=school2, daily_notification=True)
        AnonymousMenuNotificationFactory(school=school1, daily_notification=False)

        broadcast = BroadcastNotificationFactory(
            title="Test Broadcast", message="Test message", url="https://example.com"
        )

        send_broadcast_notification(broadcast.pk)

        assert mock_send_test.call_count == 2
        broadcast.refresh_from_db()
        assert broadcast.status == BroadcastNotification.Status.SENT
        assert broadcast.recipients_count == 2
        assert broadcast.success_count == 2
        assert broadcast.failure_count == 0
        assert broadcast.sent_at is not None

    @patch("notifications.tasks.send_test_notification")
    def test_filter_by_target_schools(self, mock_send_test):
        """Test broadcast filters by target schools."""
        school1 = SchoolFactory()
        school2 = SchoolFactory()
        school3 = SchoolFactory()
        AnonymousMenuNotificationFactory(school=school1, daily_notification=True)
        AnonymousMenuNotificationFactory(school=school2, daily_notification=True)
        AnonymousMenuNotificationFactory(school=school3, daily_notification=True)

        broadcast = BroadcastNotificationFactory()
        broadcast.target_schools.add(school1, school2)

        send_broadcast_notification(broadcast.pk)

        assert mock_send_test.call_count == 2
        broadcast.refresh_from_db()
        assert broadcast.recipients_count == 2
        assert broadcast.success_count == 2

    @patch("notifications.tasks.send_test_notification")
    def test_respects_daily_notification_flag(self, mock_send_test):
        """Test broadcast respects daily_notification=False."""
        school = SchoolFactory()
        AnonymousMenuNotificationFactory(school=school, daily_notification=True)
        AnonymousMenuNotificationFactory(school=school, daily_notification=False)
        AnonymousMenuNotificationFactory(school=school, daily_notification=False)

        broadcast = BroadcastNotificationFactory()

        send_broadcast_notification(broadcast.pk)

        assert mock_send_test.call_count == 1
        broadcast.refresh_from_db()
        assert broadcast.recipients_count == 1

    @patch("notifications.tasks.send_test_notification")
    def test_payload_with_url(self, mock_send_test):
        """Test broadcast payload includes URL when provided."""
        school = SchoolFactory()
        AnonymousMenuNotificationFactory(school=school, daily_notification=True)

        broadcast = BroadcastNotificationFactory(
            title="Test", message="Message", url="https://example.com/test"
        )

        send_broadcast_notification(broadcast.pk)

        mock_send_test.assert_called_once()
        args, _ = mock_send_test.call_args
        payload = args[1]
        assert payload["head"] == "Test"
        assert payload["body"] == "Message"
        assert payload["url"] == "https://example.com/test"
        assert payload["icon"] == "/static/img/notification-bell.png"

    @patch("notifications.tasks.send_test_notification")
    def test_payload_without_url(self, mock_send_test):
        """Test broadcast payload defaults to / when URL is empty."""
        school = SchoolFactory()
        AnonymousMenuNotificationFactory(school=school, daily_notification=True)

        broadcast = BroadcastNotificationFactory(
            title="Test", message="Message", url=""
        )

        send_broadcast_notification(broadcast.pk)

        mock_send_test.assert_called_once()
        args, _ = mock_send_test.call_args
        payload = args[1]
        assert payload["url"] == "/"

    @patch("notifications.tasks.logger")
    @patch("notifications.tasks.send_test_notification")
    def test_handles_send_failures(self, mock_send_test, mock_logger):
        """Test broadcast handles individual send failures."""
        school = SchoolFactory()
        AnonymousMenuNotificationFactory(school=school, daily_notification=True)
        AnonymousMenuNotificationFactory(school=school, daily_notification=True)
        AnonymousMenuNotificationFactory(school=school, daily_notification=True)

        mock_send_test.side_effect = [None, Exception("Send failed"), None]

        broadcast = BroadcastNotificationFactory()

        send_broadcast_notification(broadcast.pk)

        assert mock_send_test.call_count == 3
        broadcast.refresh_from_db()
        assert broadcast.status == BroadcastNotification.Status.SENT
        assert broadcast.recipients_count == 3
        assert broadcast.success_count == 2
        assert broadcast.failure_count == 1
        mock_logger.error.assert_called_once()

    @patch("notifications.tasks.send_test_notification")
    def test_no_subscriptions(self, mock_send_test):
        """Test broadcast with no matching subscriptions."""
        broadcast = BroadcastNotificationFactory()

        send_broadcast_notification(broadcast.pk)

        mock_send_test.assert_not_called()
        broadcast.refresh_from_db()
        assert broadcast.status == BroadcastNotification.Status.SENT
        assert broadcast.recipients_count == 0
        assert broadcast.success_count == 0
        assert broadcast.failure_count == 0

    @patch("notifications.tasks.logger")
    @patch("notifications.tasks.send_test_notification")
    def test_logs_completion(self, mock_send_test, mock_logger):
        """Test broadcast logs completion message."""
        school = SchoolFactory()
        AnonymousMenuNotificationFactory(school=school, daily_notification=True)

        broadcast = BroadcastNotificationFactory(title="Test Broadcast")

        send_broadcast_notification(broadcast.pk)

        mock_logger.info.assert_called_with(
            "Broadcast 'Test Broadcast' sent: 1 success, 0 failures"
        )
