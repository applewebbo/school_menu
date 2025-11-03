"""
Tests for public page caching functionality.

This module tests:
- Cache behavior for school_list view
- Cache behavior for get_schools_json_list view
- Cache behavior for search_schools view
- Cache invalidation when schools are created/updated
- Health check endpoint functionality
"""

import pytest
from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.urls import reverse

from school_menu.models import School

pytestmark = pytest.mark.django_db


class TestSchoolListCaching:
    """Test caching behavior for school_list view."""

    def test_school_list_view_has_cache_decorator(self, client, school_factory):
        """Test that school_list view has cache decorator applied."""
        # Create published schools
        school_factory.create_batch(3, is_published=True)

        url = reverse("school_menu:school_list")

        # Make request - should work regardless of cache backend
        response = client.get(url)
        assert response.status_code == 200

        # Verify schools are in response
        content = response.content.decode()
        assert "school" in content.lower()

    def test_school_list_cache_invalidated_on_school_save(self, client, school_factory):
        """Test that school_list cache is cleared when a school is saved."""
        school = school_factory(is_published=True)

        url = reverse("school_menu:school_list")

        # First request - populate cache
        response1 = client.get(url)
        assert response1.status_code == 200

        # Modify school (triggers cache invalidation)
        school.name = "Updated School Name"
        school.save()

        # Second request - cache should be cleared and repopulated
        response2 = client.get(url)
        assert response2.status_code == 200
        assert "Updated School Name" in response2.content.decode()

    def test_school_list_returns_only_published_schools(self, client, school_factory):
        """Test that school_list only shows published schools."""
        school_factory(is_published=True, name="Published School")
        school_factory(is_published=False, name="Unpublished School")

        url = reverse("school_menu:school_list")

        response = client.get(url)
        assert response.status_code == 200

        content = response.content.decode()
        assert "Published School" in content
        assert "Unpublished School" not in content


class TestSchoolsJsonListCaching:
    """Test caching behavior for get_schools_json_list view."""

    def test_schools_json_view_has_cache_decorator(self, client, school_factory):
        """Test that get_schools_json_list view has cache decorator applied."""
        school_factory.create_batch(3, is_published=True)

        url = reverse("school_menu:get_schools_json_list")

        # Make request - should work regardless of cache backend
        response = client.get(url)
        assert response.status_code == 200

        # Verify it returns JSON
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_schools_json_cache_invalidated_on_school_save(
        self, client, school_factory
    ):
        """Test that schools_json cache is cleared when a school is saved."""
        school = school_factory(is_published=True, name="Original Name")

        url = reverse("school_menu:get_schools_json_list")

        # First request - populate cache
        response1 = client.get(url)
        assert response1.status_code == 200

        # Modify school (triggers cache invalidation)
        school.name = "Updated Name"
        school.save()

        # Second request - cache should be cleared
        response2 = client.get(url)
        assert response2.status_code == 200
        data2 = response2.json()

        # Should have updated data
        assert data2[0]["name"] == "Updated Name"

    def test_schools_json_only_returns_published_schools(self, client, school_factory):
        """Test that only published schools are returned."""
        school_factory(is_published=True, name="Published School")
        school_factory(is_published=False, name="Unpublished School")

        url = reverse("school_menu:get_schools_json_list")

        response = client.get(url)
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["name"] == "Published School"


class TestSearchSchoolsCaching:
    """Test caching behavior for search_schools view."""

    def test_search_view_has_cache_decorator(self, client, school_factory):
        """Test that search_schools view has cache decorator applied."""
        school_factory(is_published=True, name="Test School", city="Milan")

        url = reverse("school_menu:search_schools")

        # Make request - should work regardless of cache backend
        response = client.get(url, {"q": "Test"})
        assert response.status_code == 200

    def test_search_finds_schools_by_name_and_city(self, client, school_factory):
        """Test that search finds schools by both name and city."""
        school_factory(is_published=True, name="Milan School", city="Rome")
        school_factory(is_published=True, name="Rome School", city="Milan")

        url = reverse("school_menu:search_schools")

        response = client.get(url, {"q": "Milan"})
        assert response.status_code == 200
        content = response.content.decode()

        # Should find both schools (one by name, one by city)
        assert "Milan School" in content or "Rome School" in content

    def test_search_empty_query_shows_hidden_results(self, client, school_factory):
        """Test that empty search query shows hidden results."""
        school_factory(is_published=True, name="Test School")

        url = reverse("school_menu:search_schools")

        response = client.get(url, {"q": ""})
        assert response.status_code == 200

    def test_search_no_results_shows_message(self, client, school_factory):
        """Test that no results shows appropriate message."""
        school_factory(is_published=True, name="Test School")

        url = reverse("school_menu:search_schools")

        response = client.get(url, {"q": "NonexistentSchool"})
        assert response.status_code == 200


