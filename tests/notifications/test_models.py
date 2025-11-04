import pytest

from notifications.models import (
    AnonymousMenuNotification,
    BroadcastNotification,
    DailyNotification,
)
from tests.notifications.factories import BroadcastNotificationFactory
from tests.school_menu.factories import SchoolFactory
from tests.users.factories import UserFactory

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

    def test_hash_endpoint(self):
        """Test that hash_endpoint generates consistent SHA256 hashes."""
        endpoint1 = "https://example.com/push/endpoint1"
        endpoint2 = "https://example.com/push/endpoint2"

        hash1 = AnonymousMenuNotification.hash_endpoint(endpoint1)
        hash2 = AnonymousMenuNotification.hash_endpoint(endpoint2)

        # Hashes should be 64 characters (SHA256 hex)
        assert len(hash1) == 64
        assert len(hash2) == 64

        # Same input should produce same hash
        assert hash1 == AnonymousMenuNotification.hash_endpoint(endpoint1)

        # Different inputs should produce different hashes
        assert hash1 != hash2

    def test_extract_endpoint_from_dict(self):
        """Test that extract_endpoint correctly extracts from dict."""
        subscription_info = {
            "endpoint": "https://example.com/push/test",
            "keys": {"auth": "abc", "p256dh": "def"},
        }
        endpoint = AnonymousMenuNotification.extract_endpoint(subscription_info)
        assert endpoint == "https://example.com/push/test"

    def test_extract_endpoint_from_dict_without_endpoint(self):
        """Test that extract_endpoint returns empty string if no endpoint."""
        subscription_info = {"keys": {"auth": "abc", "p256dh": "def"}}
        endpoint = AnonymousMenuNotification.extract_endpoint(subscription_info)
        assert endpoint == ""

    def test_extract_endpoint_from_non_dict(self):
        """Test that extract_endpoint handles non-dict input gracefully."""
        endpoint = AnonymousMenuNotification.extract_endpoint("not a dict")
        assert endpoint == ""

        endpoint = AnonymousMenuNotification.extract_endpoint(None)
        assert endpoint == ""

    def test_save_auto_populates_subscription_endpoint(self, school_factory):
        """Test that save() automatically populates subscription_endpoint."""
        school = school_factory()
        subscription_info = {
            "endpoint": "https://example.com/push/auto-test",
            "keys": {"auth": "abc", "p256dh": "def"},
        }

        notification = AnonymousMenuNotification(
            school=school, subscription_info=subscription_info
        )
        # subscription_endpoint should be empty before save
        assert not notification.subscription_endpoint

        notification.save()

        # After save, subscription_endpoint should be populated
        assert notification.subscription_endpoint
        assert len(notification.subscription_endpoint) == 64

        # Should match the hash of the endpoint
        expected_hash = AnonymousMenuNotification.hash_endpoint(
            "https://example.com/push/auto-test"
        )
        assert notification.subscription_endpoint == expected_hash

    def test_save_doesnt_overwrite_existing_subscription_endpoint(self, school_factory):
        """Test that save() doesn't overwrite an existing subscription_endpoint."""
        school = school_factory()
        subscription_info = {
            "endpoint": "https://example.com/push/test",
            "keys": {"auth": "abc", "p256dh": "def"},
        }

        # Manually set a subscription_endpoint
        custom_hash = "custom_hash_value_123"
        notification = AnonymousMenuNotification(
            school=school,
            subscription_info=subscription_info,
            subscription_endpoint=custom_hash,
        )
        notification.save()

        # Should keep the custom hash, not overwrite it
        assert notification.subscription_endpoint == custom_hash

    def test_unique_constraint_on_subscription_endpoint(self, school_factory):
        """Test that subscription_endpoint has a unique constraint."""
        school = school_factory()
        subscription_info = {
            "endpoint": "https://example.com/push/unique-test",
            "keys": {"auth": "abc", "p256dh": "def"},
        }

        # Create first notification
        AnonymousMenuNotification.objects.create(
            school=school, subscription_info=subscription_info
        )

        # Try to create second notification with same endpoint
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            notification2 = AnonymousMenuNotification(
                school=school, subscription_info=subscription_info
            )
            notification2.save()


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


class TestBroadcastNotificationModel:
    def test_create_and_str(self):
        """Test creation and __str__ of BroadcastNotification."""
        user = UserFactory()
        broadcast = BroadcastNotification.objects.create(
            title="Test Broadcast",
            message="Test message",
            url="https://example.com",
            created_by=user,
        )
        expected_str = (
            f"{broadcast.title} - {broadcast.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
        assert str(broadcast) == expected_str

    def test_default_status(self):
        """Test that default status is DRAFT."""
        broadcast = BroadcastNotificationFactory()
        assert broadcast.status == BroadcastNotification.Status.DRAFT

    def test_status_choices(self):
        """Test that all status choices exist."""
        assert BroadcastNotification.Status.DRAFT == "draft"
        assert BroadcastNotification.Status.SENDING == "sending"
        assert BroadcastNotification.Status.SENT == "sent"
        assert BroadcastNotification.Status.FAILED == "failed"

    def test_optional_url(self):
        """Test that URL is optional."""
        broadcast = BroadcastNotification.objects.create(
            title="Test", message="Test message"
        )
        assert broadcast.url == ""

    def test_target_schools_many_to_many(self):
        """Test that target_schools can have multiple schools."""
        broadcast = BroadcastNotificationFactory()
        school1 = SchoolFactory()
        school2 = SchoolFactory()
        broadcast.target_schools.add(school1, school2)
        assert broadcast.target_schools.count() == 2
        assert school1 in broadcast.target_schools.all()
        assert school2 in broadcast.target_schools.all()

    def test_empty_target_schools(self):
        """Test that target_schools can be empty."""
        broadcast = BroadcastNotificationFactory()
        assert broadcast.target_schools.count() == 0

    def test_meta_options(self):
        """Test Meta options of BroadcastNotification."""
        meta = BroadcastNotification._meta
        assert meta.verbose_name == "Broadcast Notification"
        assert meta.verbose_name_plural == "Broadcast Notifications"
        assert meta.ordering == ["-created_at"]

    def test_default_counts_are_zero(self):
        """Test that default counts are zero."""
        broadcast = BroadcastNotificationFactory()
        assert broadcast.recipients_count == 0
        assert broadcast.success_count == 0
        assert broadcast.failure_count == 0

    def test_sent_at_null_by_default(self):
        """Test that sent_at is null by default."""
        broadcast = BroadcastNotificationFactory()
        assert broadcast.sent_at is None

    def test_created_by_can_be_null(self):
        """Test that created_by can be null (SET_NULL on delete)."""
        user = UserFactory()
        broadcast = BroadcastNotification.objects.create(
            title="Test", message="Test message", created_by=user
        )
        user.delete()
        broadcast.refresh_from_db()
        assert broadcast.created_by is None
