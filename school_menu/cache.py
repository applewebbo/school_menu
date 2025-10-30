"""
Cache utility functions for consistent cache key generation and management.

This module provides utilities for caching meal data, school menus, and other
frequently accessed data. It supports cache invalidation using pattern matching
with django-redis.

Cache Key Patterns:
- Meals: meal:{school_id}:{week}:{day}:{season}:{meal_type}
- Types Menu: types_menu:{school_id}
- School Menu Page: school_page:{school_slug}

Default TTL: 24 hours (86400 seconds)
"""

from collections.abc import Callable
from typing import Any

from django.core.cache import cache


def get_meal_cache_key(
    school_id: int,
    week: int,
    day: int,
    season: str,
    meal_type: str,
) -> str:
    """
    Generate a consistent cache key for meal data.

    Args:
        school_id: The school's database ID
        week: Week number (1-4)
        day: Day of week (1=Monday, 5=Friday)
        season: Season identifier (e.g., 'INVERNALE', 'PRIMAVERILE')
        meal_type: Meal type (e.g., 'STANDARD', 'NO_GLUTINE')

    Returns:
        Cache key string in format: meal:{school_id}:{week}:{day}:{season}:{meal_type}

    Example:
        >>> get_meal_cache_key(1, 2, 3, 'INVERNALE', 'STANDARD')
        'meal:1:2:3:INVERNALE:STANDARD'
    """
    return f"meal:{school_id}:{week}:{day}:{season}:{meal_type}"


def get_types_menu_cache_key(school_id: int) -> str:
    """
    Generate a cache key for school meal types menu.

    Args:
        school_id: The school's database ID

    Returns:
        Cache key string in format: types_menu:{school_id}

    Example:
        >>> get_types_menu_cache_key(1)
        'types_menu:1'
    """
    return f"types_menu:{school_id}"


def get_school_menu_cache_key(school_slug: str) -> str:
    """
    Generate a cache key for school menu page.

    Args:
        school_slug: The school's slug identifier

    Returns:
        Cache key string in format: school_page:{school_slug}

    Example:
        >>> get_school_menu_cache_key('my-school-city')
        'school_page:my-school-city'
    """
    return f"school_page:{school_slug}"


def invalidate_school_meals(school_id: int) -> int:
    """
    Clear all cached meals for a specific school using pattern matching.

    This function uses django-redis's delete_pattern() to remove all meal
    caches for a school. This is useful when meal data is updated.

    Args:
        school_id: The school's database ID

    Returns:
        Number of cache keys deleted

    Example:
        >>> invalidate_school_meals(1)
        12  # Deleted 12 cache keys
    """
    pattern = f"*meal:{school_id}:*"

    # Check if cache backend supports delete_pattern (Redis backend)
    if hasattr(cache, "delete_pattern"):
        return cache.delete_pattern(pattern)

    # Fallback for non-redis backends (e.g., database cache, dummy cache)
    # In these cases, we can't use pattern matching, so just return 0
    return 0


def invalidate_school_page(school_slug: str) -> None:
    """
    Clear cached school menu page.

    Args:
        school_slug: The school's slug identifier

    Example:
        >>> invalidate_school_page('my-school-city')
    """
    cache_key = get_school_menu_cache_key(school_slug)
    cache.delete(cache_key)


def invalidate_types_menu(school_id: int) -> None:
    """
    Clear cached meal types menu for a school.

    Args:
        school_id: The school's database ID

    Example:
        >>> invalidate_types_menu(1)
    """
    cache_key = get_types_menu_cache_key(school_id)
    cache.delete(cache_key)


def get_cached_or_query(
    key: str,
    query_func: Callable[[], Any],
    timeout: int = 86400,
) -> Any:
    """
    Generic cache-or-query helper function.

    This function checks if data exists in cache. If it does, return cached data.
    If not, execute the query function, cache the result, and return it.

    Args:
        key: Cache key to use
        query_func: Callable that returns the data to cache (executed only on cache miss)
        timeout: Cache timeout in seconds (default: 86400 = 24 hours)

    Returns:
        Cached data or result of query_func

    Example:
        >>> def get_expensive_data():
        ...     return expensive_database_query()
        >>> data = get_cached_or_query('my_key', get_expensive_data, timeout=3600)
    """
    cached_data = cache.get(key)

    if cached_data is not None:
        return cached_data

    # Cache miss - execute query function
    data = query_func()

    # Cache the result
    cache.set(key, data, timeout)

    return data


def invalidate_meal_cache(school_id: int) -> int:
    """
    Clear all meal-related caches for a specific school.

    This includes:
    - Individual meal caches (meal:*)
    - Weekly meal caches (meals:*)
    - Annual meal caches (annual_meals:*)
    - Types menu caches (types_menu:*)
    - JSON API cache (json_api:*)

    Args:
        school_id: The school's database ID

    Returns:
        Total number of cache keys deleted

    Example:
        >>> invalidate_meal_cache(1)
        45  # Deleted 45 cache keys
    """
    total_deleted = 0

    # Patterns to delete
    patterns = [
        f"*meal:{school_id}:*",  # Individual meals
        f"*meals:{school_id}:*",  # Weekly meals
        f"*annual_meals:{school_id}:*",  # Annual meals
        f"*types_menu:{school_id}*",  # Types menus
        "*json_api*",  # JSON API cache (all schools, as cache_page uses complex keys)
    ]

    # Check if cache backend supports delete_pattern (Redis backend)
    if hasattr(cache, "delete_pattern"):
        for pattern in patterns:
            total_deleted += cache.delete_pattern(pattern)
    # Fallback for non-redis backends (e.g., database cache, dummy cache)
    # In these cases, we can't use pattern matching, so just return 0

    return total_deleted


def invalidate_school_cache(school_id: int, school_slug: str = None) -> int:
    """
    Clear ALL caches for a specific school.

    This is used when school settings change (menu_type, season_choice,
    week_bias, alternative menu flags) which affect display even without
    modifying meals.

    Clears:
    - All meal-related caches (via invalidate_meal_cache)
    - School page cache
    - School list cache (public pages)

    Args:
        school_id: The school's database ID
        school_slug: The school's slug identifier (optional, will skip page cache if not provided)

    Returns:
        Total number of cache keys deleted

    Example:
        >>> invalidate_school_cache(1, 'my-school-city')
        48  # Deleted 48 cache keys
    """
    # Clear all meal caches
    total_deleted = invalidate_meal_cache(school_id)

    # Clear school page cache if slug provided
    if school_slug:
        invalidate_school_page(school_slug)
        total_deleted += 1

    # Clear public school list cache
    invalidate_school_list_cache()
    total_deleted += 1

    return total_deleted


def invalidate_school_list_cache() -> None:
    """
    Clear cached public school list.

    This should be called when school settings change that affect
    the public school list display (is_published, name, city, etc.)

    Example:
        >>> invalidate_school_list_cache()
    """
    cache.delete("school_list_public")
