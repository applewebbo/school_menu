from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from pywebpush import WebPushException

from notifications.models import AnonymousMenuNotification
from notifications.tasks import (
    _send_menu_notifications,
    send_previous_day_6pm_menu_notification,
    send_same_day_6pm_menu_notification,
    send_same_day_9am_menu_notification,
    send_same_day_12pm_menu_notification,
    send_test_notification,
)
from tests.notifications.factories import AnonymousMenuNotificationFactory
from tests.school_menu.factories import SchoolFactory

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


@patch("notifications.tasks.build_menu_notification_payload")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_sends_to_correct_time(
    mock_send_test_notification, mock_build_payload, school, subscription_same_day_9am
):
    """Test that notifications are sent only to users subscribed to a specific time."""
    # Create another subscription for a different time that should not be called
    AnonymousMenuNotificationFactory(
        school=school,
        daily_notification=True,
        notification_time=AnonymousMenuNotification.SAME_DAY_12PM,
    )
    mock_build_payload.return_value = {"head": "Test", "body": "Test body"}

    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)

    mock_send_test_notification.assert_called_once()
    args, _ = mock_send_test_notification.call_args
    assert args[0] == subscription_same_day_9am.subscription_info


@patch("notifications.tasks.build_menu_notification_payload")
@patch("notifications.tasks.send_test_notification")
def test_send_menu_notifications_no_payload(
    mock_send_test_notification, mock_build_payload, subscription_same_day_9am
):
    """Test that no notification is sent if payload is None."""
    mock_build_payload.return_value = None
    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)
    mock_send_test_notification.assert_not_called()


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


@patch("notifications.tasks.webpush")
@patch("notifications.tasks.build_menu_notification_payload")
def test_expired_subscription_is_deleted(
    mock_build_payload, mock_webpush, subscription_same_day_9am
):
    """Test that an expired subscription is deleted after a WebPushException."""
    mock_build_payload.return_value = {"head": "Test", "body": "Test body"}
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
def test_send_test_notification_generic_exception_logs_error(mock_webpush, mock_logger):
    """Test that a generic Exception logs an error."""
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
