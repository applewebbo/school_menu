"""Fixed-window rate limiting for the contact and menu-report forms (#292)."""

from django.core.cache import cache


def is_rate_limited(key: str, limit: int, window_seconds: int) -> bool:
    """
    True once `key` has been hit more than `limit` times within `window_seconds`.

    `cache.add` opens the window so its TTL is only ever set once, then every
    following hit goes through `cache.incr` - two atomic cache operations rather
    than a read-then-write, so concurrent requests can't both slip in under the
    limit.
    """
    if cache.add(key, 1, window_seconds):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        # Key expired between the add() above and this incr(): treat as a fresh window.
        cache.add(key, 1, window_seconds)
        return False
    return count > limit
