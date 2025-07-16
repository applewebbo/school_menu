from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test import TestCase


@pytest.mark.django_db
class ScheduleNotificationsTest(TestCase):
    @patch("notifications.tasks.schedule_daily_menu_notification")
    def test_command_calls_schedule_daily_menu_notification(
        self, mock_schedule_daily_menu_notification
    ):
        call_command("schedule_notifications")
        mock_schedule_daily_menu_notification.assert_called_once()
