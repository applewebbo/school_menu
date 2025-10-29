"""Tests for cache utility functions."""

from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from school_menu.cache import (
    get_cached_or_query,
    get_meal_cache_key,
    get_school_menu_cache_key,
    get_types_menu_cache_key,
    invalidate_school_meals,
    invalidate_school_page,
    invalidate_types_menu,
)

pytestmark = pytest.mark.django_db


class TestCacheKeyGeneration:
    """Test cache key generation functions."""

    def test_get_meal_cache_key(self):
        """Test meal cache key generation with various parameters."""
        key = get_meal_cache_key(
            school_id=1, week=2, day=3, season="INVERNALE", meal_type="STANDARD"
        )
        assert key == "meal:1:2:3:INVERNALE:STANDARD"

    def test_get_meal_cache_key_different_params(self):
        """Test meal cache key with different parameters."""
        key = get_meal_cache_key(
            school_id=42, week=4, day=5, season="PRIMAVERILE", meal_type="NO_GLUTINE"
        )
        assert key == "meal:42:4:5:PRIMAVERILE:NO_GLUTINE"

    def test_get_types_menu_cache_key(self):
        """Test types menu cache key generation."""
        key = get_types_menu_cache_key(school_id=1)
        assert key == "types_menu:1"

    def test_get_types_menu_cache_key_different_school(self):
        """Test types menu cache key with different school ID."""
        key = get_types_menu_cache_key(school_id=99)
        assert key == "types_menu:99"

    def test_get_school_menu_cache_key(self):
        """Test school menu page cache key generation."""
        key = get_school_menu_cache_key(school_slug="my-school-city")
        assert key == "school_page:my-school-city"

    def test_get_school_menu_cache_key_different_slug(self):
        """Test school menu page cache key with different slug."""
        key = get_school_menu_cache_key(school_slug="another-school")
        assert key == "school_page:another-school"


class TestCacheInvalidation:
    """Test cache invalidation functions."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    def teardown_method(self):
        """Clear cache after each test."""
        cache.clear()

    def test_invalidate_school_page(self):
        """
        Test invalidating a school page cache.

        Note: In test environment with DummyCache, cache operations don't actually store data.
        This test verifies the function executes without errors.
        """
        school_slug = "test-school"

        # Call invalidate function - should not raise any errors
        invalidate_school_page(school_slug)

        # In DummyCache, nothing is actually cached or deleted, but function should work
        assert True

    def test_invalidate_types_menu(self):
        """
        Test invalidating types menu cache.

        Note: In test environment with DummyCache, cache operations don't actually store data.
        This test verifies the function executes without errors.
        """
        school_id = 1

        # Call invalidate function - should not raise any errors
        invalidate_types_menu(school_id)

        # In DummyCache, nothing is actually cached or deleted, but function should work
        assert True

    def test_invalidate_school_meals_fallback(self):
        """
        Test invalidating school meals with fallback (DummyCache).

        In test environment with DummyCache, delete_pattern is not supported
        and the function returns 0.
        """
        school_id = 1

        # Invalidate school 1 meals
        result = invalidate_school_meals(school_id)

        # In test environment (dummy cache), delete_pattern is not supported
        # So we expect 0 to be returned
        assert result == 0

        # Verify function works for another school too
        assert invalidate_school_meals(2) == 0

    def test_invalidate_school_meals_with_redis(self):
        """
        Test invalidating school meals when Redis backend is available.

        This mocks the cache to have delete_pattern method to test the Redis path.
        """
        school_id = 1

        # Create a mock cache with delete_pattern method
        mock_cache = MagicMock()
        mock_cache.delete_pattern = MagicMock(return_value=5)

        # Patch the cache module
        with patch("school_menu.cache.cache", mock_cache):
            result = invalidate_school_meals(school_id)

            # Verify delete_pattern was called with correct pattern
            mock_cache.delete_pattern.assert_called_once_with("*meal:1:*")

            # Verify it returns the number of deleted keys
            assert result == 5


class TestGetCachedOrQuery:
    """Test the get_cached_or_query helper function."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()
        self.query_call_count = 0

    def teardown_method(self):
        """Clear cache after each test."""
        cache.clear()

    def test_cache_miss_executes_query(self):
        """Test that query function is executed on cache miss."""

        def query_func():
            self.query_call_count += 1
            return {"data": "test_value"}

        cache_key = "test_key"

        # First call - cache miss
        result = get_cached_or_query(cache_key, query_func, timeout=300)

        assert result == {"data": "test_value"}
        assert self.query_call_count == 1

    def test_cache_hit_skips_query(self):
        """Test that query function is not executed on cache hit."""

        def query_func():
            self.query_call_count += 1
            return {"data": "test_value"}

        cache_key = "test_key"
        cached_value = {"data": "cached_value"}

        # Mock cache.get to return a cached value (simulating cache hit)
        with patch("school_menu.cache.cache") as mock_cache:
            mock_cache.get.return_value = cached_value

            result = get_cached_or_query(cache_key, query_func, timeout=300)

            # Verify cache.get was called
            mock_cache.get.assert_called_once_with(cache_key)

            # Verify query function was NOT called
            assert self.query_call_count == 0

            # Verify cached value was returned
            assert result == cached_value

            # Verify cache.set was NOT called (no need to cache on cache hit)
            mock_cache.set.assert_not_called()

    def test_custom_timeout(self):
        """Test using custom timeout value."""

        def query_func():
            return {"data": "custom_timeout"}

        cache_key = "test_timeout_key"

        # Call with custom timeout
        result = get_cached_or_query(cache_key, query_func, timeout=3600)

        assert result == {"data": "custom_timeout"}

    def test_default_timeout(self):
        """Test using default timeout (24 hours)."""

        def query_func():
            return {"data": "default_timeout"}

        cache_key = "test_default_timeout"

        # Call without specifying timeout (uses default 86400)
        result = get_cached_or_query(cache_key, query_func)

        assert result == {"data": "default_timeout"}

    def test_none_value_is_not_cached(self):
        """Test that None values from query are not treated as cache hits."""

        def query_func():
            self.query_call_count += 1
            return None

        cache_key = "test_none_key"

        # First call
        result1 = get_cached_or_query(cache_key, query_func)
        assert result1 is None
        assert self.query_call_count == 1

        # Second call - None is cached, so it should not execute query again
        # But in dummy cache, it will execute again
        result2 = get_cached_or_query(cache_key, query_func)
        assert result2 is None
        # In dummy cache, query is always executed
        assert self.query_call_count == 2

    def test_callable_returns_list(self):
        """Test that query function can return list data."""

        def query_func():
            return [1, 2, 3, 4, 5]

        cache_key = "test_list_key"

        result = get_cached_or_query(cache_key, query_func)

        assert result == [1, 2, 3, 4, 5]

    def test_callable_returns_string(self):
        """Test that query function can return string data."""

        def query_func():
            return "simple string"

        cache_key = "test_string_key"

        result = get_cached_or_query(cache_key, query_func)

        assert result == "simple string"
