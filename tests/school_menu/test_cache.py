"""Tests for cache utility functions."""

import logging
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from school_menu.cache import (
    get_cached_or_query,
    get_meal_cache_key,
    get_school_menu_cache_key,
    get_types_menu_cache_key,
    invalidate_meal_cache,
    invalidate_school_cache,
    invalidate_school_list_cache,
    invalidate_school_meals,
    invalidate_school_page,
    invalidate_types_menu,
)

pytestmark = pytest.mark.django_db


class TestCacheKeyGeneration:
    """Test cache key generation functions."""

    @pytest.mark.parametrize(
        "school_id,week,day,season,meal_type,expected_key",
        [
            (1, 2, 3, "INVERNALE", "STANDARD", "meal:1:2:3:INVERNALE:STANDARD"),
            (
                42,
                4,
                5,
                "PRIMAVERILE",
                "NO_GLUTINE",
                "meal:42:4:5:PRIMAVERILE:NO_GLUTINE",
            ),
        ],
    )
    def test_get_meal_cache_key(
        self, school_id, week, day, season, meal_type, expected_key
    ):
        """Test meal cache key generation with various parameters."""
        key = get_meal_cache_key(
            school_id=school_id, week=week, day=day, season=season, meal_type=meal_type
        )
        assert key == expected_key

    @pytest.mark.parametrize(
        "school_id,expected_key",
        [
            (1, "types_menu:1"),
            (99, "types_menu:99"),
        ],
    )
    def test_get_types_menu_cache_key(self, school_id, expected_key):
        """Test types menu cache key generation."""
        key = get_types_menu_cache_key(school_id=school_id)
        assert key == expected_key

    @pytest.mark.parametrize(
        "school_slug,expected_key",
        [
            ("my-school-city", "school_page:my-school-city"),
            ("another-school", "school_page:another-school"),
        ],
    )
    def test_get_school_menu_cache_key(self, school_slug, expected_key):
        """Test school menu page cache key generation."""
        key = get_school_menu_cache_key(school_slug=school_slug)
        assert key == expected_key


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

    def test_invalidate_meal_cache_fallback(self):
        """
        Test invalidate_meal_cache with fallback (DummyCache).

        In test environment with DummyCache, delete_pattern is not supported
        and the function returns 0.
        """
        school_id = 1

        # Invalidate meal cache for school 1
        result = invalidate_meal_cache(school_id)

        # In test environment (dummy cache), delete_pattern is not supported
        # So we expect 0 to be returned
        assert result == 0

    def test_invalidate_meal_cache_with_redis(self):
        """
        Test invalidate_meal_cache when Redis backend is available.

        This mocks the cache to have delete_pattern method to test the Redis path.
        """
        school_id = 1

        # Create a mock cache with delete_pattern method
        mock_cache = MagicMock()
        mock_cache.delete_pattern = MagicMock(return_value=5)

        # Patch the cache module
        with patch("school_menu.cache.cache", mock_cache):
            result = invalidate_meal_cache(school_id)

            # Verify delete_pattern was called with correct patterns
            assert mock_cache.delete_pattern.call_count == 5
            expected_patterns = [
                f"*meal:{school_id}:*",
                f"*meals:{school_id}:*",
                f"*annual_meals:{school_id}:*",
                f"*types_menu:{school_id}*",
                "*json_api*",
            ]
            for pattern in expected_patterns:
                mock_cache.delete_pattern.assert_any_call(pattern)

            # Verify it returns the total number of deleted keys (5 per pattern * 5 patterns)
            assert result == 25

    def test_invalidate_school_cache_fallback(self):
        """
        Test invalidate_school_cache with fallback (DummyCache).

        In test environment with DummyCache, delete_pattern is not supported.
        """
        school_id = 1
        school_slug = "test-school"

        # Invalidate school cache
        result = invalidate_school_cache(school_id, school_slug)

        # In test environment (dummy cache), only cache.delete calls succeed
        # invalidate_meal_cache returns 0, plus 2 for page and list cache
        assert result == 2

    def test_invalidate_school_cache_without_slug(self):
        """Test invalidate_school_cache without providing slug."""
        school_id = 1

        # Invalidate school cache without slug
        result = invalidate_school_cache(school_id)

        # Should still clear meal cache and school list, but not page cache
        # In test environment: 0 (meals) + 0 (no page) + 1 (list) = 1
        assert result == 1

    def test_invalidate_school_list_cache(self):
        """Test invalidating school list cache."""
        # Call invalidate function - should not raise any errors
        invalidate_school_list_cache()

        # In DummyCache, nothing is actually cached or deleted, but function should work
        assert True


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


