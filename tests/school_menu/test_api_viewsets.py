import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestSchoolViewSet:
    """Test SchoolViewSet API endpoint."""

    def test_school_list_endpoint(self, client, school):
        """Test GET /api/v1/schools/ returns published schools."""
        url = reverse("school-list")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == school.name
        assert data["results"][0]["city"] == school.city
        assert "url" in data["results"][0]

    def test_school_list_excludes_unpublished(self, client, school):
        """Test unpublished schools are not returned."""
        school.is_published = False
        school.save()

        url = reverse("school-list")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0

    def test_school_list_pagination(self, client, school_factory):
        """Test school list pagination."""
        # Create 25 schools to test pagination (default page_size=20)
        school_factory.create_batch(25, is_published=True)

        url = reverse("school-list")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 25
        assert len(data["results"]) == 20
        assert data["next"] is not None

    def test_school_list_multiple_requests(self, client, school):
        """Test school list can be requested multiple times."""
        # NOTE: In test environment we use DummyCache
        # This test verifies the endpoint works correctly with caching disabled
        url = reverse("school-list")

        # Make multiple requests
        for _ in range(3):
            response = client.get(url)
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1

    def test_school_detail_endpoint(self, client, school):
        """Test GET /api/v1/schools/{slug}/ returns school detail."""
        url = reverse("school-detail", kwargs={"slug": school.slug})
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == school.name
        assert data["city"] == school.city


class TestMenuViewSet:
    """Test MenuViewSet API endpoint."""

    def test_menu_detail_endpoint(self, client, school, detailed_meal):
        """Test GET /api/v1/menu/{slug}/ returns menu."""
        url = reverse("menu-detail", kwargs={"slug": school.slug})
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == school.name
        assert "menu" in data
        assert "types_menu" in data
        assert isinstance(data["menu"], list)

    def test_menu_detail_not_found(self, client):
        """Test menu endpoint returns 404 for non-existent school."""
        url = reverse("menu-detail", kwargs={"slug": "non-existent"})
        response = client.get(url)

        assert response.status_code == 404

    def test_menu_detail_multiple_requests(self, client, school, detailed_meal):
        """Test menu detail can be requested multiple times."""
        # NOTE: In test environment we use DummyCache
        # This test verifies the endpoint works correctly with caching disabled
        url = reverse("menu-detail", kwargs={"slug": school.slug})

        # Make multiple requests
        for _ in range(3):
            response = client.get(url)
            assert response.status_code == 200
            data = response.json()
            assert "menu" in data

    def test_menu_simple_type_structure(self, client, school, simple_meal):
        """Test menu endpoint returns correct structure for simple meals."""
        school.menu_type = "S"
        school.save()

        url = reverse("menu-detail", kwargs={"slug": school.slug})
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "menu" in data
        assert "types_menu" in data
        assert isinstance(data["menu"], list)

    def test_menu_annual_type_structure(self, client, school, annual_meal):
        """Test menu endpoint returns correct structure for annual meals."""
        school.annual_menu = True
        school.save()

        url = reverse("menu-detail", kwargs={"slug": school.slug})
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "menu" in data
        assert "types_menu" in data
        assert isinstance(data["menu"], list)


class TestAPIConfiguration:
    """Test API configuration and setup."""

    def test_rest_framework_settings_configured(self):
        """Test REST_FRAMEWORK settings are properly configured."""
        from django.conf import settings

        assert "REST_FRAMEWORK" in dir(settings)
        assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"] == "100/hour"
        assert (
            settings.REST_FRAMEWORK["EXCEPTION_HANDLER"]
            == "school_menu.api.exceptions.custom_exception_handler"
        )

    def test_custom_exception_handler_exists(self):
        """Test custom exception handler is defined."""
        from school_menu.api.exceptions import custom_exception_handler

        assert callable(custom_exception_handler)

    def test_custom_exception_handler_429_response(self):
        """Test custom exception handler formats 429 responses."""
        from rest_framework.exceptions import Throttled
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory
        from rest_framework.views import exception_handler as default_handler

        from school_menu.api.exceptions import custom_exception_handler

        factory = APIRequestFactory()
        request = factory.get("/")

        # Create a throttled exception
        exc = Throttled(wait=3600)
        context = {"request": Request(request)}

        # Get default response
        default_handler(exc, context)
        # Process with custom handler
        response = custom_exception_handler(exc, context)

        assert response.status_code == 429
        assert response.data["error"] == "Troppe richieste"
        assert "detail" in response.data
        assert "retry_after" in response.data

    def test_custom_exception_handler_non_429_passthrough(self):
        """Test custom exception handler passes through non-429 errors."""
        from rest_framework.exceptions import NotFound
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        from school_menu.api.exceptions import custom_exception_handler

        factory = APIRequestFactory()
        request = factory.get("/")

        # Create a 404 exception
        exc = NotFound(detail="Not found")
        context = {"request": Request(request)}

        response = custom_exception_handler(exc, context)

        assert response.status_code == 404
        # Should not modify non-429 responses
        assert (
            "error" not in response.data or response.data.get("detail") == "Not found"
        )
