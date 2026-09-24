from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from notifications.admin import BroadcastNotificationAdmin, NewsletterAdmin
from notifications.models import BroadcastNotification, Newsletter
from tests.notifications.factories import (
    BroadcastNotificationFactory,
    NewsletterFactory,
)
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def broadcast_admin(admin_site):
    return BroadcastNotificationAdmin(BroadcastNotification, admin_site)


@pytest.fixture
def newsletter_admin(admin_site):
    return NewsletterAdmin(Newsletter, admin_site)


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


class TestNewsletterAdmin:
    def test_save_model_new_object(self, newsletter_admin, admin_request):
        newsletter = Newsletter(subject="Test", body_html="<p>Test</p>")
        newsletter_admin.save_model(admin_request, newsletter, None, change=False)

        assert newsletter.created_by == admin_request.user
        assert newsletter.status == Newsletter.Status.DRAFT

    def test_save_model_existing_object(self, newsletter_admin, admin_request):
        original_user = UserFactory()
        newsletter = NewsletterFactory(created_by=original_user)

        newsletter_admin.save_model(admin_request, newsletter, None, change=True)

        newsletter.refresh_from_db()
        assert newsletter.created_by == original_user

    def test_send_newsletter_action_exists(self, newsletter_admin):
        assert "send_newsletter" in newsletter_admin.actions

    @patch("notifications.admin.async_task")
    def test_send_newsletter_action(
        self, mock_async_task, newsletter_admin, admin_request
    ):
        newsletter1 = NewsletterFactory(status=Newsletter.Status.DRAFT)
        newsletter2 = NewsletterFactory(status=Newsletter.Status.DRAFT)
        queryset = Newsletter.objects.filter(pk__in=[newsletter1.pk, newsletter2.pk])

        newsletter_admin.send_newsletter(admin_request, queryset)

        assert mock_async_task.call_count == 2
        newsletter1.refresh_from_db()
        newsletter2.refresh_from_db()
        assert newsletter1.status == Newsletter.Status.SENDING
        assert newsletter2.status == Newsletter.Status.SENDING

    @patch("notifications.admin.async_task")
    def test_send_newsletter_action_skips_already_sent(
        self, mock_async_task, newsletter_admin, admin_request
    ):
        newsletter1 = NewsletterFactory(status=Newsletter.Status.SENT)
        newsletter2 = NewsletterFactory(status=Newsletter.Status.DRAFT)
        queryset = Newsletter.objects.filter(pk__in=[newsletter1.pk, newsletter2.pk])

        newsletter_admin.send_newsletter(admin_request, queryset)

        assert mock_async_task.call_count == 1
        mock_async_task.assert_called_with(
            "notifications.tasks.send_newsletter", newsletter2.pk
        )

    @patch("notifications.admin.async_task")
    def test_send_newsletter_action_all_already_sent(
        self, mock_async_task, newsletter_admin, admin_request
    ):
        newsletter1 = NewsletterFactory(status=Newsletter.Status.SENT)
        newsletter2 = NewsletterFactory(status=Newsletter.Status.SENDING)
        queryset = Newsletter.objects.filter(pk__in=[newsletter1.pk, newsletter2.pk])

        newsletter_admin.send_newsletter(admin_request, queryset)

        mock_async_task.assert_not_called()

    def test_send_newsletter_action_description(self, newsletter_admin):
        action = newsletter_admin.send_newsletter
        assert action.short_description == "Send selected newsletters"

    def test_send_test_to_self_action_exists(self, newsletter_admin):
        assert "send_test_to_self" in newsletter_admin.actions

    def test_send_test_to_self_sends_to_admin_email(
        self, newsletter_admin, admin_request, mailoutbox
    ):
        newsletter = NewsletterFactory(
            subject="Anteprima", body_html="<p>Ciao</p>", status=Newsletter.Status.DRAFT
        )
        queryset = Newsletter.objects.filter(pk=newsletter.pk)

        newsletter_admin.send_test_to_self(admin_request, queryset)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [admin_request.user.email]
        assert mailoutbox[0].subject == "Anteprima"

    def test_send_test_to_self_does_not_touch_status_or_counts(
        self, newsletter_admin, admin_request, mailoutbox
    ):
        newsletter = NewsletterFactory(status=Newsletter.Status.DRAFT)
        queryset = Newsletter.objects.filter(pk=newsletter.pk)

        newsletter_admin.send_test_to_self(admin_request, queryset)

        newsletter.refresh_from_db()
        assert newsletter.status == Newsletter.Status.DRAFT
        assert newsletter.recipients_count == 0
        assert newsletter.sent_at is None

    def test_send_test_to_self_uses_a_placeholder_unsubscribe_link(
        self, newsletter_admin, admin_request, mailoutbox
    ):
        newsletter = NewsletterFactory(body_html="<p>Ciao</p>")
        queryset = Newsletter.objects.filter(pk=newsletter.pk)

        newsletter_admin.send_test_to_self(admin_request, queryset)

        html_body = mailoutbox[0].alternatives[0][0]
        assert "anteprima" in html_body


class TestDailyNotificationAdmin:
    def test_is_read_only(self, admin_site, admin_request):
        """The audit log is written by the task only — no add / change in the admin."""
        from notifications.admin import DailyNotificationAdmin
        from notifications.models import DailyNotification

        admin_obj = DailyNotificationAdmin(DailyNotification, admin_site)

        assert admin_obj.has_add_permission(admin_request) is False
        assert admin_obj.has_change_permission(admin_request) is False


class TestMonthlyDigestAdmin:
    def test_is_read_only(self, admin_site, admin_request):
        """The audit log is written by the task only — no add / change in the admin."""
        from notifications.admin import MonthlyDigestAdmin
        from notifications.models import MonthlyDigest

        admin_obj = MonthlyDigestAdmin(MonthlyDigest, admin_site)

        assert admin_obj.has_add_permission(admin_request) is False
        assert admin_obj.has_change_permission(admin_request) is False
