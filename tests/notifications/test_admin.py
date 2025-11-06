from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from notifications.admin import BroadcastNotificationAdmin
from notifications.models import BroadcastNotification
from tests.notifications.factories import BroadcastNotificationFactory
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def broadcast_admin(admin_site):
    return BroadcastNotificationAdmin(BroadcastNotification, admin_site)


@pytest.fixture
def admin_request():
    """Create a mock admin request with a superuser."""
    factory = RequestFactory()
    request = factory.get("/admin/")
    request.user = UserFactory(is_staff=True, is_superuser=True)
    # Add session and messages support
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


class TestBroadcastNotificationAdmin:
    def test_list_display_fields(self, broadcast_admin):
        """Test that list_display includes all expected fields."""
        expected_fields = [
            "title",
            "created_at",
            "sent_at",
            "status",
            "recipients_count",
            "success_count",
            "failure_count",
        ]
        assert broadcast_admin.list_display == expected_fields

    def test_list_filter_fields(self, broadcast_admin):
        """Test that list_filter includes expected fields."""
        assert "status" in broadcast_admin.list_filter
        assert "created_at" in broadcast_admin.list_filter
        assert "sent_at" in broadcast_admin.list_filter

    def test_filter_horizontal(self, broadcast_admin):
        """Test that target_schools uses filter_horizontal."""
        assert "target_schools" in broadcast_admin.filter_horizontal

    def test_readonly_fields(self, broadcast_admin):
        """Test that metadata fields are readonly."""
        readonly = broadcast_admin.readonly_fields
        assert "created_by" in readonly
        assert "created_at" in readonly
        assert "sent_at" in readonly
        assert "recipients_count" in readonly
        assert "success_count" in readonly
        assert "failure_count" in readonly
        assert "status" in readonly

    def test_fieldsets_structure(self, broadcast_admin):
        """Test that fieldsets are properly configured."""
        fieldsets = broadcast_admin.fieldsets
        assert len(fieldsets) == 3
        assert fieldsets[0][0] == "Notification Content"
        assert fieldsets[1][0] == "Recipients"
        assert fieldsets[2][0] == "Status"

    def test_save_model_new_object(self, broadcast_admin, admin_request):
        """Test that save_model sets created_by for new objects."""
        broadcast = BroadcastNotification(title="Test", message="Test message")
        broadcast_admin.save_model(admin_request, broadcast, None, change=False)

        assert broadcast.created_by == admin_request.user
        assert broadcast.status == BroadcastNotification.Status.DRAFT

    def test_save_model_existing_object(self, broadcast_admin, admin_request):
        """Test that save_model doesn't modify created_by for existing objects."""
        original_user = UserFactory()
        broadcast = BroadcastNotificationFactory(created_by=original_user)
        original_created_by = broadcast.created_by

        broadcast_admin.save_model(admin_request, broadcast, None, change=True)

        broadcast.refresh_from_db()
        assert broadcast.created_by == original_created_by

    def test_send_broadcast_action_exists(self, broadcast_admin):
        """Test that send_broadcast action is registered."""
        assert "send_broadcast" in broadcast_admin.actions

    @patch("notifications.admin.async_task")
    def test_send_broadcast_action(
        self, mock_async_task, broadcast_admin, admin_request
    ):
        """Test send_broadcast action triggers async task."""
        broadcast1 = BroadcastNotificationFactory(
            status=BroadcastNotification.Status.DRAFT
        )
        broadcast2 = BroadcastNotificationFactory(
            status=BroadcastNotification.Status.DRAFT
        )
        queryset = BroadcastNotification.objects.filter(
            pk__in=[broadcast1.pk, broadcast2.pk]
        )

        broadcast_admin.send_broadcast(admin_request, queryset)

        assert mock_async_task.call_count == 2
        broadcast1.refresh_from_db()
        broadcast2.refresh_from_db()
        assert broadcast1.status == BroadcastNotification.Status.SENDING
        assert broadcast2.status == BroadcastNotification.Status.SENDING

    @patch("notifications.admin.async_task")
    def test_send_broadcast_action_skips_already_sent(
        self, mock_async_task, broadcast_admin, admin_request
    ):
        """Test send_broadcast action skips already sent broadcasts."""
        broadcast1 = BroadcastNotificationFactory(
            status=BroadcastNotification.Status.SENT
        )
        broadcast2 = BroadcastNotificationFactory(
            status=BroadcastNotification.Status.DRAFT
        )
        queryset = BroadcastNotification.objects.filter(
            pk__in=[broadcast1.pk, broadcast2.pk]
        )

        broadcast_admin.send_broadcast(admin_request, queryset)

        assert mock_async_task.call_count == 1
        mock_async_task.assert_called_with(
            "notifications.tasks.send_broadcast_notification", broadcast2.pk
        )

    def test_send_broadcast_action_description(self, broadcast_admin):
        """Test send_broadcast action has correct description."""
        action = broadcast_admin.send_broadcast
        assert hasattr(action, "short_description")
        assert action.short_description == "Send selected broadcasts"

    @patch("notifications.admin.async_task")
    def test_send_broadcast_action_all_already_sent(
        self, mock_async_task, broadcast_admin, admin_request
    ):
        """Test send_broadcast action when all broadcasts are already sent."""
        broadcast1 = BroadcastNotificationFactory(
            status=BroadcastNotification.Status.SENT
        )
        broadcast2 = BroadcastNotificationFactory(
            status=BroadcastNotification.Status.SENT
        )
        queryset = BroadcastNotification.objects.filter(
            pk__in=[broadcast1.pk, broadcast2.pk]
        )

        broadcast_admin.send_broadcast(admin_request, queryset)

        mock_async_task.assert_not_called()

    @patch("notifications.admin.async_task")
    def test_send_broadcast_action_skips_sending_status(
        self, mock_async_task, broadcast_admin, admin_request
    ):
        """Test send_broadcast action skips broadcasts with SENDING status."""
        broadcast1 = BroadcastNotificationFactory(
            status=BroadcastNotification.Status.SENDING
        )
        broadcast2 = BroadcastNotificationFactory(
            status=BroadcastNotification.Status.DRAFT
        )
        queryset = BroadcastNotification.objects.filter(
            pk__in=[broadcast1.pk, broadcast2.pk]
        )

        broadcast_admin.send_broadcast(admin_request, queryset)

        assert mock_async_task.call_count == 1
        mock_async_task.assert_called_with(
            "notifications.tasks.send_broadcast_notification", broadcast2.pk
        )
