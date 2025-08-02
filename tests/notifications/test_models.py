import pytest

from notifications.models import AnonymousMenuNotification, DailyNotification
from tests.school_menu.factories import SchoolFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def school_factory():
    return SchoolFactory


class TestAnonymousMenuNotificationModel:
    def test_create_and_str(self, school_factory):
        """
        Test creazione e __str__ di AnonymousMenuNotification.
        """
        school = school_factory(name="Test School")
        subscription_info = {
            "endpoint": "https://example.com",
            "keys": {"auth": "abc", "p256dh": "def"},
        }
        notification = AnonymousMenuNotification.objects.create(
            school=school, subscription_info=subscription_info
        )
        created_at = notification.created_at
        expected_str = f"Anonymous subscription for {school} at {created_at}"
        assert str(notification) == expected_str

    def test_default_notification_time(self, school_factory):
        """Test that the default notification time is set correctly."""
        school = school_factory(name="Test School")
        subscription_info = {
            "endpoint": "https://example.com",
            "keys": {"auth": "abc", "p256dh": "def"},
        }
        notification = AnonymousMenuNotification.objects.create(
            school=school, subscription_info=subscription_info
        )
        assert notification.notification_time == AnonymousMenuNotification.SAME_DAY_12PM

    def test_meta_options(self):
        """
        Test Meta options di AnonymousMenuNotification.
        """
        meta = AnonymousMenuNotification._meta
        assert meta.verbose_name == "Anonymous Menu Notification"
        assert meta.verbose_name_plural == "Anonymous Menu Notifications"
        assert meta.ordering == ["-created_at"]


class TestDailyNotificationModel:
    def test_create_and_str(self, school_factory):
        """
        Test creazione e __str__ di DailyNotification.
        """
        school = school_factory(name="Test School")
        notification = DailyNotification.objects.create(school=school)
        created_at = notification.created_at
        expected_str = f"Daily notification for {school} at {created_at}"
        assert str(notification) == expected_str
