import pytest
from django.urls import reverse

from school_menu.models import AuditLog

pytestmark = pytest.mark.django_db


class TestAuditLoggingIntegration:
    """Test audit logging is integrated in views."""

    def test_audit_log_middleware_available(self, rf, user):
        """Test audit_log method is available on requests."""
        from core.middleware import AuditLogMiddleware

        request = rf.get("/")
        request.user = user

        middleware = AuditLogMiddleware(lambda r: None)
        middleware.process_request(request)

        assert hasattr(request, "audit_log")
        assert callable(request.audit_log)

        # Test creating an audit log
        request.audit_log(
            action="SCHOOL_CREATE",
            model_name="School",
            object_id=1,
            object_repr="Test",
            changes={"created": True},
        )

        audit = AuditLog.objects.get()
        assert audit.action == "SCHOOL_CREATE"
        assert audit.user == user

    def test_audit_log_serializes_changes(self, rf, user):
        """Test audit log correctly serializes changes with str() conversion."""
        from datetime import date

        from core.middleware import AuditLogMiddleware

        request = rf.get("/")
        request.user = user

        middleware = AuditLogMiddleware(lambda r: None)
        middleware.process_request(request)

        # Test with date objects (simulating form changes)
        changes = {
            "start_date": {"old": str(date(2024, 9, 1)), "new": str(date(2025, 9, 1))},
            "name": {"old": "Old Name", "new": "New Name"},
        }

        request.audit_log(
            action="SCHOOL_UPDATE",
            model_name="School",
            object_id=1,
            object_repr="Test School",
            changes=changes,
        )

        audit = AuditLog.objects.get()
        assert audit.action == "SCHOOL_UPDATE"
        assert "start_date" in audit.changes
        assert "2025-09-01" in audit.changes["start_date"]["new"]


class TestDeprecationHeaders:
    """Test deprecation headers on legacy JSON endpoints."""

    def test_schools_json_list_has_deprecation_headers(self, client, school):
        """Test /json/schools/ returns deprecation headers."""
        response = client.get(reverse("school_menu:get_schools_json_list"))

        assert response.status_code == 200
        assert response["X-API-Deprecated"] == "true"
        assert 'version="v1"' in response["Deprecation"]
        assert "/api/v1/schools/" in response["Warning"]

    def test_school_json_menu_has_deprecation_headers(
        self, client, school, detailed_meal
    ):
        """Test /json/menu/<slug>/ returns deprecation headers."""
        response = client.get(
            reverse("school_menu:get_school_json_menu", kwargs={"slug": school.slug})
        )

        assert response.status_code == 200
        assert response["X-API-Deprecated"] == "true"
        assert 'version="v1"' in response["Deprecation"]
        assert f"/api/v1/menu/{school.slug}/" in response["Warning"]

    def test_legacy_endpoints_still_functional(self, client, school, detailed_meal):
        """Test legacy endpoints still return correct data despite deprecation."""
        # Test schools list
        response = client.get(reverse("school_menu:get_schools_json_list"))
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["name"] == school.name

        # Test menu detail
        response = client.get(
            reverse("school_menu:get_school_json_menu", kwargs={"slug": school.slug})
        )
        assert response.status_code == 200
        data = response.json()
        assert "meals" in data
        assert "current_day" in data
