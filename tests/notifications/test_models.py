import pytest

from notifications.models import AnonymousMenuNotification

pytestmark = pytest.mark.django_db


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

    def test_meta_options(self):
        """
        Test Meta options di AnonymousMenuNotification.
        """
        meta = AnonymousMenuNotification._meta
        assert meta.verbose_name == "Anonymous Menu Notification"
        assert meta.verbose_name_plural == "Anonymous Menu Notifications"
        assert meta.ordering == ["-created_at"]