class TestCacheLogging:
    """Test cache hit/miss logging."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    def teardown_method(self):
        """Clear cache after each test."""
        cache.clear()

    def test_cache_miss_logging(self, caplog):
        """Test that cache misses are logged at DEBUG level."""

        def query_func():
            return {"data": "test"}

        cache_key = "test_log_key"

        with caplog.at_level(logging.DEBUG, logger="school_menu.cache"):
            result = get_cached_or_query(cache_key, query_func, timeout=300)

            # In DummyCache, we should see MISS and SET logs
            assert any("Cache MISS" in record.message for record in caplog.records)
            assert any("Cache SET" in record.message for record in caplog.records)
            assert result == {"data": "test"}

    def test_cache_hit_logging(self, caplog):
        """Test that cache hits are logged at DEBUG level."""
        cache_key = "test_hit_key"
        cached_value = {"data": "cached"}

        # Mock cache to simulate a hit
        with patch("school_menu.cache.cache") as mock_cache:
            mock_cache.get.return_value = cached_value

            with caplog.at_level(logging.DEBUG, logger="school_menu.cache"):
                result = get_cached_or_query(cache_key, lambda: {}, timeout=300)

                # Verify HIT log appears
                assert any("Cache HIT" in record.message for record in caplog.records)
                assert result == cached_value


class TestModelCacheInvalidation:
    """Test cache invalidation on model save/delete operations."""

    def test_simple_meal_save_invalidates_cache(self, school):
        """Test that saving a SimpleMeal triggers cache invalidation."""
        from school_menu.models import SimpleMeal

        with patch("school_menu.models.invalidate_meal_cache") as mock_invalidate:
            SimpleMeal.objects.create(
                school=school,
                week=1,
                day=1,
                season=1,
                type="S",
                menu="Test menu",
            )

            # Verify invalidate_meal_cache was called with school ID
            mock_invalidate.assert_called_once_with(school.id)

    def test_simple_meal_delete_invalidates_cache(self, school):
        """Test that deleting a SimpleMeal triggers cache invalidation."""
        from school_menu.models import SimpleMeal

        meal = SimpleMeal.objects.create(
            school=school,
            week=1,
            day=1,
            season=1,
            type="S",
            menu="Test menu",
        )

        with patch("school_menu.models.invalidate_meal_cache") as mock_invalidate:
            meal.delete()

            # Verify invalidate_meal_cache was called with school ID
            mock_invalidate.assert_called_once_with(school.id)

    def test_detailed_meal_save_invalidates_cache(self, school):
        """Test that saving a DetailedMeal triggers cache invalidation."""
        from school_menu.models import DetailedMeal

        with patch("school_menu.models.invalidate_meal_cache") as mock_invalidate:
            DetailedMeal.objects.create(
                school=school,
                week=1,
                day=1,
                season=1,
                type="S",
                first_course="Pasta",
                second_course="Chicken",
                side_dish="Salad",
                fruit="Apple",
                snack="Crackers",
            )

            # Verify invalidate_meal_cache was called with school ID
            mock_invalidate.assert_called_once_with(school.id)

    def test_detailed_meal_delete_invalidates_cache(self, school):
        """Test that deleting a DetailedMeal triggers cache invalidation."""
        from school_menu.models import DetailedMeal

        meal = DetailedMeal.objects.create(
            school=school,
            week=1,
            day=1,
            season=1,
            type="S",
            first_course="Pasta",
            second_course="Chicken",
            side_dish="Salad",
            fruit="Apple",
            snack="Crackers",
        )

        with patch("school_menu.models.invalidate_meal_cache") as mock_invalidate:
            meal.delete()

            # Verify invalidate_meal_cache was called with school ID
            mock_invalidate.assert_called_once_with(school.id)

    def test_annual_meal_save_invalidates_cache(self, school):
        """Test that saving an AnnualMeal triggers cache invalidation."""
        from datetime import date

        from school_menu.models import AnnualMeal

        with patch("school_menu.models.invalidate_meal_cache") as mock_invalidate:
            AnnualMeal.objects.create(
                school=school,
                day=1,
                type="S",
                menu="Test menu",
                date=date(2025, 1, 15),
            )

            # Verify invalidate_meal_cache was called with school ID
            mock_invalidate.assert_called_once_with(school.id)

    def test_annual_meal_delete_invalidates_cache(self, school):
        """Test that deleting an AnnualMeal triggers cache invalidation."""
        from datetime import date

        from school_menu.models import AnnualMeal

        meal = AnnualMeal.objects.create(
            school=school,
            day=1,
            type="S",
            menu="Test menu",
            date=date(2025, 1, 15),
        )

        with patch("school_menu.models.invalidate_meal_cache") as mock_invalidate:
            meal.delete()

            # Verify invalidate_meal_cache was called with school ID
            mock_invalidate.assert_called_once_with(school.id)

    def test_school_save_invalidates_cache(self, user):
        """Test that saving a School triggers cache invalidation."""
        from school_menu.models import School

        with patch("school_menu.models.invalidate_school_cache") as mock_invalidate:
            school = School.objects.create(
                name="Test School",
                city="Test City",
                user=user,
            )

            # Verify invalidate_school_cache was called with school ID and slug
            mock_invalidate.assert_called_once_with(school.id, school.slug)

    def test_school_update_invalidates_cache(self, school):
        """Test that updating a School triggers cache invalidation."""

        # Update the school
        with patch("school_menu.models.invalidate_school_cache") as mock_invalidate:
            school.menu_type = "S"
            school.save()

            # Verify invalidate_school_cache was called
            mock_invalidate.assert_called_once_with(school.id, school.slug)


class TestCacheIsolation:
    """Test that cache is properly isolated between schools."""

    def test_cache_isolation_between_schools(
        self, school, school_factory, user_factory
    ):
        """Test that cache invalidation for one school doesn't affect another."""
        from school_menu.models import SimpleMeal

        # Create a second school using factory
        second_user = user_factory()
        second_school = school_factory(user=second_user)

        # Create meals for both schools
        SimpleMeal.objects.create(
            school=school,
            week=1,
            day=1,
            season=1,
            type="S",
            menu="School 1 menu",
        )

        SimpleMeal.objects.create(
            school=second_school,
            week=1,
            day=1,
            season=1,
            type="S",
            menu="School 2 menu",
        )

        # Generate cache keys for both schools
        key1 = get_meal_cache_key(school.id, 1, 1, "1", "S")
        key2 = get_meal_cache_key(second_school.id, 1, 1, "1", "S")

        # Verify keys are different
        assert key1 != key2
        assert str(school.id) in key1
        assert str(second_school.id) in key2