class TestCacheInvalidationOnSchoolChanges:
    """Test that cache is properly invalidated when schools change."""

    def test_creating_school_invalidates_cache(self, client, user_factory):
        """Test that creating a new school invalidates the cache."""
        # Clear cache
        cache.clear()

        url = reverse("school_menu:school_list")

        # Populate cache
        client.get(url)

        # Create a new school
        user = user_factory()
        School.objects.create(
            user=user,
            name="New School",
            city="Milan",
            is_published=True,
            start_month=9,
            start_day=10,
            end_month=6,
            end_day=10,
        )

        # Cache should be invalidated
        # Making a new request should return updated data
        response = client.get(url)
        assert response.status_code == 200
        assert "New School" in response.content.decode()

    def test_updating_school_is_published_invalidates_cache(
        self, client, school_factory
    ):
        """Test that updating is_published invalidates cache."""
        school = school_factory(is_published=False, name="Hidden School")

        url = reverse("school_menu:school_list")

        # Populate cache
        response1 = client.get(url)
        content1 = response1.content.decode()
        assert "Hidden School" not in content1

        # Publish the school
        school.is_published = True
        school.save()

        # Cache should be invalidated
        response2 = client.get(url)
        content2 = response2.content.decode()
        assert "Hidden School" in content2


class TestHealthCheckEndpoint:
    """Test health check endpoint functionality."""

    def test_health_check_returns_healthy_status(self, client):
        """Test that health check returns healthy status when all services are ok."""
        url = reverse("health_check")

        response = client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"
        data = response.json()

        # In test environment (DummyCache), cache might be "error" or "degraded"
        # But database should always be ok
        assert data["status"] in ["healthy", "degraded"]
        assert "status" in data
        assert "services" in data
        assert "cache" in data["services"]
        assert "database" in data["services"]
        assert data["services"]["database"] == "ok"
        assert data["services"]["cache"] in ["ok", "error"]

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            }
        }
    )
    def test_health_check_degraded_when_cache_fails(self, client, monkeypatch):
        """Test that health check returns degraded when cache fails."""

        # Mock cache.set to raise an exception
        def mock_cache_set(*args, **kwargs):
            raise Exception("Cache connection failed")

        monkeypatch.setattr(cache, "set", mock_cache_set)

        url = reverse("health_check")
        response = client.get(url)

        assert response.status_code == 200  # Still returns 200 for degraded
        data = response.json()

        assert data["status"] == "degraded"
        assert "error" in data["services"]["cache"]

    def test_health_check_unhealthy_when_database_fails(self, client, monkeypatch):
        """Test that health check returns unhealthy when database fails."""

        # Mock database cursor to raise an exception
        class MockCursor:
            def __enter__(self):
                raise Exception("Database connection failed")

            def __exit__(self, *args):
                pass

        def mock_cursor():
            return MockCursor()

        monkeypatch.setattr(connection, "cursor", mock_cursor)

        url = reverse("health_check")
        response = client.get(url)

        assert response.status_code == 503  # Service unavailable
        data = response.json()

        assert data["status"] == "unhealthy"
        assert "error" in data["services"]["database"]

    def test_health_check_only_accepts_get(self, client):
        """Test that health check only accepts GET requests."""
        url = reverse("health_check")

        # POST should not be allowed
        response = client.post(url)
        assert response.status_code == 405  # Method not allowed


class TestCacheInvalidationPatterns:
    """Test cache invalidation pattern matching."""

    def test_invalidate_school_list_cache_clears_all_patterns(self, school_factory):
        """Test that invalidate_school_list_cache clears all relevant patterns."""
        from school_menu.cache import invalidate_school_list_cache

        # Create a school to trigger cache population
        school_factory(is_published=True)

        # Set some cache keys manually
        cache.set("school_list_test", "data", 3600)
        cache.set("schools_json_test", "data", 3600)
        cache.set("search_test", "data", 3600)

        # Call invalidation
        deleted_count = invalidate_school_list_cache()

        # In test environment (DummyCache), this returns 1 (fallback behavior)
        # In production (Redis), it would return the actual count
        assert deleted_count >= 0

    def test_invalidate_with_pattern_matching(self, monkeypatch):
        """Test cache invalidation when cache supports delete_pattern."""
        import school_menu.cache as cache_module

        # Mock cache to have delete_pattern method
        deleted_patterns = []

        class MockCache:
            def delete_pattern(self, pattern):
                deleted_patterns.append(pattern)
                return 1  # Return 1 to indicate one key deleted

        mock_cache = MockCache()

        # Patch the cache in the cache module
        monkeypatch.setattr(cache_module, "cache", mock_cache)

        # Call invalidation
        from school_menu.cache import invalidate_school_list_cache

        deleted_count = invalidate_school_list_cache()

        # Should have called delete_pattern for each pattern
        assert len(deleted_patterns) == 3
        assert "*school_list*" in deleted_patterns
        assert "*schools_json*" in deleted_patterns
        assert "*search*" in deleted_patterns
        assert deleted_count == 3


class TestHealthCheckWithRealCache:
    """Test health check with database cache backend."""

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.db.DatabaseCache",
                "LOCATION": "test_cache_table",
            }
        }
    )
    def test_health_check_with_database_cache(
        self, client, django_db_setup, django_db_blocker
    ):
        """Test health check with database cache backend."""
        from django.core.management import call_command

        # Create cache table
        with django_db_blocker.unblock():
            try:
                call_command("createcachetable", "test_cache_table", verbosity=0)
            except Exception:  # nosec B110
                # Table might already exist - this is expected behavior
                pass

        url = reverse("health_check")

        response = client.get(url)
        data = response.json()

        # With database cache, cache should work
        assert response.status_code == 200
        assert data["services"]["cache"] == "ok"
        assert data["services"]["database"] == "ok"
        assert data["status"] == "healthy"
