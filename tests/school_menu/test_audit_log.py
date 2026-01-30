import pytest
from django.test import RequestFactory

from core.middleware import AuditLogMiddleware
from school_menu.models import AuditLog

pytestmark = pytest.mark.django_db


class TestAuditLogModel:
    """Test AuditLog model."""

    def test_audit_log_creation(self, user):
        """Test creating audit log entry."""
        audit = AuditLog.objects.create(
            user=user,
            action=AuditLog.Actions.SCHOOL_CREATE,
            model_name="School",
            object_id=1,
            object_repr="Test School",
            changes={"name": "Test School"},
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
        )

        assert audit.user == user
        assert audit.action == AuditLog.Actions.SCHOOL_CREATE
        assert audit.model_name == "School"
        assert audit.object_id == 1
        assert audit.object_repr == "Test School"
        assert audit.changes == {"name": "Test School"}
        assert audit.ip_address == "127.0.0.1"
        assert audit.user_agent == "Mozilla/5.0"

    def test_audit_log_str(self, user):
        """Test AuditLog __str__ method."""
        audit = AuditLog.objects.create(
            user=user,
            action=AuditLog.Actions.MENU_UPLOAD,
            model_name="DetailedMeal",
            object_repr="Test Menu",
        )

        str_repr = str(audit)
        assert "Menu caricato" in str_repr
        assert "Test Menu" in str_repr

    def test_audit_log_nullable_user(self):
        """Test audit log without user (anonymous action)."""
        audit = AuditLog.objects.create(
            user=None,
            action=AuditLog.Actions.SETTINGS_CHANGE,
            model_name="Settings",
            object_repr="System Settings",
        )

        assert audit.user is None
        assert audit.action == AuditLog.Actions.SETTINGS_CHANGE

    def test_audit_log_ordering(self, user):
        """Test audit logs are ordered by timestamp descending."""
        audit1 = AuditLog.objects.create(
            user=user,
            action=AuditLog.Actions.SCHOOL_CREATE,
            model_name="School",
            object_repr="First",
        )
        audit2 = AuditLog.objects.create(
            user=user,
            action=AuditLog.Actions.SCHOOL_UPDATE,
            model_name="School",
            object_repr="Second",
        )

        audits = list(AuditLog.objects.all())
        assert audits[0] == audit2
        assert audits[1] == audit1


class TestAuditLogMiddleware:
    """Test AuditLogMiddleware."""

    def test_middleware_adds_audit_log_method(self, rf: RequestFactory, user):
        """Test middleware adds audit_log method to request."""
        request = rf.get("/")
        request.user = user

        middleware = AuditLogMiddleware(lambda r: None)
        middleware.process_request(request)

        assert hasattr(request, "audit_log")
        assert callable(request.audit_log)

    def test_audit_log_method_creates_entry(self, rf: RequestFactory, user):
        """Test request.audit_log() creates AuditLog entry."""
        request = rf.get("/")
        request.user = user
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Test Browser"

        middleware = AuditLogMiddleware(lambda r: None)
        middleware.process_request(request)

        request.audit_log(
            action=AuditLog.Actions.SCHOOL_CREATE,
            model_name="School",
            object_id=123,
            object_repr="Test School",
            changes={"field": "value"},
        )

        audit = AuditLog.objects.get()
        assert audit.user == user
        assert audit.action == AuditLog.Actions.SCHOOL_CREATE
        assert audit.model_name == "School"
        assert audit.object_id == 123
        assert audit.object_repr == "Test School"
        assert audit.changes == {"field": "value"}
        assert audit.ip_address == "192.168.1.1"
        assert audit.user_agent == "Test Browser"

    def test_audit_log_anonymous_user(self, rf: RequestFactory):
        """Test audit_log works with anonymous user."""
        from django.contrib.auth.models import AnonymousUser

        request = rf.get("/")
        request.user = AnonymousUser()
        request.META["REMOTE_ADDR"] = "10.0.0.1"

        middleware = AuditLogMiddleware(lambda r: None)
        middleware.process_request(request)

        request.audit_log(
            action=AuditLog.Actions.SETTINGS_CHANGE,
            model_name="Settings",
            object_id=None,
            object_repr="Public Settings",
        )

        audit = AuditLog.objects.get()
        assert audit.user is None
        assert audit.ip_address == "10.0.0.1"

    def test_get_client_ip_with_proxy(self, rf: RequestFactory):
        """Test IP extraction with X-Forwarded-For header."""
        request = rf.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1, 198.51.100.1"
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        middleware = AuditLogMiddleware(lambda r: None)
        ip = middleware.get_client_ip(request)

        assert ip == "203.0.113.1"

    def test_get_client_ip_without_proxy(self, rf: RequestFactory):
        """Test IP extraction without X-Forwarded-For header."""
        request = rf.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        middleware = AuditLogMiddleware(lambda r: None)
        ip = middleware.get_client_ip(request)

        assert ip == "192.168.1.100"

    def test_user_agent_truncation(self, rf: RequestFactory, user):
        """Test user agent is truncated to 500 chars."""
        request = rf.get("/")
        request.user = user
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.META["HTTP_USER_AGENT"] = "X" * 600

        middleware = AuditLogMiddleware(lambda r: None)
        middleware.process_request(request)

        request.audit_log(
            action=AuditLog.Actions.SCHOOL_CREATE,
            model_name="School",
            object_id=1,
            object_repr="Test",
        )

        audit = AuditLog.objects.get()
        assert len(audit.user_agent) == 500


class TestAuditLogAdmin:
    """Test AuditLogAdmin permissions."""

    def test_admin_no_add_permission(self, admin_client):
        """Test that AuditLog cannot be added via admin."""
        from django.contrib.admin.sites import AdminSite

        from school_menu.admin import AuditLogAdmin

        admin_instance = AuditLogAdmin(AuditLog, AdminSite())
        request = type("Request", (), {"user": None})()

        assert admin_instance.has_add_permission(request) is False

    def test_admin_no_change_permission(self, admin_client):
        """Test that AuditLog cannot be changed via admin."""
        from django.contrib.admin.sites import AdminSite

        from school_menu.admin import AuditLogAdmin

        admin_instance = AuditLogAdmin(AuditLog, AdminSite())
        request = type("Request", (), {"user": None})()

        assert admin_instance.has_change_permission(request) is False

    def test_admin_delete_permission_superuser_only(self, admin_user):
        """Test that only superusers can delete AuditLog entries."""
        from django.contrib.admin.sites import AdminSite

        from school_menu.admin import AuditLogAdmin

        admin_instance = AuditLogAdmin(AuditLog, AdminSite())

        # Superuser request
        request_super = type("Request", (), {"user": admin_user})()
        assert admin_instance.has_delete_permission(request_super) is True

        # Non-superuser request
        admin_user.is_superuser = False
        request_non_super = type("Request", (), {"user": admin_user})()
        assert admin_instance.has_delete_permission(request_non_super) is False
